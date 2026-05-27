"""
================================================================================
SCRIPT 3: DESCRIPTIVE ANALYSIS AND SUMMARY TABLES
================================================================================
DataWatch White Paper — Medicare Anxiety & Cardiovascular Spending Analysis

PURPOSE:
  - Produce Table 1 (baseline characteristics by anxiety status)
  - Produce spending comparison tables by CVD condition
  - Produce spending comparison by age group
  - Run unadjusted statistical tests (Wilcoxon, chi-square)
  - Output: formatted tables and test results for your white paper

BEFORE RUNNING THIS SCRIPT:
  1. You must have run Scripts 1 and 2 successfully
  2. analytic_dataset.csv must exist in OUTPUT_DIR

OUTPUTS:
  - table1_characteristics.csv
  - table2_spending_by_cvd.csv
  - table3_spending_by_age.csv
  - unadjusted_tests.txt
================================================================================
"""

import pandas as pd
import numpy as np
from scipy import stats
import os
import warnings
warnings.filterwarnings('ignore')

# ==============================================================================
# >>> USER INPUT REQUIRED <<<
# ==============================================================================

# Same output directory as Scripts 1 and 2
OUTPUT_DIR = "./output"  # Path for output files

# Significance level for statistical tests
ALPHA = 0.05

# ==============================================================================
# END OF USER INPUTS
# ==============================================================================

print("=" * 70)
print("LOADING ANALYTIC DATASET")
print("=" * 70)

df = pd.read_csv(os.path.join(OUTPUT_DIR, "analytic_dataset.csv"))
print(f"Loaded {len(df):,} beneficiaries\n")


# ======================================================================
# TABLE 1: BASELINE CHARACTERISTICS BY ANXIETY STATUS
# ======================================================================
print("=" * 70)
print("TABLE 1: BASELINE CHARACTERISTICS BY ANXIETY STATUS")
print("=" * 70)

def calc_table1(df):
    """Build a Table 1 comparing anxiety vs. no-anxiety groups."""
    
    anx = df[df['has_anxiety'] == 1]
    no_anx = df[df['has_anxiety'] == 0]
    
    rows = []
    
    # --- Sample size ---
    rows.append({
        'Characteristic': 'N',
        'Anxiety': f"{len(anx):,}",
        'No Anxiety': f"{len(no_anx):,}",
        'p-value': ''
    })
    
    # --- Continuous variables (age, comorbidity count) ---
    for var, label in [('age', 'Age, mean (SD)'), 
                        ('comorbidity_count', 'Comorbidity count, mean (SD)')]:
        if var in df.columns:
            anx_mean, anx_sd = anx[var].mean(), anx[var].std()
            no_mean, no_sd = no_anx[var].mean(), no_anx[var].std()
            _, pval = stats.mannwhitneyu(
                anx[var].dropna(), no_anx[var].dropna(), alternative='two-sided'
            )
            rows.append({
                'Characteristic': label,
                'Anxiety': f"{anx_mean:.1f} ({anx_sd:.1f})",
                'No Anxiety': f"{no_mean:.1f} ({no_sd:.1f})",
                'p-value': f"{pval:.4f}" if pval >= 0.0001 else "<0.0001"
            })
    
    # --- Categorical variables ---
    cat_vars = {
        'sex': 'Sex',
        'race': 'Race',
        'age_group': 'Age group',
    }
    
    for var, label in cat_vars.items():
        if var not in df.columns:
            continue
        
        # Chi-square test
        ct = pd.crosstab(df[var], df['has_anxiety'])
        chi2, pval, _, _ = stats.chi2_contingency(ct)
        
        rows.append({
            'Characteristic': label,
            'Anxiety': '',
            'No Anxiety': '',
            'p-value': f"{pval:.4f}" if pval >= 0.0001 else "<0.0001"
        })
        
        for cat in sorted(df[var].dropna().unique()):
            anx_n = (anx[var] == cat).sum()
            anx_pct = 100 * anx_n / len(anx) if len(anx) > 0 else 0
            no_n = (no_anx[var] == cat).sum()
            no_pct = 100 * no_n / len(no_anx) if len(no_anx) > 0 else 0
            rows.append({
                'Characteristic': f"  {cat}",
                'Anxiety': f"{anx_n:,} ({anx_pct:.1f}%)",
                'No Anxiety': f"{no_n:,} ({no_pct:.1f}%)",
                'p-value': ''
            })
    
    # --- CVD condition prevalence ---
    rows.append({
        'Characteristic': 'Cardiovascular conditions',
        'Anxiety': '', 'No Anxiety': '', 'p-value': ''
    })
    
    for cvd, label in [('has_hypertension', '  Hypertension'),
                        ('has_cad', '  CAD'),
                        ('has_afib', '  AFib')]:
        anx_n = anx[cvd].sum()
        anx_pct = 100 * anx_n / len(anx) if len(anx) > 0 else 0
        no_n = no_anx[cvd].sum()
        no_pct = 100 * no_n / len(no_anx) if len(no_anx) > 0 else 0
        
        ct = pd.crosstab(df[cvd], df['has_anxiety'])
        _, pval, _, _ = stats.chi2_contingency(ct)
        
        rows.append({
            'Characteristic': label,
            'Anxiety': f"{anx_n:,} ({anx_pct:.1f}%)",
            'No Anxiety': f"{no_n:,} ({no_pct:.1f}%)",
            'p-value': f"{pval:.4f}" if pval >= 0.0001 else "<0.0001"
        })
    
    # --- CVD count ---
    anx_cvd_mean = anx['cvd_count'].mean() if 'cvd_count' in df.columns else 0
    no_cvd_mean = no_anx['cvd_count'].mean() if 'cvd_count' in df.columns else 0
    if 'cvd_count' in df.columns:
        _, pval = stats.mannwhitneyu(
            anx['cvd_count'].dropna(), no_anx['cvd_count'].dropna()
        )
        rows.append({
            'Characteristic': 'CVD count, mean (SD)',
            'Anxiety': f"{anx['cvd_count'].mean():.2f} ({anx['cvd_count'].std():.2f})",
            'No Anxiety': f"{no_anx['cvd_count'].mean():.2f} ({no_anx['cvd_count'].std():.2f})",
            'p-value': f"{pval:.4f}" if pval >= 0.0001 else "<0.0001"
        })
    
    return pd.DataFrame(rows)


table1 = calc_table1(df)
print(table1.to_string(index=False))

table1.to_csv(os.path.join(OUTPUT_DIR, "table1_characteristics.csv"), index=False)
print(f"\nSaved to: {os.path.join(OUTPUT_DIR, 'table1_characteristics.csv')}")


# ======================================================================
# TABLE 2: SPENDING BY CVD CONDITION × ANXIETY STATUS
# ======================================================================
print("\n" + "=" * 70)
print("TABLE 2: SPENDING BY CVD CONDITION × ANXIETY STATUS")
print("=" * 70)

def spending_comparison(df, cvd_flag, cvd_label):
    """
    Compare spending between anxiety and no-anxiety groups
    within a specific CVD condition.
    Returns a dict of results and the Wilcoxon p-value.
    """
    subset = df[df[cvd_flag] == 1].copy()
    anx = subset[subset['has_anxiety'] == 1]
    no_anx = subset[subset['has_anxiety'] == 0]
    
    results = {'CVD Condition': cvd_label}
    
    # Sample sizes
    results['N (Anxiety)'] = len(anx)
    results['N (No Anxiety)'] = len(no_anx)
    
    # Spending comparisons
    for spend_var, label in [('total_spend', 'Total'),
                              ('inpatient_spend', 'Inpatient'),
                              ('outpatient_spend', 'Outpatient')]:
        if spend_var not in df.columns:
            continue
            
        results[f'{label} Mean (Anxiety)'] = anx[spend_var].mean()
        results[f'{label} Median (Anxiety)'] = anx[spend_var].median()
        results[f'{label} Mean (No Anxiety)'] = no_anx[spend_var].mean()
        results[f'{label} Median (No Anxiety)'] = no_anx[spend_var].median()
        
        # Difference
        results[f'{label} Mean Diff'] = anx[spend_var].mean() - no_anx[spend_var].mean()
        
        # Cost ratio
        if no_anx[spend_var].mean() > 0:
            results[f'{label} Cost Ratio'] = anx[spend_var].mean() / no_anx[spend_var].mean()
        else:
            results[f'{label} Cost Ratio'] = np.nan
        
        # Wilcoxon rank-sum test (Mann-Whitney U)
        if len(anx) > 0 and len(no_anx) > 0:
            stat, pval = stats.mannwhitneyu(
                anx[spend_var].dropna(),
                no_anx[spend_var].dropna(),
                alternative='two-sided'
            )
            results[f'{label} p-value'] = pval
        else:
            results[f'{label} p-value'] = np.nan
    
    # Utilization
    for util_var, label in [('total_claim_count', 'Total Claims'),
                             ('inpatient_claim_count', 'IP Claims'),
                             ('outpatient_claim_count', 'OP Claims')]:
        if util_var in df.columns:
            results[f'{label} Mean (Anxiety)'] = anx[util_var].mean()
            results[f'{label} Mean (No Anxiety)'] = no_anx[util_var].mean()
    
    return results


# Run for each CVD condition
cvd_conditions = [
    ('has_hypertension', 'Hypertension'),
    ('has_cad', 'CAD'),
    ('has_afib', 'AFib'),
]

table2_rows = []
for flag, label in cvd_conditions:
    result = spending_comparison(df, flag, label)
    table2_rows.append(result)

table2 = pd.DataFrame(table2_rows)

# Format for display
display_cols = [
    'CVD Condition', 'N (Anxiety)', 'N (No Anxiety)',
    'Total Mean (Anxiety)', 'Total Mean (No Anxiety)', 'Total Mean Diff',
    'Total Cost Ratio', 'Total p-value',
    'Inpatient Mean (Anxiety)', 'Inpatient Mean (No Anxiety)',
    'Outpatient Mean (Anxiety)', 'Outpatient Mean (No Anxiety)',
]
display_cols = [c for c in display_cols if c in table2.columns]

print("\nSPENDING COMPARISON SUMMARY:")
print("-" * 80)
for _, row in table2.iterrows():
    print(f"\n{row['CVD Condition']}:")
    print(f"  N:  Anxiety={row.get('N (Anxiety)', 'N/A'):,}  |  "
          f"No Anxiety={row.get('N (No Anxiety)', 'N/A'):,}")
    print(f"  Total Mean Spending:")
    print(f"    Anxiety:    ${row.get('Total Mean (Anxiety)', 0):>10,.2f}")
    print(f"    No Anxiety: ${row.get('Total Mean (No Anxiety)', 0):>10,.2f}")
    print(f"    Difference: ${row.get('Total Mean Diff', 0):>10,.2f}")
    cr = row.get('Total Cost Ratio', np.nan)
    print(f"    Cost Ratio: {cr:.3f}" if pd.notna(cr) else "    Cost Ratio: N/A")
    pv = row.get('Total p-value', np.nan)
    pv_str = f"{pv:.4f}" if pd.notna(pv) and pv >= 0.0001 else "<0.0001"
    sig = " ***" if pd.notna(pv) and pv < ALPHA else ""
    print(f"    p-value:    {pv_str}{sig}")

table2.to_csv(os.path.join(OUTPUT_DIR, "table2_spending_by_cvd.csv"), index=False)
print(f"\nSaved to: {os.path.join(OUTPUT_DIR, 'table2_spending_by_cvd.csv')}")


# ======================================================================
# TABLE 3: SPENDING BY AGE GROUP × ANXIETY STATUS (within each CVD)
# ======================================================================
print("\n" + "=" * 70)
print("TABLE 3: SPENDING BY AGE GROUP × ANXIETY STATUS")
print("=" * 70)

table3_rows = []

for cvd_flag, cvd_label in cvd_conditions:
    subset = df[df[cvd_flag] == 1]
    
    for age_grp in sorted(df['age_group'].dropna().unique()):
        age_subset = subset[subset['age_group'] == age_grp]
        anx = age_subset[age_subset['has_anxiety'] == 1]
        no_anx = age_subset[age_subset['has_anxiety'] == 0]
        
        row = {
            'CVD Condition': cvd_label,
            'Age Group': age_grp,
            'N (Anxiety)': len(anx),
            'N (No Anxiety)': len(no_anx),
            'Mean Spend (Anxiety)': anx['total_spend'].mean() if len(anx) > 0 else np.nan,
            'Mean Spend (No Anxiety)': no_anx['total_spend'].mean() if len(no_anx) > 0 else np.nan,
            'Median Spend (Anxiety)': anx['total_spend'].median() if len(anx) > 0 else np.nan,
            'Median Spend (No Anxiety)': no_anx['total_spend'].median() if len(no_anx) > 0 else np.nan,
        }
        
        # Spending gap
        if len(anx) > 0 and len(no_anx) > 0:
            row['Mean Diff'] = anx['total_spend'].mean() - no_anx['total_spend'].mean()
            stat, pval = stats.mannwhitneyu(
                anx['total_spend'].dropna(), no_anx['total_spend'].dropna(),
                alternative='two-sided'
            )
            row['p-value'] = pval
        else:
            row['Mean Diff'] = np.nan
            row['p-value'] = np.nan
        
        table3_rows.append(row)

table3 = pd.DataFrame(table3_rows)

print("\nSPENDING BY AGE GROUP:")
print("-" * 80)
for cvd_label in ['Hypertension', 'CAD', 'AFib']:
    print(f"\n{cvd_label}:")
    sub = table3[table3['CVD Condition'] == cvd_label]
    for _, row in sub.iterrows():
        pv = row['p-value']
        pv_str = (f"{pv:.4f}" if pd.notna(pv) and pv >= 0.0001 
                  else "<0.0001" if pd.notna(pv) else "N/A")
        sig = " *" if pd.notna(pv) and pv < ALPHA else ""
        print(f"  {row['Age Group']:>10s}: "
              f"Anxiety ${row['Mean Spend (Anxiety)']:>9,.0f} vs "
              f"No Anx ${row['Mean Spend (No Anxiety)']:>9,.0f}  "
              f"Diff=${row.get('Mean Diff', 0):>+9,.0f}  "
              f"p={pv_str}{sig}")

table3.to_csv(os.path.join(OUTPUT_DIR, "table3_spending_by_age.csv"), index=False)
print(f"\nSaved to: {os.path.join(OUTPUT_DIR, 'table3_spending_by_age.csv')}")


# ======================================================================
# TABLE 4: STATE-LEVEL SPENDING GAP
# ======================================================================
print("\n" + "=" * 70)
print("TABLE 4: STATE-LEVEL SPENDING GAP")
print("=" * 70)

state_rows = []
for st in sorted(df['state'].dropna().unique()):
    if st == 'Unknown':
        continue
    st_data = df[df['state'] == st]
    anx = st_data[st_data['has_anxiety'] == 1]
    no_anx = st_data[st_data['has_anxiety'] == 0]
    
    if len(anx) < 10 or len(no_anx) < 10:
        continue  # Skip states with very small cell sizes
    
    row = {
        'State': st,
        'N Total': len(st_data),
        'N Anxiety': len(anx),
        'N No Anxiety': len(no_anx),
        'Anxiety Prevalence (%)': 100 * len(anx) / len(st_data),
        'Mean Spend (Anxiety)': anx['total_spend'].mean(),
        'Mean Spend (No Anxiety)': no_anx['total_spend'].mean(),
        'Spending Gap': anx['total_spend'].mean() - no_anx['total_spend'].mean(),
    }
    
    if no_anx['total_spend'].mean() > 0:
        row['Cost Ratio'] = anx['total_spend'].mean() / no_anx['total_spend'].mean()
    
    state_rows.append(row)

table4 = pd.DataFrame(state_rows)
table4 = table4.sort_values('Spending Gap', ascending=False)

print(f"\nTop 10 states by spending gap (Anxiety - No Anxiety):")
print("-" * 70)
for _, row in table4.head(10).iterrows():
    print(f"  {row['State']:>2s}: Gap=${row['Spending Gap']:>+10,.0f}  "
          f"(Anx=${row['Mean Spend (Anxiety)']:>9,.0f}  "
          f"No Anx=${row['Mean Spend (No Anxiety)']:>9,.0f})  "
          f"n_anx={row['N Anxiety']:,}")

table4.to_csv(os.path.join(OUTPUT_DIR, "table4_state_spending_gap.csv"), index=False)
print(f"\nSaved to: {os.path.join(OUTPUT_DIR, 'table4_state_spending_gap.csv')}")


# ======================================================================
# COMPREHENSIVE UNADJUSTED TESTS REPORT
# ======================================================================
print("\n" + "=" * 70)
print("WRITING COMPREHENSIVE TEST RESULTS")
print("=" * 70)

test_path = os.path.join(OUTPUT_DIR, "unadjusted_tests.txt")
with open(test_path, 'w') as f:
    f.write("UNADJUSTED STATISTICAL TESTS\n")
    f.write("=" * 60 + "\n")
    f.write(f"Alpha level: {ALPHA}\n")
    f.write(f"All spending tests: Wilcoxon rank-sum (Mann-Whitney U)\n")
    f.write(f"Categorical tests: Chi-square test of independence\n\n")
    
    # Overall comparison
    anx = df[df['has_anxiety'] == 1]
    no_anx = df[df['has_anxiety'] == 0]
    
    f.write("OVERALL CVD COHORT:\n")
    f.write(f"  N with anxiety:    {len(anx):,}\n")
    f.write(f"  N without anxiety: {len(no_anx):,}\n\n")
    
    stat, pval = stats.mannwhitneyu(
        anx['total_spend'].dropna(), no_anx['total_spend'].dropna()
    )
    f.write(f"  Total spending: U={stat:,.0f}, p={pval:.6f}\n")
    f.write(f"    Anxiety mean:    ${anx['total_spend'].mean():,.2f}\n")
    f.write(f"    No Anxiety mean: ${no_anx['total_spend'].mean():,.2f}\n")
    f.write(f"    Difference:      ${anx['total_spend'].mean() - no_anx['total_spend'].mean():+,.2f}\n\n")
    
    # By CVD condition
    for cvd_flag, cvd_label in cvd_conditions:
        f.write(f"\n{'='*40}\n{cvd_label.upper()}\n{'='*40}\n")
        subset = df[df[cvd_flag] == 1]
        anx_sub = subset[subset['has_anxiety'] == 1]
        no_anx_sub = subset[subset['has_anxiety'] == 0]
        
        f.write(f"  N: {len(anx_sub):,} anxiety, {len(no_anx_sub):,} no anxiety\n\n")
        
        for spend_var, label in [('total_spend', 'Total'),
                                  ('inpatient_spend', 'Inpatient'),
                                  ('outpatient_spend', 'Outpatient')]:
            if spend_var not in df.columns:
                continue
            if len(anx_sub) < 2 or len(no_anx_sub) < 2:
                f.write(f"  {label}: insufficient sample size\n")
                continue
                
            stat, pval = stats.mannwhitneyu(
                anx_sub[spend_var].dropna(), no_anx_sub[spend_var].dropna()
            )
            sig = "***" if pval < 0.001 else "**" if pval < 0.01 else "*" if pval < 0.05 else ""
            
            f.write(f"  {label} spending:\n")
            f.write(f"    U statistic:     {stat:>12,.0f}\n")
            f.write(f"    p-value:         {pval:.6f} {sig}\n")
            f.write(f"    Anxiety mean:    ${anx_sub[spend_var].mean():>12,.2f}\n")
            f.write(f"    No Anxiety mean: ${no_anx_sub[spend_var].mean():>12,.2f}\n")
            f.write(f"    Difference:      ${anx_sub[spend_var].mean() - no_anx_sub[spend_var].mean():>+12,.2f}\n\n")
        
        # Utilization
        for util_var, label in [('total_claim_count', 'Total claims'),
                                 ('inpatient_claim_count', 'IP claims')]:
            if util_var in df.columns and len(anx_sub) > 1 and len(no_anx_sub) > 1:
                stat, pval = stats.mannwhitneyu(
                    anx_sub[util_var].dropna(), no_anx_sub[util_var].dropna()
                )
                sig = "***" if pval < 0.001 else "**" if pval < 0.01 else "*" if pval < 0.05 else ""
                f.write(f"  {label}: Anx mean={anx_sub[util_var].mean():.1f} vs "
                        f"No Anx mean={no_anx_sub[util_var].mean():.1f}, "
                        f"p={pval:.6f} {sig}\n")

print(f"Test results saved to: {test_path}")
print("\n>>> Script 3 complete. Proceed to Script 4 (R) for regression models. <<<")
