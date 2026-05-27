"""
================================================================================
TABLEAU EXHIBIT DATA PREP
================================================================================
Reads analytic_dataset.csv and produces four small CSVs, one per exhibit,
structured for direct drag-and-drop in Tableau.

BEFORE RUNNING:
  - analytic_dataset.csv must exist in OUTPUT_DIR (from Script 2)
  - state_level_analysis.csv must exist in OUTPUT_DIR (from Script 4)
  - model1_gamma_glm.csv must exist in OUTPUT_DIR (from Script 4)

OUTPUTS:
  - exhibit1_spending_by_cvd.csv
  - exhibit2_ip_op_breakdown.csv
  - exhibit3_results_table.csv
  - exhibit4_state_gap.csv
================================================================================
"""

import pandas as pd
import numpy as np
import os

# ==============================================================================
# >>> USER INPUT REQUIRED <<<
# ==============================================================================

OUTPUT_DIR = "./output"  # Path for output files

# ==============================================================================
# END OF USER INPUTS
# ==============================================================================

df = pd.read_csv(os.path.join(OUTPUT_DIR, "analytic_dataset.csv"))
print(f"Loaded {len(df):,} beneficiaries\n")


# ======================================================================
# EXHIBIT 1: Mean Total Spending by Anxiety Status × CVD Condition
# ======================================================================
print("=" * 60)
print("EXHIBIT 1: Spending by CVD Condition × Anxiety Status")
print("=" * 60)

rows = []
for cvd_flag, cvd_label in [('has_hypertension', 'Hypertension'),
                              ('has_cad', 'CAD'),
                              ('has_afib', 'AFib')]:
    subset = df[df[cvd_flag] == 1]
    for anx_val, anx_label in [(1, 'With Anxiety'), (0, 'Without Anxiety')]:
        grp = subset[subset['has_anxiety'] == anx_val]
        rows.append({
            'CVD Condition': cvd_label,
            'Anxiety Status': anx_label,
            'Mean Total Spending': round(grp['total_spend'].mean(), 2),
            'Median Total Spending': round(grp['total_spend'].median(), 2),
            'N': len(grp),
        })

ex1 = pd.DataFrame(rows)

# Add the spending difference as a separate column for labeling
for cvd in ['Hypertension', 'CAD', 'AFib']:
    anx_val = ex1.loc[(ex1['CVD Condition'] == cvd) & 
                       (ex1['Anxiety Status'] == 'With Anxiety'), 
                       'Mean Total Spending'].values[0]
    no_anx_val = ex1.loc[(ex1['CVD Condition'] == cvd) & 
                          (ex1['Anxiety Status'] == 'Without Anxiety'), 
                          'Mean Total Spending'].values[0]
    diff = anx_val - no_anx_val
    ex1.loc[ex1['CVD Condition'] == cvd, 'Spending Difference'] = round(diff, 2)
    ex1.loc[ex1['CVD Condition'] == cvd, 'Pct Difference'] = round(100 * diff / no_anx_val, 1)

ex1.to_csv(os.path.join(OUTPUT_DIR, "exhibit1_spending_by_cvd.csv"), index=False)
print(ex1.to_string(index=False))
print(f"\nSaved to: exhibit1_spending_by_cvd.csv\n")


# ======================================================================
# EXHIBIT 2: Inpatient vs Outpatient Breakdown by Anxiety Status
# ======================================================================
print("=" * 60)
print("EXHIBIT 2: Inpatient vs Outpatient Breakdown")
print("=" * 60)

rows2 = []
for anx_val, anx_label in [(1, 'With Anxiety'), (0, 'Without Anxiety')]:
    grp = df[df['has_anxiety'] == anx_val]
    
    # Overall CVD cohort
    rows2.append({
        'Anxiety Status': anx_label,
        'Spending Type': 'Inpatient',
        'Mean Spending': round(grp['inpatient_spend'].mean(), 2),
        'N': len(grp),
    })
    rows2.append({
        'Anxiety Status': anx_label,
        'Spending Type': 'Outpatient',
        'Mean Spending': round(grp['outpatient_spend'].mean(), 2),
        'N': len(grp),
    })
    # Add carrier if it exists
    if 'carrier_spend' in grp.columns:
        rows2.append({
            'Anxiety Status': anx_label,
            'Spending Type': 'Carrier (Physician)',
            'Mean Spending': round(grp['carrier_spend'].mean(), 2),
            'N': len(grp),
        })

ex2 = pd.DataFrame(rows2)
ex2.to_csv(os.path.join(OUTPUT_DIR, "exhibit2_ip_op_breakdown.csv"), index=False)
print(ex2.to_string(index=False))
print(f"\nSaved to: exhibit2_ip_op_breakdown.csv\n")


# Also create a version broken down by CVD condition (useful alternative)
rows2b = []
for cvd_flag, cvd_label in [('has_hypertension', 'Hypertension'),
                              ('has_cad', 'CAD'),
                              ('has_afib', 'AFib')]:
    subset = df[df[cvd_flag] == 1]
    for anx_val, anx_label in [(1, 'With Anxiety'), (0, 'Without Anxiety')]:
        grp = subset[subset['has_anxiety'] == anx_val]
        
        rows2b.append({
            'CVD Condition': cvd_label,
            'Anxiety Status': anx_label,
            'Spending Type': 'Inpatient',
            'Mean Spending': round(grp['inpatient_spend'].mean(), 2),
            'Pct With Any Claims': round(100 * (grp['inpatient_spend'] > 0).mean(), 1),
        })
        rows2b.append({
            'CVD Condition': cvd_label,
            'Anxiety Status': anx_label,
            'Spending Type': 'Outpatient',
            'Mean Spending': round(grp['outpatient_spend'].mean(), 2),
            'Pct With Any Claims': round(100 * (grp['outpatient_spend'] > 0).mean(), 1),
        })

ex2b = pd.DataFrame(rows2b)
ex2b.to_csv(os.path.join(OUTPUT_DIR, "exhibit2b_ip_op_by_cvd.csv"), index=False)
print("Also saved detailed version: exhibit2b_ip_op_by_cvd.csv\n")


# ======================================================================
# EXHIBIT 3: Compact Results Table
# ======================================================================
print("=" * 60)
print("EXHIBIT 3: Results Table")
print("=" * 60)

# Load Model 1 results for adjusted cost ratios
model1_path = os.path.join(OUTPUT_DIR, "model1_gamma_glm.csv")
if os.path.exists(model1_path):
    model1 = pd.read_csv(model1_path)
    anxiety_rows = model1[model1['term'] == 'has_anxietyAnxiety']
else:
    anxiety_rows = pd.DataFrame()
    print("WARNING: model1_gamma_glm.csv not found. Run Script 4 first.")

rows3 = []
for cvd_flag, cvd_label in [('has_hypertension', 'Hypertension'),
                              ('has_cad', 'CAD'),
                              ('has_afib', 'AFib')]:
    subset = df[df[cvd_flag] == 1]
    anx = subset[subset['has_anxiety'] == 1]
    no_anx = subset[subset['has_anxiety'] == 0]
    
    row = {
        'CVD Condition': cvd_label,
        'N Anxiety': len(anx),
        'N No Anxiety': len(no_anx),
        'Mean Spend Anxiety': round(anx['total_spend'].mean(), 0),
        'Mean Spend No Anxiety': round(no_anx['total_spend'].mean(), 0),
        'Unadjusted Difference': round(anx['total_spend'].mean() - no_anx['total_spend'].mean(), 0),
    }
    
    # Add adjusted cost ratio from Model 1
    if len(anxiety_rows) > 0:
        model_row = anxiety_rows[anxiety_rows['condition'] == cvd_label]
        if len(model_row) > 0:
            cr = model_row['cost_ratio'].values[0]
            cr_lo = model_row['cr_lower'].values[0]
            cr_hi = model_row['cr_upper'].values[0]
            pval = model_row['p.value'].values[0]
            
            row['Adjusted Cost Ratio'] = round(cr, 3)
            row['95% CI'] = f"{cr_lo:.3f}-{cr_hi:.3f}"
            row['p-value'] = '<0.001' if pval < 0.001 else f"{pval:.3f}"
    
    rows3.append(row)

ex3 = pd.DataFrame(rows3)
ex3.to_csv(os.path.join(OUTPUT_DIR, "exhibit3_results_table.csv"), index=False)
print(ex3.to_string(index=False))
print(f"\nSaved to: exhibit3_results_table.csv\n")


# ======================================================================
# EXHIBIT 4: State-Level Spending Gap
# ======================================================================
print("=" * 60)
print("EXHIBIT 4: State-Level Spending Gap")
print("=" * 60)

state_path = os.path.join(OUTPUT_DIR, "state_level_analysis.csv")
if os.path.exists(state_path):
    state_data = pd.read_csv(state_path)
else:
    # Build it from scratch
    print("state_level_analysis.csv not found. Building from analytic_dataset...")
    state_rows = []
    for st in sorted(df['state'].dropna().unique()):
        if st == 'Unknown':
            continue
        st_data = df[df['state'] == st]
        anx = st_data[st_data['has_anxiety'] == 1]
        no_anx = st_data[st_data['has_anxiety'] == 0]
        if len(anx) < 10 or len(no_anx) < 10:
            continue
        state_rows.append({
            'state': st,
            'spending_gap': anx['total_spend'].mean() - no_anx['total_spend'].mean(),
            'mean_spend_Anxiety': anx['total_spend'].mean(),
            'mean_spend_No Anxiety': no_anx['total_spend'].mean(),
            'n_Anxiety': len(anx),
            'n_No Anxiety': len(no_anx),
            'total_n': len(st_data),
        })
    state_data = pd.DataFrame(state_rows)

# Clean up for Tableau
ex4 = state_data[['state', 'spending_gap', 'total_n']].copy()
if 'mean_spend_Anxiety' in state_data.columns:
    ex4['Mean Spend Anxiety'] = state_data['mean_spend_Anxiety'].round(0)
if 'mean_spend_No Anxiety' in state_data.columns:
    ex4['Mean Spend No Anxiety'] = state_data['mean_spend_No Anxiety'].round(0)
if 'cost_ratio' in state_data.columns:
    ex4['Cost Ratio'] = state_data['cost_ratio'].round(3)

ex4 = ex4.rename(columns={
    'state': 'State',
    'spending_gap': 'Spending Gap',
    'total_n': 'Sample Size',
})
ex4 = ex4.sort_values('Spending Gap', ascending=True).reset_index(drop=True)
ex4['Rank'] = range(1, len(ex4) + 1)

ex4.to_csv(os.path.join(OUTPUT_DIR, "exhibit4_state_gap.csv"), index=False)
print(f"States: {len(ex4)}")
print(f"All positive gaps: {(ex4['Spending Gap'] > 0).all()}")
print(f"Range: ${ex4['Spending Gap'].min():,.0f} to ${ex4['Spending Gap'].max():,.0f}")
print(f"\nSaved to: exhibit4_state_gap.csv\n")


print("=" * 60)
print("ALL EXHIBIT FILES READY FOR TABLEAU")
print("=" * 60)
print(f"""
Files in {OUTPUT_DIR}:
  exhibit1_spending_by_cvd.csv    → Exhibit 1 (grouped bar chart)
  exhibit2_ip_op_breakdown.csv    → Exhibit 2 (stacked/paired bars)
  exhibit2b_ip_op_by_cvd.csv     → Exhibit 2 alternative (by CVD condition)
  exhibit3_results_table.csv      → Exhibit 3 (formatted table)
  exhibit4_state_gap.csv          → Exhibit 4 (dot plot / lollipop)
""")
