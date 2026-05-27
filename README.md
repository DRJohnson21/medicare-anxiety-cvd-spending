# Medicare Cardiovascular Spending Variation by Anxiety Status

Does anxiety independently raise healthcare spending among Medicare beneficiaries with cardiovascular disease — and where does the extra cost go?

This project analyzes CMS Medicare claims data to examine the relationship between anxiety and healthcare spending across three major cardiovascular conditions: **hypertension**, **coronary artery disease (CAD)**, and **atrial fibrillation (AFib)**. It was completed as a Health Affairs DataWatch-style white paper assignment for my Healthcare Analytics course.

## Key Findings

- **Unadjusted gap:** Patients with anxiety spend **$2,600–$3,000 more per year** across all three CVD conditions (44.6%–63.1% higher)
- **Adjusted gap:** After controlling for age, sex, race, and comorbidities, spending remains **7.8%–12.4% higher** (all p < 0.001)
- **Outpatient-driven:** The spending gap is concentrated in outpatient care — patients with anxiety had **43%–58% higher odds of any outpatient use** but no significant difference in hospitalization
- **Nationwide pattern:** All **50 states and DC** show a positive anxiety spending gap (mean: $3,011, range: $353–$6,959)

## Project Structure

```
├── paper/
│   ├── Medicare_CVD_Spending_by_Anxiety_Status_Paper.pdf    # Full white paper
│   └── Medicare_CVD_Spending_by_Anxiety_Status_Slides.pdf   # Summary slide deck
│
├── scripts/
│   ├── 01_cohort_construction.py       # Load CMS SynPUF data, flag diagnoses, build cohort
│   ├── 02_spending_calculation.py      # Calculate per-beneficiary spending from claims
│   ├── 03_descriptive_analysis.py      # Table 1, spending comparisons, unadjusted tests
│   ├── 04_regression_models.R          # Gamma GLMs, two-part models, interaction tests, state analysis
│   └── 05_tableau_exhibit_prep.py      # Prepare exhibit-ready CSVs for Tableau
│
└── README.md
```

## Analytical Pipeline

| Script | Language | Purpose | Key Outputs |
|--------|----------|---------|-------------|
| `01` | Python | Cohort construction from raw CMS SynPUF files | `cvd_cohort_with_flags.csv` |
| `02` | Python | Spending and utilization calculation from claims | `analytic_dataset.csv` |
| `03` | Python | Descriptive statistics, Table 1, unadjusted tests | Summary tables, Wilcoxon/chi-square tests |
| `04` | R | Gamma GLMs, two-part models, interaction models, state analysis | Model coefficients, cost ratios, state-level gaps |
| `05` | Python | Tableau-ready exhibit data | Four exhibit CSVs for visualization |

## Methods

- **Gamma GLMs** with log link for total spending (standard for right-skewed cost data)
- **Two-part models** (logistic + Gamma) to decompose the probability of any use from conditional spending
- **Interaction models** to test heterogeneity across CVD conditions and age groups
- **State-level ecological analysis** with one-sample t-tests and coefficient of variation

## Data Source

[CMS DE-SynPUF](https://www.cms.gov/Research-Statistics-Data-and-Systems/Downloadable-Public-Use-Files/SynPUFs/DE_Syn_PUF) (Synthetic Public Use Files), Sample 1. These are publicly available synthetic Medicare claims designed to mimic real beneficiary data while protecting privacy.

### To Reproduce

1. Download the SynPUF Sample 1 files from the CMS link above
2. Update the `DATA_DIR` and `OUTPUT_DIR` paths in each script
3. Run scripts in order: `01` → `02` → `03` → `04` (R) → `05`

## Requirements

**Python:**
- pandas
- numpy
- scipy

**R:**
- tidyverse
- broom
- sandwich
- lmtest
- MASS

## Author

Davey Johnson

## License

This project is licensed under the MIT License — see [LICENSE](LICENSE) for details.
