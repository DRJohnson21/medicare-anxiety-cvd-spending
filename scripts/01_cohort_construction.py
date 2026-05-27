"""
================================================================================
SCRIPT 1: DATA LOADING, DIAGNOSIS FLAGGING, AND COHORT CONSTRUCTION
================================================================================
DataWatch White Paper — Medicare Anxiety & Cardiovascular Spending Analysis

PURPOSE:
  - Load CMS SynPUF beneficiary and claims files
  - Flag beneficiaries with hypertension, CAD, AFib, and anxiety
  - Build the cardiovascular cohort with anxiety exposure variable
  - Output: cohort CSV ready for spending analysis

BEFORE RUNNING THIS SCRIPT:
  1. Download the CMS DE-SynPUF data from:
     https://www.cms.gov/Research-Statistics-Data-and-Systems/Downloadable-Public-Use-Files/SynPUFs/DE_Syn_PUF
  2. You need these files from your chosen sample (e.g., Sample 1):
       - DE1_0_2008_Beneficiary_Summary_File_Sample_1.csv
       - DE1_0_2009_Beneficiary_Summary_File_Sample_1.csv
       - DE1_0_2010_Beneficiary_Summary_File_Sample_1.csv
       - DE1_0_2008_to_2010_Inpatient_Claims_Sample_1.csv
       - DE1_0_2008_to_2010_Outpatient_Claims_Sample_1.csv
       - DE1_0_2008_to_2010_Carrier_Claims_Sample_1.csv
  3. Place all files in a single folder
  4. Update the DATA_DIR path below

OUTPUTS:
  - cvd_cohort_with_flags.csv  (beneficiary-level analytic file)
  - cohort_summary.txt         (quick summary stats for sanity check)
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

# 1. Set the path to the folder containing your downloaded SynPUF CSV files
DATA_DIR = "./data"  # Path to your downloaded CMS SynPUF CSV files

# 2. Which sample number are you using? (1 through 20)
SAMPLE_NUM = 1

# 3. Which year do you want as your primary analysis year?
#    The SynPUF has 2008, 2009, 2010. Pick one as the index year.
#    2009 is recommended (full year of claims before and after).
ANALYSIS_YEAR = 2009

# 4. Where should output files be saved?
OUTPUT_DIR = "./output"  # Path for output files

# 5. Do you have the carrier claims files?
#    Set to False if you were unable to download them from CMS.
#    The analysis will still work using inpatient + outpatient claims only.
INCLUDE_CARRIER = True  # You have both Carrier A and B files

# ==============================================================================
# END OF USER INPUTS — the rest runs automatically
# ==============================================================================

os.makedirs(OUTPUT_DIR, exist_ok=True)

print("=" * 70)
print("STEP 1: LOADING BENEFICIARY SUMMARY FILE")
print("=" * 70)

bene_file = os.path.join(
    DATA_DIR,
    f"DE1_0_{ANALYSIS_YEAR}_Beneficiary_Summary_File_Sample_{SAMPLE_NUM}.csv"
)
print(f"Loading: {bene_file}")
bene = pd.read_csv(bene_file)
print(f"  Loaded {len(bene):,} beneficiaries")
print(f"  Columns: {list(bene.columns)}\n")


print("=" * 70)
print("STEP 2: LOADING CLAIMS FILES")
print("=" * 70)

# Inpatient claims
ip_file = os.path.join(
    DATA_DIR,
    f"DE1_0_2008_to_2010_Inpatient_Claims_Sample_{SAMPLE_NUM}.csv"
)
print(f"Loading inpatient: {ip_file}")
inpatient = pd.read_csv(ip_file, dtype=str)
print(f"  Loaded {len(inpatient):,} inpatient claims")

# Outpatient claims
op_file = os.path.join(
    DATA_DIR,
    f"DE1_0_2008_to_2010_Outpatient_Claims_Sample_{SAMPLE_NUM}.csv"
)
print(f"Loading outpatient: {op_file}")
outpatient = pd.read_csv(op_file, dtype=str)
print(f"  Loaded {len(outpatient):,} outpatient claims")

# Carrier claims — CMS splits these into two files: Segment A and Segment B
if INCLUDE_CARRIER:
    cr_file_a = os.path.join(
        DATA_DIR,
        f"DE1_0_2008_to_2010_Carrier_Claims_Sample_{SAMPLE_NUM}A.csv"
    )
    cr_file_b = os.path.join(
        DATA_DIR,
        f"DE1_0_2008_to_2010_Carrier_Claims_Sample_{SAMPLE_NUM}B.csv"
    )
    
    print(f"Loading carrier segment A: {cr_file_a}")
    carrier_a = pd.read_csv(cr_file_a, dtype=str)
    print(f"  Loaded {len(carrier_a):,} claims from segment A")
    
    print(f"Loading carrier segment B: {cr_file_b}")
    carrier_b = pd.read_csv(cr_file_b, dtype=str)
    print(f"  Loaded {len(carrier_b):,} claims from segment B")
    
    carrier = pd.concat([carrier_a, carrier_b], ignore_index=True)
    print(f"  Combined carrier total: {len(carrier):,} claims\n")
    
    # Free memory
    del carrier_a, carrier_b
else:
    carrier = None
    print("Carrier claims: SKIPPED (INCLUDE_CARRIER = False)\n")


print("=" * 70)
print("STEP 3: DEFINING ICD-9 DIAGNOSIS CODE SETS")
print("=" * 70)

# -----------------------------------------------------------------------
# ICD-9-CM Code Definitions
# -----------------------------------------------------------------------
# NOTE: SynPUF uses ICD-9 codes (data is from 2008-2010, pre-ICD-10 era).
# Codes are stored WITHOUT decimal points in the SynPUF (e.g., "4011" not "401.1").
#
# If you want to add or remove codes, edit the lists below.
# -----------------------------------------------------------------------

# Hypertension: 401.x through 405.x
HYPERTENSION_CODES = [
    '4010', '4011', '4019',                          # Essential HTN
    '4020', '40200', '40201', '4021', '40210',        # Hypertensive heart disease
    '40211', '4029', '40290', '40291',
    '4030', '40300', '40301', '4031', '40310',        # Hypertensive CKD
    '40311', '4039', '40390', '40391',
    '4040', '40400', '40401', '40402', '40403',       # Hypertensive heart + CKD
    '4041', '40410', '40411', '40412', '40413',
    '4049', '40490', '40491', '40492', '40493',
    '4050', '40501', '40509', '4051', '40511',        # Secondary HTN
    '40519', '4059', '40591', '40599',
]

# Coronary artery disease (CAD) / Ischemic heart disease
CAD_CODES = [
    '41400', '41401', '41402', '41403', '41404',     # Coronary atherosclerosis
    '41405', '41406', '41407', '4141', '4148', '4149',
    '41100', '41101', '4111', '41181', '41189',       # Acute coronary syndromes
    '4130', '4131', '4139',                            # Angina pectoris
]

# Atrial fibrillation
AFIB_CODES = [
    '42731',                                           # AFib
    '42732',                                           # Atrial flutter
]

# Anxiety disorders
ANXIETY_CODES = [
    '30000', '30001', '30002', '30009',               # Anxiety states
    '30010',                                           # Hysteria, unspecified
    '30020', '30021', '30022', '30023', '30029',      # Phobias
    '3003',                                            # OCD
    '30924',                                           # Adjustment disorder w/ anxiety
    '29384',                                           # Anxiety due to general medical condition
    '3007',                                            # Hypochondriasis
    '30089',                                           # Other neurotic disorders
    '3009',                                            # Neurotic disorder NOS
    '30981',                                           # Prolonged PTSD
    '3080', '3081', '3082', '3083', '3084', '3089',   # Acute stress reaction
]

print("Diagnosis code sets defined:")
print(f"  Hypertension codes: {len(HYPERTENSION_CODES)}")
print(f"  CAD codes:          {len(CAD_CODES)}")
print(f"  AFib codes:         {len(AFIB_CODES)}")
print(f"  Anxiety codes:      {len(ANXIETY_CODES)}")
print()


print("=" * 70)
print("STEP 4: FLAGGING DIAGNOSES FROM CLAIMS")
print("=" * 70)

def flag_diagnoses_from_claims(claims_df, code_set, label):
    """
    Scan all ICD-9 diagnosis columns in a claims dataframe.
    Return a set of beneficiary IDs that have at least one matching code.
    
    SynPUF diagnosis columns follow the pattern:
      Inpatient:  ICD9_DGNS_CD_1 through ICD9_DGNS_CD_10, ADMTNG_ICD9_DGNS_CD
      Outpatient: ICD9_DGNS_CD_1 through ICD9_DGNS_CD_10
      Carrier:    ICD9_DGNS_CD_1 through ICD9_DGNS_CD_8, LINE_ICD9_DGNS_CD_1..4
    """
    # Find all diagnosis code columns
    dx_cols = [c for c in claims_df.columns 
               if 'ICD9_DGNS_CD' in c or 'DGNS_CD' in c]
    
    if not dx_cols:
        print(f"  WARNING: No diagnosis columns found in claims for {label}")
        return set()
    
    # Build a mask: True for any row with a matching code in any dx column
    mask = pd.Series(False, index=claims_df.index)
    for col in dx_cols:
        mask = mask | claims_df[col].astype(str).str.strip().isin(code_set)
    
    matched_ids = set(claims_df.loc[mask, 'DESYNPUF_ID'].unique())
    print(f"  {label}: found {len(matched_ids):,} beneficiaries across {mask.sum():,} claims")
    return matched_ids


# --- Flag from INPATIENT claims ---
print("\nScanning INPATIENT claims...")
ip_htn  = flag_diagnoses_from_claims(inpatient, HYPERTENSION_CODES, "Hypertension")
ip_cad  = flag_diagnoses_from_claims(inpatient, CAD_CODES, "CAD")
ip_afib = flag_diagnoses_from_claims(inpatient, AFIB_CODES, "AFib")
ip_anx  = flag_diagnoses_from_claims(inpatient, ANXIETY_CODES, "Anxiety")

# --- Flag from OUTPATIENT claims ---
print("\nScanning OUTPATIENT claims...")
op_htn  = flag_diagnoses_from_claims(outpatient, HYPERTENSION_CODES, "Hypertension")
op_cad  = flag_diagnoses_from_claims(outpatient, CAD_CODES, "CAD")
op_afib = flag_diagnoses_from_claims(outpatient, AFIB_CODES, "AFib")
op_anx  = flag_diagnoses_from_claims(outpatient, ANXIETY_CODES, "Anxiety")

# --- Flag from CARRIER claims ---
if INCLUDE_CARRIER and carrier is not None:
    print("\nScanning CARRIER claims...")
    cr_htn  = flag_diagnoses_from_claims(carrier, HYPERTENSION_CODES, "Hypertension")
    cr_cad  = flag_diagnoses_from_claims(carrier, CAD_CODES, "CAD")
    cr_afib = flag_diagnoses_from_claims(carrier, AFIB_CODES, "AFib")
    cr_anx  = flag_diagnoses_from_claims(carrier, ANXIETY_CODES, "Anxiety")
else:
    print("\nSkipping CARRIER claims (not available)...")
    cr_htn = cr_cad = cr_afib = cr_anx = set()

# --- Combine across all claim types ---
print("\nCombining flags across all claim types...")
all_htn  = ip_htn  | op_htn  | cr_htn
all_cad  = ip_cad  | op_cad  | cr_cad
all_afib = ip_afib | op_afib | cr_afib
all_anx  = ip_anx  | op_anx  | cr_anx

print(f"  Total Hypertension: {len(all_htn):,}")
print(f"  Total CAD:          {len(all_cad):,}")
print(f"  Total AFib:         {len(all_afib):,}")
print(f"  Total Anxiety:      {len(all_anx):,}")


print("\n" + "=" * 70)
print("STEP 5: SUPPLEMENTING WITH BENEFICIARY SUMMARY CHRONIC CONDITION FLAGS")
print("=" * 70)

# The beneficiary summary file has pre-computed chronic condition flags.
# Values: 1 = yes, 2 = no (CMS convention — note: 1 means HAS the condition)
# We'll use these as a supplement to claims-based flags.

# Map SynPUF column names to our conditions:
#   SP_ISCHMCHT = Ischemic Heart Disease (covers most CAD)
#   SP_CHRNKIDN = Chronic Kidney Disease (not needed but FYI)
#   SP_CNCR     = Cancer, etc.
# NOTE: There is NO pre-built anxiety flag in the beneficiary file.

bene_flag_cols = {
    'SP_ISCHMCHT': 'bene_flag_cad',   # Ischemic heart disease
}

# Check which chronic condition columns exist
available_cc = [c for c in bene.columns if c.startswith('SP_')]
print(f"Available chronic condition columns: {available_cc}")

# Add bene-file CAD flag (1 = yes in CMS convention)
if 'SP_ISCHMCHT' in bene.columns:
    bene_cad_ids = set(bene.loc[bene['SP_ISCHMCHT'] == 1, 'DESYNPUF_ID'])
    all_cad = all_cad | bene_cad_ids
    print(f"  After adding bene-file ischemic heart flag, CAD total: {len(all_cad):,}")

# Check for atrial fibrillation flag
if 'SP_ATRLFB' in bene.columns:
    bene_afib_ids = set(bene.loc[bene['SP_ATRLFB'] == 1, 'DESYNPUF_ID'])
    all_afib = all_afib | bene_afib_ids
    print(f"  After adding bene-file AFib flag, AFib total: {len(all_afib):,}")


print("\n" + "=" * 70)
print("STEP 6: BUILDING THE ANALYTIC COHORT")
print("=" * 70)

# Apply flags to beneficiary dataframe
bene['has_hypertension'] = bene['DESYNPUF_ID'].isin(all_htn).astype(int)
bene['has_cad']          = bene['DESYNPUF_ID'].isin(all_cad).astype(int)
bene['has_afib']         = bene['DESYNPUF_ID'].isin(all_afib).astype(int)
bene['has_anxiety']      = bene['DESYNPUF_ID'].isin(all_anx).astype(int)

# Any cardiovascular condition
bene['has_any_cvd'] = (
    (bene['has_hypertension'] == 1) |
    (bene['has_cad'] == 1) |
    (bene['has_afib'] == 1)
).astype(int)

# Filter to CVD cohort only
cvd_cohort = bene[bene['has_any_cvd'] == 1].copy()
print(f"Total beneficiaries in file:      {len(bene):,}")
print(f"Beneficiaries with any CVD:       {len(cvd_cohort):,}")
print(f"  - With hypertension:            {cvd_cohort['has_hypertension'].sum():,}")
print(f"  - With CAD:                     {cvd_cohort['has_cad'].sum():,}")
print(f"  - With AFib:                    {cvd_cohort['has_afib'].sum():,}")
print(f"  - With anxiety (exposure):      {cvd_cohort['has_anxiety'].sum():,}")
print(f"  - Without anxiety (comparator): {(cvd_cohort['has_anxiety'] == 0).sum():,}")


print("\n" + "=" * 70)
print("STEP 7: CREATING DEMOGRAPHIC VARIABLES")
print("=" * 70)

# --- Age ---
# BENE_BIRTH_DT is in format YYYYMMDD (as integer or string)
cvd_cohort['BENE_BIRTH_DT'] = cvd_cohort['BENE_BIRTH_DT'].astype(str)
cvd_cohort['birth_year'] = cvd_cohort['BENE_BIRTH_DT'].str[:4].astype(int)
cvd_cohort['age'] = ANALYSIS_YEAR - cvd_cohort['birth_year']

cvd_cohort['age_group'] = pd.cut(
    cvd_cohort['age'],
    bins=[0, 64, 74, 84, 200],
    labels=['Under 65', '65-74', '75-84', '85+'],
    right=True
)

print("Age distribution:")
print(cvd_cohort['age_group'].value_counts().sort_index().to_string())

# --- Sex ---
# BENE_SEX_IDENT_CD: 1 = Male, 2 = Female
cvd_cohort['sex'] = cvd_cohort['BENE_SEX_IDENT_CD'].map({1: 'Male', 2: 'Female'})
print(f"\nSex distribution:")
print(cvd_cohort['sex'].value_counts().to_string())

# --- Race ---
# BENE_RACE_CD: 1=White, 2=Black, 3=Other, 5=Hispanic
cvd_cohort['race'] = cvd_cohort['BENE_RACE_CD'].map({
    1: 'White', 2: 'Black', 3: 'Other', 5: 'Hispanic'
})
cvd_cohort['race'] = cvd_cohort['race'].fillna('Other')
print(f"\nRace distribution:")
print(cvd_cohort['race'].value_counts().to_string())

# --- State ---
# SP_STATE_CODE is a numeric code. We map to state abbreviations.
# Full FIPS mapping (SynPUF uses SSA state codes, which differ from FIPS)
# The SynPUF documentation lists the SSA-to-state mapping.
# Below is the standard SSA state code crosswalk:

SSA_STATE_MAP = {
    1: 'AL', 2: 'AK', 3: 'AZ', 4: 'AR', 5: 'CA', 6: 'CO', 7: 'CT',
    8: 'DE', 9: 'DC', 10: 'FL', 11: 'GA', 12: 'HI', 13: 'ID', 14: 'IL',
    15: 'IN', 16: 'IA', 17: 'KS', 18: 'KY', 19: 'LA', 20: 'ME',
    21: 'MD', 22: 'MA', 23: 'MI', 24: 'MN', 25: 'MS', 26: 'MO',
    27: 'MT', 28: 'NE', 29: 'NV', 30: 'NH', 31: 'NJ', 32: 'NM',
    33: 'NY', 34: 'NC', 35: 'ND', 36: 'OH', 37: 'OK', 38: 'OR',
    39: 'PA', 40: 'PR', 41: 'RI', 42: 'SC', 43: 'SD', 44: 'TN',
    45: 'TX', 46: 'UT', 47: 'VT', 48: 'VA', 49: 'VI', 50: 'WA',
    51: 'WV', 52: 'WI', 53: 'WY',
}

cvd_cohort['state'] = cvd_cohort['SP_STATE_CODE'].map(SSA_STATE_MAP)
cvd_cohort['state'] = cvd_cohort['state'].fillna('Unknown')
print(f"\nTop 10 states by beneficiary count:")
print(cvd_cohort['state'].value_counts().head(10).to_string())


# --- Comorbidity count (for use as a covariate) ---
# Count how many CMS chronic condition flags each person has
cc_flag_cols = [c for c in bene.columns if c.startswith('SP_') and c != 'SP_STATE_CODE']
# CMS: 1 = has condition, 2 = does not
for col in cc_flag_cols:
    if col in cvd_cohort.columns:
        cvd_cohort[col] = pd.to_numeric(cvd_cohort[col], errors='coerce')

cvd_cohort['comorbidity_count'] = 0
for col in cc_flag_cols:
    if col in cvd_cohort.columns:
        cvd_cohort['comorbidity_count'] += (cvd_cohort[col] == 1).astype(int)

print(f"\nComorbidity count distribution:")
print(cvd_cohort['comorbidity_count'].describe().to_string())


print("\n" + "=" * 70)
print("STEP 8: SAVING COHORT FILE")
print("=" * 70)

# Select columns to keep
keep_cols = [
    'DESYNPUF_ID',
    'has_hypertension', 'has_cad', 'has_afib', 'has_anxiety', 'has_any_cvd',
    'age', 'age_group', 'sex', 'race', 'state',
    'BENE_SEX_IDENT_CD', 'BENE_RACE_CD', 'SP_STATE_CODE',
    'comorbidity_count',
    # Keep coverage months for potential exclusion criteria
    'BENE_HI_CVRAGE_TOT_MONS',   # Part A months
    'BENE_SMI_CVRAGE_TOT_MONS',  # Part B months
    'BENE_HMO_CVRAGE_TOT_MONS',  # HMO months
]

# Only keep columns that actually exist
keep_cols = [c for c in keep_cols if c in cvd_cohort.columns]
cohort_out = cvd_cohort[keep_cols].copy()

outpath = os.path.join(OUTPUT_DIR, "cvd_cohort_with_flags.csv")
cohort_out.to_csv(outpath, index=False)
print(f"Cohort saved to: {outpath}")
print(f"  Rows: {len(cohort_out):,}")
print(f"  Columns: {len(cohort_out.columns)}")

# --- Save summary for sanity checking ---
summary_path = os.path.join(OUTPUT_DIR, "cohort_summary.txt")
with open(summary_path, 'w') as f:
    f.write("CVD COHORT SUMMARY\n")
    f.write("=" * 50 + "\n\n")
    f.write(f"Analysis year:   {ANALYSIS_YEAR}\n")
    f.write(f"Sample number:   {SAMPLE_NUM}\n")
    f.write(f"Total CVD bene:  {len(cohort_out):,}\n\n")
    
    f.write("CONDITION PREVALENCE:\n")
    f.write(f"  Hypertension:  {cohort_out['has_hypertension'].sum():,} "
            f"({100*cohort_out['has_hypertension'].mean():.1f}%)\n")
    f.write(f"  CAD:           {cohort_out['has_cad'].sum():,} "
            f"({100*cohort_out['has_cad'].mean():.1f}%)\n")
    f.write(f"  AFib:          {cohort_out['has_afib'].sum():,} "
            f"({100*cohort_out['has_afib'].mean():.1f}%)\n")
    f.write(f"  Anxiety:       {cohort_out['has_anxiety'].sum():,} "
            f"({100*cohort_out['has_anxiety'].mean():.1f}%)\n\n")
    
    f.write("DEMOGRAPHICS:\n")
    f.write(cohort_out['age_group'].value_counts().sort_index().to_string())
    f.write("\n\n")
    f.write(cohort_out['sex'].value_counts().to_string())
    f.write("\n\n")
    f.write(cohort_out['race'].value_counts().to_string())
    f.write("\n")

print(f"Summary saved to: {summary_path}")
print("\n>>> Script 1 complete. Proceed to Script 2 for spending calculation. <<<")
