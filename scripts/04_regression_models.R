#' =============================================================================
#' SCRIPT 4: REGRESSION MODELS AND INFERENTIAL ANALYSIS
#' =============================================================================
#' DataWatch White Paper — Medicare Anxiety & Cardiovascular Spending Analysis
#'
#' PURPOSE:
#'   - Gamma GLM models (standard for healthcare cost data)
#'   - Two-part models (logistic + gamma for zero-inflated spending)
#'   - Interaction models (anxiety × CVD condition, anxiety × age group)
#'   - State-level ecological analysis
#'   - Output: formatted model results for your white paper
#'
#' BEFORE RUNNING THIS SCRIPT:
#'   1. Scripts 1-3 must have been run successfully
#'   2. analytic_dataset.csv must exist in your output directory
#'   3. Install required R packages (see below)
#'
#' REQUIRED PACKAGES (run once):
#'   install.packages(c("tidyverse", "broom", "sandwich", "lmtest",
#'                       "MASS", "pscl", "marginaleffects", "knitr"))
#'
#' OUTPUTS:
#'   - model_results_summary.txt     (all model coefficients and fit stats)
#'   - model1_gamma_glm.csv          (main GLM results by CVD condition)
#'   - model2_twopart.csv            (two-part model results)
#'   - model3_interactions.csv       (interaction model results)
#'   - state_level_analysis.csv      (state ecological results)
#' =============================================================================

library(tidyverse)
library(broom)
library(MASS)
library(sandwich)
library(lmtest)

# ==============================================================================
# >>> USER INPUT REQUIRED <<<
# ==============================================================================

# Path to the analytic dataset from Script 2
DATA_PATH <- "./output/analytic_dataset.csv"

# Path to save output files
OUTPUT_DIR <- "./output"

# Significance level
ALPHA <- 0.05

# ==============================================================================
# END OF USER INPUTS
# ==============================================================================

cat("=======================================================================\n")
cat("LOADING AND PREPARING DATA\n")
cat("=======================================================================\n\n")

df <- read.csv(DATA_PATH, stringsAsFactors = FALSE)
cat(sprintf("Loaded %s beneficiaries\n\n", format(nrow(df), big.mark = ",")))

# --- Factor variables ---
df$has_anxiety   <- factor(df$has_anxiety, levels = c(0, 1),
                           labels = c("No Anxiety", "Anxiety"))
df$sex           <- factor(df$sex)
df$race          <- factor(df$race)
df$age_group     <- factor(df$age_group,
                           levels = c("Under 65", "65-74", "75-84", "85+"))

# Reference categories
df$has_anxiety <- relevel(df$has_anxiety, ref = "No Anxiety")
df$sex         <- relevel(df$sex, ref = "Male")
df$race        <- relevel(df$race, ref = "White")
df$age_group   <- relevel(df$age_group, ref = "65-74")

# Create primary_cvd factor HERE — before creating any subsets —
# so that df_model3 inherits the correct factor levels and reference category.
df$primary_cvd <- factor(df$primary_cvd,
                         levels = c("Hypertension", "CAD", "AFib"))

# For gamma GLM, we need spending > 0. Handle zeros by:
# (a) adding a small constant, or (b) using a two-part model.
# We'll do both approaches.

# Add $1 to avoid log(0) issues in gamma GLM
df$total_spend_adj    <- df$total_spend + 1
df$inpatient_spend_adj <- df$inpatient_spend + 1
df$outpatient_spend_adj <- df$outpatient_spend + 1

# Create the positive-spend subset AFTER all factor conversions
# so primary_cvd, age_group, etc. carry their levels correctly into Model 3.
df_model3 <- df %>%
  filter(total_spend_adj > 0)

cat(sprintf("df_model3: %s rows (after excluding zero-spend)\n",
            format(nrow(df_model3), big.mark = ",")))
cat(sprintf("  primary_cvd levels: %s\n", paste(levels(df_model3$primary_cvd), collapse = ", ")))


# ======================================================================
# MODEL 1: GAMMA GLM — SEPARATE BY CVD CONDITION
# ======================================================================
cat("\n=======================================================================\n")
cat("MODEL 1: GAMMA GLM FOR TOTAL SPENDING (by CVD condition)\n")
cat("=======================================================================\n\n")

#' The Gamma GLM with log link is the standard approach for modeling
#' healthcare costs because:
#'   - It handles the right-skewed distribution of spending
#'   - The log link gives multiplicative (ratio) interpretation
#'   - Coefficients exponentiate to cost ratios
#'
#' Formula: total_spend ~ anxiety + age_group + sex + race + comorbidity_count
#'
#' Exponentiated coefficient for anxiety = cost ratio (anxiety / no anxiety)

run_gamma_glm <- function(data, condition_name) {
  cat(sprintf("\n--- %s ---\n", condition_name))
  cat(sprintf("  N = %s\n", format(nrow(data), big.mark = ",")))
  cat(sprintf("  N Anxiety = %s\n",
              format(sum(data$has_anxiety == "Anxiety"), big.mark = ",")))
  
  # Check for sufficient sample in both groups
  if (sum(data$has_anxiety == "Anxiety") < 20) {
    cat("  WARNING: Very small anxiety group. Results may be unreliable.\n")
  }
  
  # Fit Gamma GLM with log link
  model <- tryCatch(
    glm(total_spend_adj ~ has_anxiety + age_group + sex + race + comorbidity_count,
        data = data,
        family = Gamma(link = "log")),
    error = function(e) {
      cat(sprintf("  ERROR fitting model: %s\n", e$message))
      return(NULL)
    }
  )
  
  if (is.null(model)) return(NULL)
  
  # Robust standard errors (sandwich estimator)
  robust_se <- tryCatch(
    coeftest(model, vcov = vcovHC(model, type = "HC1")),
    error = function(e) NULL
  )
  
  # Tidy output
  results <- tidy(model, conf.int = TRUE) %>%
    mutate(
      cost_ratio    = exp(estimate),
      cr_lower      = exp(conf.low),
      cr_upper      = exp(conf.high),
      sig           = case_when(
        p.value < 0.001 ~ "***",
        p.value < 0.01  ~ "**",
        p.value < 0.05  ~ "*",
        p.value < 0.1   ~ ".",
        TRUE             ~ ""
      ),
      condition     = condition_name
    )
  
  # Print key results
  anxiety_row <- results %>% filter(term == "has_anxietyAnxiety")
  if (nrow(anxiety_row) > 0) {
    cat(sprintf("\n  ANXIETY EFFECT:\n"))
    cat(sprintf("    Cost ratio:   %.3f (%.3f - %.3f)\n",
                anxiety_row$cost_ratio, anxiety_row$cr_lower, anxiety_row$cr_upper))
    cat(sprintf("    p-value:      %.3e %s\n", anxiety_row$p.value, anxiety_row$sig))
    cat(sprintf("    Interpretation: Anxiety patients cost %.1f%% %s\n",
                abs(anxiety_row$cost_ratio - 1) * 100,
                ifelse(anxiety_row$cost_ratio > 1, "more", "less")))
  }
  
  # Model fit
  cat(sprintf("\n  Model fit:\n"))
  cat(sprintf("    AIC:          %.1f\n", AIC(model)))
  cat(sprintf("    Deviance:     %.1f\n", deviance(model)))
  cat(sprintf("    Null deviance:%.1f\n", model$null.deviance))
  
  return(list(model = model, results = results, robust = robust_se))
}


# Run for each CVD condition
model1_results <- list()

# Hypertension
htn_data <- df %>%
  filter(has_hypertension == 1, total_spend_adj > 0)
model1_results$hypertension <- run_gamma_glm(htn_data, "Hypertension")

# CAD
cad_data <- df %>%
  filter(has_cad == 1, total_spend_adj > 0)
model1_results$cad <- run_gamma_glm(cad_data, "CAD")

# AFib
afib_data <- df %>%
  filter(has_afib == 1, total_spend_adj > 0)
model1_results$afib <- run_gamma_glm(afib_data, "AFib")

# Combine results
model1_combined <- bind_rows(
  lapply(model1_results, function(x) if (!is.null(x)) x$results else NULL)
)

print(model1_combined)
colnames(model1_combined)
nrow(model1_combined)

write.csv(model1_combined,
          file.path(OUTPUT_DIR, "model1_gamma_glm.csv"),
          row.names = FALSE)
cat(sprintf("\nModel 1 results saved to: %s\n",
            file.path(OUTPUT_DIR, "model1_gamma_glm.csv")))

# ======================================================================
# FIGURE 2: ADJUSTED PREDICTED SPENDING VALUES FOR TABLEAU
# ======================================================================
cat("\n=======================================================================\n")
cat("FIGURE 2: ADJUSTED PREDICTED SPENDING VALUES\n")
cat("=======================================================================\n\n")

# This creates adjusted spending estimates using the fitted Model 1 Gamma GLMs.
# For each CVD condition, we predict spending twice:
#   1. assuming everyone has anxiety
#   2. assuming everyone does not have anxiety
# Then we average those predictions to create adjusted mean spending values.

adjusted_predictions <- list()

condition_info <- list(
  Hypertension = list(
    model = model1_results$hypertension$model,
    data  = htn_data
  ),
  CAD = list(
    model = model1_results$cad$model,
    data  = cad_data
  ),
  AFib = list(
    model = model1_results$afib$model,
    data  = afib_data
  )
)

for (cond_name in names(condition_info)) {
  
  model_obj <- condition_info[[cond_name]]$model
  cond_data <- condition_info[[cond_name]]$data
  
  if (is.null(model_obj)) {
    cat(sprintf("Skipping %s because model is NULL\n", cond_name))
    next
  }
  
  data_anx <- cond_data
  data_no_anx <- cond_data
  
  data_anx$has_anxiety <- factor(
    "Anxiety",
    levels = levels(cond_data$has_anxiety)
  )
  
  data_no_anx$has_anxiety <- factor(
    "No Anxiety",
    levels = levels(cond_data$has_anxiety)
  )
  
  pred_anx <- predict(model_obj, newdata = data_anx, type = "response") - 1
  pred_no_anx <- predict(model_obj, newdata = data_no_anx, type = "response") - 1
  
  temp <- data.frame(
    condition = cond_name,
    anxiety_status = c("With Anxiety", "Without Anxiety"),
    adjusted_mean_spending = c(
      mean(pred_anx, na.rm = TRUE),
      mean(pred_no_anx, na.rm = TRUE)
    )
  )
  
  adjusted_predictions[[cond_name]] <- temp
}

figure2_adjusted_spending <- bind_rows(adjusted_predictions) %>%
  group_by(condition) %>%
  mutate(
    adjusted_difference =
      adjusted_mean_spending[anxiety_status == "With Anxiety"] -
      adjusted_mean_spending[anxiety_status == "Without Anxiety"],
    
    adjusted_percent_difference =
      adjusted_difference /
      adjusted_mean_spending[anxiety_status == "Without Anxiety"] * 100
  ) %>%
  ungroup() %>%
  mutate(
    adjusted_mean_spending = round(adjusted_mean_spending, 2),
    adjusted_difference = round(adjusted_difference, 2),
    adjusted_percent_difference = round(adjusted_percent_difference, 1)
  )

print(figure2_adjusted_spending)

write.csv(
  figure2_adjusted_spending,
  file.path(OUTPUT_DIR, "figure2_adjusted_spending.csv"),
  row.names = FALSE
)

cat(sprintf("\nFigure 2 adjusted spending values saved to: %s\n",
            file.path(OUTPUT_DIR, "figure2_adjusted_spending.csv")))


# ======================================================================
# MODEL 2: TWO-PART MODEL
# ======================================================================
cat("\n=======================================================================\n")
cat("MODEL 2: TWO-PART MODEL (Logistic + Gamma)\n")
cat("=======================================================================\n\n")

#' Two-part models are appropriate when there is a mass of zeros in spending.
#' Part 1: Logistic regression — P(any spending > 0)
#' Part 2: Gamma GLM — E[spending | spending > 0]
#'
#' Combined effect = change in P(any spending) × change in E[spending|>0]

run_two_part <- function(data, spend_var, condition_name) {
  cat(sprintf("\n--- %s: %s ---\n", condition_name, spend_var))
  
  # Check zero proportion
  zero_pct <- mean(data[[spend_var]] == 0) * 100
  cat(sprintf("  Zero spending: %.1f%%\n", zero_pct))
  
  if (zero_pct < 5) {
    cat("  <5% zeros — two-part model may not be needed; Gamma GLM is sufficient.\n")
  }
  
  # Part 1: Logistic (any spending?)
  data$any_spend <- as.integer(data[[spend_var]] > 0)
  
  part1 <- tryCatch(
    glm(any_spend ~ has_anxiety + age_group + sex + race + comorbidity_count,
        data = data, family = binomial(link = "logit")),
    error = function(e) { cat(sprintf("  Part 1 error: %s\n", e$message)); NULL }
  )
  
  # Part 2: Gamma GLM on positive spenders only
  pos_data <- data %>% filter(data[[spend_var]] > 0)
  pos_data$spend_pos <- pos_data[[spend_var]]
  
  part2 <- tryCatch(
    glm(spend_pos ~ has_anxiety + age_group + sex + race + comorbidity_count,
        data = pos_data, family = Gamma(link = "log")),
    error = function(e) { cat(sprintf("  Part 2 error: %s\n", e$message)); NULL }
  )
  
  # Results
  results <- data.frame(condition = condition_name, spend_type = spend_var)
  
  if (!is.null(part1)) {
    p1_anx <- tidy(part1) %>% filter(term == "has_anxietyAnxiety")
    if (nrow(p1_anx) > 0) {
      results$part1_or    <- exp(p1_anx$estimate)
      results$part1_pval  <- p1_anx$p.value
      cat(sprintf("  Part 1 (Logistic): OR = %.3f, p = %.4e\n",
                  results$part1_or, results$part1_pval))
    }
  }
  
  if (!is.null(part2)) {
    p2_anx <- tidy(part2) %>% filter(term == "has_anxietyAnxiety")
    if (nrow(p2_anx) > 0) {
      results$part2_cost_ratio <- exp(p2_anx$estimate)
      results$part2_pval       <- p2_anx$p.value
      cat(sprintf("  Part 2 (Gamma):    CR = %.3f, p = %.4e\n",
                  results$part2_cost_ratio, results$part2_pval))
    }
  }
  
  return(results)
}

# Run two-part models for each condition × spending type
twopart_results <- list()
counter <- 1

for (cvd_flag in c("has_hypertension", "has_cad", "has_afib")) {
  cvd_label <- switch(cvd_flag,
                      has_hypertension = "Hypertension",
                      has_cad = "CAD",
                      has_afib = "AFib"
  )
  cvd_data <- df %>% filter(!!sym(cvd_flag) == 1)
  
  for (spend_var in c("inpatient_spend", "outpatient_spend")) {
    twopart_results[[counter]] <- run_two_part(cvd_data, spend_var, cvd_label)
    counter <- counter + 1
  }
}

twopart_combined <- bind_rows(twopart_results)
write.csv(twopart_combined,
          file.path(OUTPUT_DIR, "model2_twopart.csv"),
          row.names = FALSE)
cat(sprintf("\nTwo-part model results saved to: %s\n",
            file.path(OUTPUT_DIR, "model2_twopart.csv")))

# ======================================================================
# FIGURE 3: ADJUSTED INPATIENT VS OUTPATIENT SPENDING FOR TABLEAU
# ======================================================================

cat("\n=======================================================================\n")
cat("FIGURE 3: ADJUSTED INPATIENT VS OUTPATIENT SPENDING VALUES\n")
cat("=======================================================================\n\n")

figure3_results <- list()
counter <- 1

for (cvd_flag in c("has_hypertension", "has_cad", "has_afib")) {
  
  cvd_label <- switch(cvd_flag,
                      has_hypertension = "Hypertension",
                      has_cad = "CAD",
                      has_afib = "AFib")
  
  cvd_data <- df %>% filter(!!sym(cvd_flag) == 1)
  
  for (spend_var in c("outpatient_spend", "inpatient_spend")) {
    
    spend_label <- ifelse(spend_var == "outpatient_spend",
                          "Outpatient",
                          "Inpatient")
    
    cat(sprintf("\n--- %s: %s ---\n", cvd_label, spend_label))
    
    # Create spending flag for two-part model
    cvd_data$any_spend <- as.integer(cvd_data[[spend_var]] > 0)
    
    # Part 1: probability of any spending
    part1 <- glm(
      any_spend ~ has_anxiety + age_group + sex + race + comorbidity_count,
      data = cvd_data,
      family = binomial(link = "logit")
    )
    
    # Part 2: spending amount among positive spenders
    pos_data <- cvd_data %>%
      filter(.data[[spend_var]] > 0)
    
    pos_data$spend_pos <- pos_data[[spend_var]]
    
    part2 <- glm(
      spend_pos ~ has_anxiety + age_group + sex + race + comorbidity_count,
      data = pos_data,
      family = Gamma(link = "log")
    )
    
    # Create two prediction datasets:
    # one where everyone has anxiety, one where everyone does not
    data_anx <- cvd_data
    data_no_anx <- cvd_data
    
    data_anx$has_anxiety <- factor(
      "Anxiety",
      levels = levels(cvd_data$has_anxiety)
    )
    
    data_no_anx$has_anxiety <- factor(
      "No Anxiety",
      levels = levels(cvd_data$has_anxiety)
    )
    
    # Predict probability of any spending
    prob_anx <- predict(part1, newdata = data_anx, type = "response")
    prob_no_anx <- predict(part1, newdata = data_no_anx, type = "response")
    
    # Predict conditional spending among spenders
    cond_spend_anx <- predict(part2, newdata = data_anx, type = "response")
    cond_spend_no_anx <- predict(part2, newdata = data_no_anx, type = "response")
    
    # Two-part expected spending = probability of spending × conditional spending
    expected_anx <- prob_anx * cond_spend_anx
    expected_no_anx <- prob_no_anx * cond_spend_no_anx
    
    temp <- data.frame(
      condition = cvd_label,
      spend_type = spend_label,
      anxiety_status = c("With Anxiety", "Without Anxiety"),
      adjusted_expected_spending = c(
        mean(expected_anx, na.rm = TRUE),
        mean(expected_no_anx, na.rm = TRUE)
      )
    )
    
    figure3_results[[counter]] <- temp
    counter <- counter + 1
  }
}

figure3_adjusted_spending <- bind_rows(figure3_results) %>%
  group_by(condition, spend_type) %>%
  mutate(
    adjusted_difference =
      adjusted_expected_spending[anxiety_status == "With Anxiety"] -
      adjusted_expected_spending[anxiety_status == "Without Anxiety"],
    
    adjusted_percent_difference =
      adjusted_difference /
      adjusted_expected_spending[anxiety_status == "Without Anxiety"] * 100
  ) %>%
  ungroup() %>%
  mutate(
    adjusted_expected_spending = round(adjusted_expected_spending, 2),
    adjusted_difference = round(adjusted_difference, 2),
    adjusted_percent_difference = round(adjusted_percent_difference, 1)
  )

print(figure3_adjusted_spending)

write.csv(
  figure3_adjusted_spending,
  file.path(OUTPUT_DIR, "figure3_adjusted_inpatient_outpatient.csv"),
  row.names = FALSE
)

cat(sprintf("\nFigure 3 adjusted inpatient/outpatient values saved to: %s\n",
            file.path(OUTPUT_DIR, "figure3_adjusted_inpatient_outpatient.csv")))

# ======================================================================
# MODEL 3: INTERACTION MODELS
# ======================================================================
cat("\n=======================================================================\n")
cat("MODEL 3: INTERACTION MODELS\n")
cat("=======================================================================\n\n")

#' Test whether the anxiety-spending relationship differs by:
#'   (a) CVD condition type
#'   (b) Age group
#'
#' We use df_model3 (positive spenders only, all factors already set).

# --- 3a: Anxiety × CVD condition ---
cat("--- Model 3a: Anxiety x CVD Condition ---\n")

model3a <- tryCatch(
  glm(total_spend_adj ~ has_anxiety * primary_cvd + age_group + sex + race +
        comorbidity_count,
      data = df_model3,
      family = Gamma(link = "log")),
  error = function(e) { cat(sprintf("Error: %s\n", e$message)); NULL }
)

if (!is.null(model3a)) {
  cat("\nInteraction terms (Anxiety x CVD Condition):\n")
  interaction_terms <- tidy(model3a) %>%
    filter(grepl("has_anxiety.*primary_cvd|primary_cvd.*has_anxiety", term))
  print(interaction_terms %>%
          mutate(cost_ratio = exp(estimate)) %>%
          dplyr::select(term, estimate, cost_ratio, p.value))
  
  # Likelihood ratio test: interaction model vs. main effects only
  model3a_main <- glm(total_spend_adj ~ has_anxiety + primary_cvd + age_group +
                        sex + race + comorbidity_count,
                      data = df_model3, family = Gamma(link = "log"))
  lr_test <- anova(model3a_main, model3a, test = "Chisq")
  cat(sprintf("\nLR test for interaction: p = %.3e\n", lr_test$`Pr(>Chi)`[2]))
}

# --- 3b: Anxiety × Age Group ---
cat("\n--- Model 3b: Anxiety x Age Group ---\n")

model3b <- tryCatch(
  glm(total_spend_adj ~ has_anxiety * age_group + sex + race +
        comorbidity_count + primary_cvd,
      data = df_model3,
      family = Gamma(link = "log")),
  error = function(e) { cat(sprintf("Error: %s\n", e$message)); NULL }
)

if (!is.null(model3b)) {
  cat("\nInteraction terms (Anxiety x Age Group):\n")
  interaction_terms_b <- tidy(model3b) %>%
    filter(grepl("has_anxiety.*age_group|age_group.*has_anxiety", term))
  print(interaction_terms_b %>%
          mutate(cost_ratio = exp(estimate)) %>%
          dplyr::select(term, estimate, cost_ratio, p.value))
  
  model3b_main <- glm(total_spend_adj ~ has_anxiety + age_group + sex + race +
                        comorbidity_count + primary_cvd,
                      data = df_model3, family = Gamma(link = "log"))
  lr_test_b <- anova(model3b_main, model3b, test = "Chisq")
  cat(sprintf("\nLR test for interaction: p = %.3e\n", lr_test_b$`Pr(>Chi)`[2]))
}

# Save interaction model results
if (!is.null(model3a) && !is.null(model3b)) {
  model3_combined <- bind_rows(
    tidy(model3a) %>% mutate(model = "Anxiety x CVD"),
    tidy(model3b) %>% mutate(model = "Anxiety x Age")
  ) %>% mutate(cost_ratio = exp(estimate))
  
  write.csv(model3_combined,
            file.path(OUTPUT_DIR, "model3_interactions.csv"),
            row.names = FALSE)
  cat(sprintf("\nInteraction results saved to: %s\n",
              file.path(OUTPUT_DIR, "model3_interactions.csv")))
}


# ======================================================================
# MODEL 4: STATE-LEVEL GEOGRAPHIC VARIATION
# ======================================================================
cat("\n=======================================================================\n")
cat("MODEL 4: STATE-LEVEL GEOGRAPHIC VARIATION\n")
cat("=======================================================================\n\n")

#' Examine whether the anxiety-associated spending gap is consistent
#' across states or concentrated in certain regions.
#' No external data required — this uses only the claims data.

# Compute state-level spending gap
state_gap <- df %>%
  filter(state != "Unknown") %>%
  group_by(state, has_anxiety) %>%
  summarise(
    n = n(),
    mean_spend = mean(total_spend, na.rm = TRUE),
    median_spend = median(total_spend, na.rm = TRUE),
    mean_ip_spend = mean(inpatient_spend, na.rm = TRUE),
    mean_op_spend = mean(outpatient_spend, na.rm = TRUE),
    .groups = "drop"
  ) %>%
  pivot_wider(
    names_from = has_anxiety,
    values_from = c(n, mean_spend, median_spend, mean_ip_spend, mean_op_spend),
    names_sep = "_"
  ) %>%
  mutate(
    spending_gap = `mean_spend_Anxiety` - `mean_spend_No Anxiety`,
    cost_ratio   = `mean_spend_Anxiety` / `mean_spend_No Anxiety`,
    ip_gap       = `mean_ip_spend_Anxiety` - `mean_ip_spend_No Anxiety`,
    op_gap       = `mean_op_spend_Anxiety` - `mean_op_spend_No Anxiety`,
    anxiety_prevalence = `n_Anxiety` / (`n_Anxiety` + `n_No Anxiety`) * 100,
    total_n = `n_Anxiety` + `n_No Anxiety`
  ) %>%
  filter(total_n >= 50)  # Minimum sample size per state

cat(sprintf("States with sufficient data: %d\n", nrow(state_gap)))
cat(sprintf("Mean spending gap across states: $%.0f\n", mean(state_gap$spending_gap, na.rm = TRUE)))
cat(sprintf("SD of spending gap: $%.0f\n", sd(state_gap$spending_gap, na.rm = TRUE)))
cat(sprintf("Range: $%.0f to $%.0f\n",
            min(state_gap$spending_gap, na.rm = TRUE),
            max(state_gap$spending_gap, na.rm = TRUE)))

# How many states show a positive gap (anxiety costs more)?
n_positive <- sum(state_gap$spending_gap > 0, na.rm = TRUE)
n_total <- sum(!is.na(state_gap$spending_gap))
cat(sprintf("\nStates where anxiety group costs more: %d of %d (%.1f%%)\n",
            n_positive, n_total, 100 * n_positive / n_total))

# Consistency test: one-sample t-test on state-level gaps
# H0: the mean spending gap across states = 0
if (n_total >= 5) {
  gap_test <- t.test(state_gap$spending_gap, mu = 0)
  cat(sprintf("\nOne-sample t-test on state spending gaps:\n"))
  cat(sprintf("  Mean gap:  $%.0f\n", gap_test$estimate))
  cat(sprintf("  t = %.3f, df = %.0f, p = %.4e\n",
              gap_test$statistic, gap_test$parameter, gap_test$p.value))
  cat(sprintf("  95%% CI: $%.0f to $%.0f\n", gap_test$conf.int[1], gap_test$conf.int[2]))
  if (gap_test$p.value < ALPHA) {
    cat("  --> The spending gap is significantly different from zero across states.\n")
  } else {
    cat("  --> The spending gap is NOT significantly different from zero across states.\n")
  }
}

# Correlation: anxiety prevalence vs spending gap
if (nrow(state_gap) > 5) {
  cor_test <- cor.test(state_gap$anxiety_prevalence, state_gap$spending_gap,
                       method = "spearman")
  cat(sprintf("\nCorrelation (anxiety prevalence vs spending gap):\n"))
  cat(sprintf("  Spearman rho = %.3f, p = %.4e\n", cor_test$estimate, cor_test$p.value))
}

# Top and bottom states
cat("\nTop 5 states by spending gap (anxiety costs most):\n")
top5 <- state_gap %>% arrange(desc(spending_gap)) %>% head(5)
for (i in 1:nrow(top5)) {
  r <- top5[i, ]
  cat(sprintf("  %s: gap = $%+.0f  (Anx=$%.0f vs No Anx=$%.0f, n=%d)\n",
              r$state, r$spending_gap,
              r$`mean_spend_Anxiety`, r$`mean_spend_No Anxiety`, r$total_n))
}

cat("\nBottom 5 states by spending gap (anxiety costs least or less):\n")
bot5 <- state_gap %>% arrange(spending_gap) %>% head(5)
for (i in 1:nrow(bot5)) {
  r <- bot5[i, ]
  cat(sprintf("  %s: gap = $%+.0f  (Anx=$%.0f vs No Anx=$%.0f, n=%d)\n",
              r$state, r$spending_gap,
              r$`mean_spend_Anxiety`, r$`mean_spend_No Anxiety`, r$total_n))
}

# Coefficient of variation — how consistent is the gap?
cv_gap <- sd(state_gap$spending_gap, na.rm = TRUE) / abs(mean(state_gap$spending_gap, na.rm = TRUE))
cat(sprintf("\nCoefficient of variation of spending gap: %.2f\n", cv_gap))
if (cv_gap < 1) {
  cat("  --> Relatively consistent gap across states.\n")
} else {
  cat("  --> Substantial geographic variation in the gap.\n")
}

write.csv(state_gap,
          file.path(OUTPUT_DIR, "state_level_analysis.csv"),
          row.names = FALSE)
cat(sprintf("\nState results saved to: %s\n",
            file.path(OUTPUT_DIR, "state_level_analysis.csv")))


# ======================================================================
# WRITE COMPREHENSIVE SUMMARY
# ======================================================================
cat("\n=======================================================================\n")
cat("WRITING COMPREHENSIVE MODEL SUMMARY\n")
cat("=======================================================================\n\n")

sink(file.path(OUTPUT_DIR, "model_results_summary.txt"))

cat("================================================================================\n")
cat("REGRESSION MODEL RESULTS SUMMARY\n")
cat("DataWatch White Paper — Anxiety & Cardiovascular Spending\n")
cat("================================================================================\n\n")

cat("MODEL 1: GAMMA GLM (Adjusted Cost Ratios for Anxiety)\n")
cat("------------------------------------------------------------------------\n")
cat("Covariates: age_group, sex, race, comorbidity_count\n")
cat("Family: Gamma(link = log)\n\n")

for (cond_name in c("Hypertension", "CAD", "AFib")) {
  cond_key <- tolower(gsub(" ", "_", cond_name))
  if (cond_key == "cad") cond_key <- "cad"
  if (cond_key == "afib") cond_key <- "afib"
  
  res <- model1_combined %>% filter(condition == cond_name, term == "has_anxietyAnxiety")
  if (nrow(res) > 0) {
    cat(sprintf("  %s:\n", cond_name))
    cat(sprintf("    Adjusted Cost Ratio: %.3f (95%% CI: %.3f - %.3f)\n",
                res$cost_ratio, res$cr_lower, res$cr_upper))
    cat(sprintf("    p-value: %.3e %s\n\n", res$p.value, res$sig))
  }
}

cat("\nMODEL 2: TWO-PART MODEL RESULTS\n")
cat("------------------------------------------------------------------------\n")
if (nrow(twopart_combined) > 0) {
  print(twopart_combined, row.names = FALSE)
}

cat("\n\nMODEL 3: INTERACTION TESTS\n")
cat("------------------------------------------------------------------------\n")
if (!is.null(model3a)) {
  cat("3a: Anxiety x CVD Condition\n")
  cat(sprintf("    LR test p-value: %.3e\n", lr_test$`Pr(>Chi)`[2]))
}
if (!is.null(model3b)) {
  cat("3b: Anxiety x Age Group\n")
  cat(sprintf("    LR test p-value: %.3e\n", lr_test_b$`Pr(>Chi)`[2]))
}

cat("\n\nMODEL 4: STATE-LEVEL GEOGRAPHIC VARIATION\n")
cat("------------------------------------------------------------------------\n")
cat(sprintf("States analyzed: %d\n", nrow(state_gap)))
cat(sprintf("Mean spending gap: $%.0f\n", mean(state_gap$spending_gap, na.rm = TRUE)))
cat(sprintf("SD of spending gap: $%.0f\n", sd(state_gap$spending_gap, na.rm = TRUE)))
n_pos <- sum(state_gap$spending_gap > 0, na.rm = TRUE)
cat(sprintf("States with positive gap: %d of %d\n", n_pos, nrow(state_gap)))

sink()

cat(sprintf("Summary saved to: %s\n", file.path(OUTPUT_DIR, "model_results_summary.txt")))
cat("\n>>> Script 4 complete. All models fitted. Ready for visualization. <<<\n")
