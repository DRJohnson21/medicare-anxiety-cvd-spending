"""
================================================================================
SCRIPT 2: SPENDING AND UTILIZATION CALCULATION
================================================================================
DataWatch White Paper — Medicare Anxiety & Cardiovascular Spending Analysis

PURPOSE:
  - Calculate per-beneficiary spending from inpatient, outpatient, carrier claims
  - Calculate utilization counts (number of claims, visits)
  - Merge spending onto the cohort file from Script 1
  - Output: analysis-ready dataset with spending and utilization variables

BEFORE RUNNING THIS SCRIPT:
  1. You must have run Script 1 successfully
  2. The cohort file (cvd_cohort_with_flags.csv) must exist in OUTPUT_DIR
  3. Update paths below to match what you used in Script 1

OUTPUTS:
  - analytic_dataset.csv   (final analysis-ready file)
  - spending_summary.txt   (sanity check on spending distributions)
================================================================================
"""

import pandas as pd
import numpy as np
import os
import warnings
warnings.filterwarnings('ignore')

# ==============================================================================
# >>> USER INPUT REQUIRED <<<
# ==============================================================================

# 1. Same paths as Script 1
DATA_DIR = "./data"  # Path to your downloaded CMS SynPUF CSV files
OUTPUT_DIR = "./output"  # Path for output files
SAMPLE_NUM = 1                              # Same as Script 1
ANALYSIS_YEAR = 2009                        # Same as Script 1

# 2. Should carrier claims be included in total spending?
#    Set to True if you successfully downloaded the carrier files.
#    Set to False if carrier files are unavailable (CMS download issues are common).
#    Without carrier: analysis still works but undercounts physician office visits.
#    NOTE: If False, Script 1's carrier-based diagnosis flags will also be skipped.
INCLUDE_CARRIER = True  # You have both Carrier A and B files

# 3. Should we filter to beneficiaries with full-year coverage?
#    Recommended: True (avoids partial-year bias in spending)
REQUIRE_FULL_YEAR_COVERAGE = True

# ==============================================================================
# END OF USER INPUTS
# ==============================================================================

print("=" * 70)
print("STEP 1: LOADING FILES")
print("=" * 70)

# Load cohort from Script 1
cohort_path = os.path.join(OUTPUT_DIR, "cvd_cohort_with_flags.csv")
print(f"Loading cohort: {cohort_path}")
cohort = pd.read_csv(cohort_path)
print(f"  Cohort size: {len(cohort):,}")

# Load claims files (same as Script 1, but we need payment columns as numeric)
ip_file = os.path.join(DATA_DIR, f"DE1_0_2008_to_2010_Inpatient_Claims_Sample_{SAMPLE_NUM}.csv")
op_file = os.path.join(DATA_DIR, f"DE1_0_2008_to_2010_Outpatient_Claims_Sample_{SAMPLE_NUM}.csv")
cr_file_a = os.path.join(DATA_DIR, f"DE1_0_2008_to_2010_Carrier_Claims_Sample_{SAMPLE_NUM}A.csv")
cr_file_b = os.path.join(DATA_DIR, f"DE1_0_2008_to_2010_Carrier_Claims_Sample_{SAMPLE_NUM}B.csv")

print(f"Loading inpatient claims...")
inpatient = pd.read_csv(ip_file, dtype=str)
print(f"  {len(inpatient):,} claims")

print(f"Loading outpatient claims...")
outpatient = pd.read_csv(op_file, dtype=str)
print(f"  {len(outpatient):,} claims")

if INCLUDE_CARRIER:
    print(f"Loading carrier claims (segment A)...")
    carrier_a = pd.read_csv(cr_file_a, dtype=str)
    print(f"  {len(carrier_a):,} claims from segment A")
    
    print(f"Loading carrier claims (segment B)...")
    carrier_b = pd.read_csv(cr_file_b, dtype=str)
    print(f"  {len(carrier_b):,} claims from segment B")
    
    carrier = pd.concat([carrier_a, carrier_b], ignore_index=True)
    print(f"  Combined carrier total: {len(carrier):,} claims")
    del carrier_a, carrier_b


print("\n" + "=" * 70)
print("STEP 2: FILTERING CLAIMS TO ANALYSIS YEAR")
print("=" * 70)

def filter_claims_to_year(claims_df, year, date_col):
    """
    Filter claims to those with a service date in the specified year.
    SynPUF dates are in YYYYMMDD format (as strings).
    """
    claims_df[date_col] = claims_df[date_col].astype(str).str.strip()
    year_str = str(year)
    mask = claims_df[date_col].str[:4] == year_str
    filtered = claims_df[mask].copy()
    print(f"  Filtered {date_col} to {year}: {len(filtered):,} of {len(claims_df):,} claims")
    return filtered

# Inpatient: use CLM_FROM_DT (claim start date)
inpatient = filter_claims_to_year(inpatient, ANALYSIS_YEAR, 'CLM_FROM_DT')

# Outpatient: use CLM_FROM_DT
outpatient = filter_claims_to_year(outpatient, ANALYSIS_YEAR, 'CLM_FROM_DT')

# Carrier: use CLM_FROM_DT
if INCLUDE_CARRIER:
    carrier = filter_claims_to_year(carrier, ANALYSIS_YEAR, 'CLM_FROM_DT')


print("\n" + "=" * 70)
print("STEP 3: CALCULATING SPENDING PER BENEFICIARY")
print("=" * 70)

def calc_spending(claims_df, id_col, pay_cols, label):
    """
    Sum payment columns per beneficiary.
    Returns a DataFrame with DESYNPUF_ID, spend, and claim_count.
    """
    # Strip any whitespace from column names (common CSV issue)
    claims_df.columns = claims_df.columns.str.strip()
    
    # Show available payment-related columns for debugging
    amt_cols = [c for c in claims_df.columns if 'AMT' in c.upper() or 'PMT' in c.upper()]
    print(f"  Available payment columns in {label}: {amt_cols}")
    
    # Convert payment columns to numeric
    for col in pay_cols:
        if col in claims_df.columns:
            claims_df[col] = pd.to_numeric(claims_df[col], errors='coerce').fillna(0)
    
    # Use only columns that exist
    valid_pay_cols = [c for c in pay_cols if c in claims_df.columns]
    
    if not valid_pay_cols:
        print(f"  WARNING: None of {pay_cols} found for {label}")
        print(f"  >>> Check the column names above and update the pay_cols list <<<")
        # Return zeros so downstream code doesn't break
        unique_ids = claims_df[id_col].unique()
        fallback = pd.DataFrame({
            id_col: unique_ids,
            f'{label}_spend': 0.0,
            f'{label}_claim_count': claims_df.groupby(id_col).size().reindex(unique_ids, fill_value=0).values
        })
        return fallback
    
    claims_df[f'{label}_claim_total'] = claims_df[valid_pay_cols].sum(axis=1)
    
    spend = claims_df.groupby(id_col).agg(
        spend=(f'{label}_claim_total', 'sum'),
        claim_count=(f'{label}_claim_total', 'count')
    ).reset_index()
    
    spend.columns = [id_col, f'{label}_spend', f'{label}_claim_count']
    
    print(f"  {label}: {len(spend):,} beneficiaries, "
          f"mean=${spend[f'{label}_spend'].mean():,.0f}, "
          f"median=${spend[f'{label}_spend'].median():,.0f}")
    
    return spend


# --- Inpatient spending ---
# Key payment columns in SynPUF inpatient:
#   CLM_PMT_AMT         = Claim payment amount
#   NCH_PRMRY_PYR_CLM_PD_AMT = Primary payer paid
#   CLM_PASS_THRU_PER_DIEM_AMT = Per diem pass-through
#   NCH_BENE_IP_DDCTBL_AMT  = Beneficiary deductible
#   NCH_BENE_PTA_COINSRNC_LBLTY_AM = Beneficiary coinsurance
print("Calculating INPATIENT spending...")
ip_spend = calc_spending(
    inpatient, 'DESYNPUF_ID',
    ['CLM_PMT_AMT', 'NCH_PRMRY_PYR_CLM_PD_AMT'],
    'inpatient'
)

# Also compute length of stay
if 'CLM_FROM_DT' in inpatient.columns and 'CLM_THRU_DT' in inpatient.columns:
    inpatient['CLM_FROM_DT_parsed'] = pd.to_datetime(inpatient['CLM_FROM_DT'], format='%Y%m%d', errors='coerce')
    inpatient['CLM_THRU_DT_parsed'] = pd.to_datetime(inpatient['CLM_THRU_DT'], format='%Y%m%d', errors='coerce')
    inpatient['los'] = (inpatient['CLM_THRU_DT_parsed'] - inpatient['CLM_FROM_DT_parsed']).dt.days
    
    ip_los = inpatient.groupby('DESYNPUF_ID').agg(
        total_los=('los', 'sum'),
        ip_admissions=('los', 'count')
    ).reset_index()
    ip_spend = ip_spend.merge(ip_los, on='DESYNPUF_ID', how='left')

# --- Outpatient spending ---
print("\nCalculating OUTPATIENT spending...")
op_spend = calc_spending(
    outpatient, 'DESYNPUF_ID',
    ['CLM_PMT_AMT', 'NCH_PRMRY_PYR_CLM_PD_AMT'],
    'outpatient'
)

# --- Carrier spending ---
if INCLUDE_CARRIER:
    print("\nCalculating CARRIER spending...")
    # The carrier file has NO claim-level CLM_PMT_AMT. Instead, payments are
    # at the service line level: LINE_NCH_PMT_AMT_1 through LINE_NCH_PMT_AMT_13.
    # We sum across all 13 line columns to get a per-claim total, then aggregate
    # to the beneficiary level.
    
    carrier.columns = carrier.columns.str.strip()
    
    # Find all LINE_NCH_PMT_AMT columns (the Medicare payment per service line)
    line_pmt_cols = [c for c in carrier.columns if c.startswith('LINE_NCH_PMT_AMT_')]
    print(f"  Found {len(line_pmt_cols)} line payment columns: {line_pmt_cols[:3]}...{line_pmt_cols[-1]}")
    
    # Convert to numeric
    for col in line_pmt_cols:
        carrier[col] = pd.to_numeric(carrier[col], errors='coerce').fillna(0)
    
    # Sum across all service lines within each claim to get per-claim total
    carrier['carrier_claim_total'] = carrier[line_pmt_cols].sum(axis=1)
    
    # Aggregate to beneficiary level
    cr_spend = carrier.groupby('DESYNPUF_ID').agg(
        carrier_spend=('carrier_claim_total', 'sum'),
        carrier_claim_count=('carrier_claim_total', 'count')
    ).reset_index()
    
    print(f"  Carrier: {len(cr_spend):,} beneficiaries, "
          f"mean=${cr_spend['carrier_spend'].mean():,.0f}, "
          f"median=${cr_spend['carrier_spend'].median():,.0f}")


print("\n" + "=" * 70)
print("STEP 4: MERGING SPENDING ONTO COHORT")
print("=" * 70)

# Merge inpatient spending
cohort = cohort.merge(ip_spend, on='DESYNPUF_ID', how='left')

# Merge outpatient spending
cohort = cohort.merge(op_spend, on='DESYNPUF_ID', how='left')

# Merge carrier spending
if INCLUDE_CARRIER:
    cohort = cohort.merge(cr_spend, on='DESYNPUF_ID', how='left')

# Fill NaN spending with 0 (beneficiary had no claims of that type)
spend_cols = [c for c in cohort.columns if '_spend' in c or '_claim_count' in c 
              or c in ['total_los', 'ip_admissions']]
cohort[spend_cols] = cohort[spend_cols].fillna(0)

# Calculate total spending
cohort['total_spend'] = cohort['inpatient_spend'] + cohort['outpatient_spend']
if INCLUDE_CARRIER:
    cohort['total_spend'] += cohort['carrier_spend']

# Total claim count
cohort['total_claim_count'] = cohort['inpatient_claim_count'] + cohort['outpatient_claim_count']
if INCLUDE_CARRIER:
    cohort['total_claim_count'] += cohort['carrier_claim_count']

print(f"Cohort with spending: {len(cohort):,} rows")
print(f"\nSpending columns: {[c for c in cohort.columns if 'spend' in c]}")
print(f"Utilization columns: {[c for c in cohort.columns if 'count' in c or 'los' in c or 'admission' in c]}")


print("\n" + "=" * 70)
print("STEP 5: OPTIONAL — FULL-YEAR COVERAGE FILTER")
print("=" * 70)

if REQUIRE_FULL_YEAR_COVERAGE:
    before = len(cohort)
    
    # Part A coverage = 12 months AND Part B coverage = 12 months
    # AND HMO months = 0 (HMO enrollees don't have FFS claims)
    if 'BENE_HI_CVRAGE_TOT_MONS' in cohort.columns:
        cohort['BENE_HI_CVRAGE_TOT_MONS'] = pd.to_numeric(
            cohort['BENE_HI_CVRAGE_TOT_MONS'], errors='coerce')
        cohort = cohort[cohort['BENE_HI_CVRAGE_TOT_MONS'] == 12]
    
    if 'BENE_SMI_CVRAGE_TOT_MONS' in cohort.columns:
        cohort['BENE_SMI_CVRAGE_TOT_MONS'] = pd.to_numeric(
            cohort['BENE_SMI_CVRAGE_TOT_MONS'], errors='coerce')
        cohort = cohort[cohort['BENE_SMI_CVRAGE_TOT_MONS'] == 12]
    
    if 'BENE_HMO_CVRAGE_TOT_MONS' in cohort.columns:
        cohort['BENE_HMO_CVRAGE_TOT_MONS'] = pd.to_numeric(
            cohort['BENE_HMO_CVRAGE_TOT_MONS'], errors='coerce')
        cohort = cohort[cohort['BENE_HMO_CVRAGE_TOT_MONS'] == 0]
    
    after = len(cohort)
    print(f"Full-year FFS filter: {before:,} → {after:,} ({before - after:,} excluded)")
else:
    print("Skipping full-year coverage filter (REQUIRE_FULL_YEAR_COVERAGE = False)")


print("\n" + "=" * 70)
print("STEP 6: CREATING DERIVED ANALYSIS VARIABLES")
print("=" * 70)

# --- Primary CVD condition (for stratified analysis) ---
# A beneficiary may have multiple CVDs. Create a "primary CVD" variable
# using a hierarchy: AFib > CAD > Hypertension (rarest to most common)
conditions = []
for _, row in cohort.iterrows():
    if row['has_afib'] == 1:
        conditions.append('AFib')
    elif row['has_cad'] == 1:
        conditions.append('CAD')
    elif row['has_hypertension'] == 1:
        conditions.append('Hypertension')
    else:
        conditions.append('Other')
cohort['primary_cvd'] = conditions

# Alternative: create a column for each CVD-anxiety combination
# This allows you to analyze "HTN+Anxiety" vs "HTN only" etc.
for cvd in ['hypertension', 'cad', 'afib']:
    cohort[f'{cvd}_anxiety'] = (
        (cohort[f'has_{cvd}'] == 1) & (cohort['has_anxiety'] == 1)
    ).astype(int)
    cohort[f'{cvd}_no_anxiety'] = (
        (cohort[f'has_{cvd}'] == 1) & (cohort['has_anxiety'] == 0)
    ).astype(int)

# --- Log-transformed spending (for regression) ---
cohort['log_total_spend'] = np.log1p(cohort['total_spend'])
cohort['log_inpatient_spend'] = np.log1p(cohort['inpatient_spend'])
cohort['log_outpatient_spend'] = np.log1p(cohort['outpatient_spend'])

# --- Spending indicator (any spending vs none) ---
cohort['any_inpatient'] = (cohort['inpatient_spend'] > 0).astype(int)
cohort['any_outpatient'] = (cohort['outpatient_spend'] > 0).astype(int)

# --- CVD count (number of cardiovascular conditions, 1-3) ---
cohort['cvd_count'] = (
    cohort['has_hypertension'] + cohort['has_cad'] + cohort['has_afib']
)

print(f"Primary CVD distribution:")
print(cohort['primary_cvd'].value_counts().to_string())
print(f"\nCVD count distribution:")
print(cohort['cvd_count'].value_counts().sort_index().to_string())


print("\n" + "=" * 70)
print("STEP 7: SAVING ANALYTIC DATASET")
print("=" * 70)

out_path = os.path.join(OUTPUT_DIR, "analytic_dataset.csv")
cohort.to_csv(out_path, index=False)
print(f"Analytic dataset saved to: {out_path}")
print(f"  Rows:    {len(cohort):,}")
print(f"  Columns: {len(cohort.columns)}")

# --- Save spending summary ---
summary_path = os.path.join(OUTPUT_DIR, "spending_summary.txt")
with open(summary_path, 'w') as f:
    f.write("SPENDING SUMMARY BY ANXIETY STATUS\n")
    f.write("=" * 60 + "\n\n")
    
    for cvd in ['hypertension', 'cad', 'afib']:
        f.write(f"\n--- {cvd.upper()} ---\n")
        subset = cohort[cohort[f'has_{cvd}'] == 1]
        
        for anx_label, anx_val in [('With Anxiety', 1), ('Without Anxiety', 0)]:
            grp = subset[subset['has_anxiety'] == anx_val]
            f.write(f"\n  {anx_label} (n={len(grp):,}):\n")
            f.write(f"    Mean total spend:      ${grp['total_spend'].mean():>10,.2f}\n")
            f.write(f"    Median total spend:    ${grp['total_spend'].median():>10,.2f}\n")
            f.write(f"    Mean inpatient spend:  ${grp['inpatient_spend'].mean():>10,.2f}\n")
            f.write(f"    Mean outpatient spend: ${grp['outpatient_spend'].mean():>10,.2f}\n")
            if INCLUDE_CARRIER:
                f.write(f"    Mean carrier spend:    ${grp['carrier_spend'].mean():>10,.2f}\n")
            f.write(f"    Mean total claims:     {grp['total_claim_count'].mean():>10.1f}\n")
            if 'ip_admissions' in grp.columns:
                f.write(f"    Mean IP admissions:    {grp['ip_admissions'].mean():>10.1f}\n")

print(f"Spending summary saved to: {summary_path}")
print("\n>>> Script 2 complete. Proceed to Script 3 for descriptive analysis. <<<")
