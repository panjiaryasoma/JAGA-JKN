"""
Central Configuration.
All pipeline modules import paths, feature sets, seeds, and hyperparameters from here.
"""

from pathlib import Path

# --- Project Paths -----------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# --- Reproducibility Seeds ---------------------------------------------------
SPLIT_SEED = 20261011  # Company-level stratified split seed
MODEL_SEED = 20261012  # Model initialization seed

# --- Input Data Paths --------------------------------------------------------
DATA_CURATED_EVIDENCE = PROJECT_ROOT / "data/synthetic/curated/curated_kepatuhan_evidence.csv"
DATA_MASTER_BU        = PROJECT_ROOT / "data/synthetic/curated/curated_master_badan_usaha.csv"
DATA_SPLITS_DIR       = PROJECT_ROOT / "data/synthetic/ml_splits"

# Split files (clean simple naming)
TRAIN_PATH    = DATA_SPLITS_DIR / "train.csv"
VAL_PATH      = DATA_SPLITS_DIR / "val.csv"
TEST_PATH     = DATA_SPLITS_DIR / "test.csv"
MANIFEST_PATH = DATA_SPLITS_DIR / "split_manifest.json"

# --- Output Paths ------------------------------------------------------------
RESULTS_DIR  = PROJECT_ROOT / "results"
FIGURES_DIR  = RESULTS_DIR / "figures"
MODELS_DIR   = PROJECT_ROOT / "models"

LEAKAGE_AUDIT_PATH = RESULTS_DIR / "label_and_leakage_audit.md"
METRICS_PATH       = RESULTS_DIR / "ml_baseline_metrics.json"
THRESHOLD_PATH     = RESULTS_DIR / "threshold_analysis.json"
FEAT_IMP_PATH      = RESULTS_DIR / "feature_importance.csv"
MODEL_METADATA_PATH = MODELS_DIR / "metadata.json"
BEST_MODEL_PATH    = MODELS_DIR / "best_model.pkl"

# --- Column Renaming Map (Raw Dataset -> English Identifiers) -----------------
COLUMN_RENAME_MAP = {
    "id_badan_usaha": "company_id",
    "periode_bulan": "period_month",
    "synthetic_risk_mode_ground_truth": "risk_mode_ground_truth",
    "skala_usaha": "business_scale",
    "sektor_industri": "industry_sector",
    "kode_kbli": "kbli_code",
    "bentuk_badan_hukum": "legal_entity_type",
    "provinsi": "province",
    "kantor_cabang_bpjs": "bpjs_branch_office",
}

# --- Standard Key Column Names -----------------------------------------------
COL_COMPANY_ID     = "company_id"
COL_PERIOD         = "period_month"
COL_RAW_RISK_MODE  = "risk_mode_ground_truth"
COL_BINARY_LABEL   = "label_binary"     # 0: NORMAL, 1: NON-NORMAL
COL_TARGET         = "target_lead_1"    # Binary label shifted by -1 month (t+1 early warning)

# --- Feature Groups (32 Total Model Features) --------------------------------

# Group A: Evidence Quality & Metadata Validation (16 features)
FEATURES_EVIDENCE_QUALITY = [
    "registration_evidence_valid",
    "registration_evidence_quality",
    "registration_source_metadata_valid",
    "registration_period_binding_valid",
    "registration_worker_set_valid",
    "registration_explanation_metadata_valid",
    "wage_evidence_valid",
    "wage_evidence_quality",
    "wage_source_metadata_valid",
    "wage_period_binding_valid",
    "wage_semantic_consistency_valid",
    "contribution_evidence_valid",
    "contribution_evidence_quality",
    "contribution_source_metadata_valid",
    "contribution_period_binding_valid",
    "payment_semantic_consistency_valid",
]

# Group B: Pre-adjudication Observations Audited with Low Leakage Risk (3 features)
FEATURES_OBSERVATION = [
    "observed_registered_worker_count",  # correlation = -0.037
    "unexpected_worker_count",           # correlation = -0.105
    "observed_wage_signal_rp",           # correlation = -0.031
]

# Group C: Enterprise Demographic Profile Attributes (6 features)
FEATURES_MASTER = [
    "business_scale",
    "industry_sector",
    "kbli_code",
    "legal_entity_type",
    "province",
    "bpjs_branch_office",
]

# Group D: Engineered Temporal and Composite Quality Scores (7 features)
FEATURES_ENGINEERED = [
    "month_index",
    "is_semester_end",
    "evidence_quality_composite",
    "total_evidence_flags",
    "registration_quality_score",
    "wage_quality_score",
    "contribution_quality_score",
]

# Complete feature vector for training (32 features)
ALL_FEATURES = (
    FEATURES_EVIDENCE_QUALITY
    + FEATURES_OBSERVATION
    + FEATURES_MASTER
    + FEATURES_ENGINEERED
)

# Categorical features requiring OrdinalEncoder
CATEGORICAL_FEATURES = FEATURES_MASTER

# Validation flag subsets for domain-level scoring
REG_QUALITY_COLS = [
    "registration_evidence_valid",
    "registration_source_metadata_valid",
    "registration_period_binding_valid",
    "registration_worker_set_valid",
    "registration_explanation_metadata_valid",
]
WAGE_QUALITY_COLS = [
    "wage_evidence_valid",
    "wage_source_metadata_valid",
    "wage_period_binding_valid",
    "wage_semantic_consistency_valid",
]
CONTRIB_QUALITY_COLS = [
    "contribution_evidence_valid",
    "contribution_source_metadata_valid",
    "contribution_period_binding_valid",
    "payment_semantic_consistency_valid",
]
ALL_EVIDENCE_VALID_COLS = REG_QUALITY_COLS + WAGE_QUALITY_COLS + CONTRIB_QUALITY_COLS

TRAIN_RATIO = 0.70
VAL_RATIO   = 0.15
TEST_RATIO  = 0.15

DEFAULT_THRESHOLD     = 0.50
OPERATIONAL_THRESHOLD = 0.60

FORBIDDEN_FEATURES = [
    "registration_discrepancy_detected",
    "wage_discrepancy_signal_rp",
    "wage_discrepancy_detected",
    "missing_worker_count",
    "contribution_payment_gap_observed",
    "registration_rule_result",
    "wage_rule_result",
    "contribution_rule_result",
    "registration_review_state",
    "wage_review_state",
    "contribution_review_state",
    "overall_review_state",
    "human_review_recommendation",
    "observed_discrepancy_types",
    "estimated_exposure_synthetic_rp",
    "exposure_decision_role",
    "risk_mode_ground_truth",
    "synthetic_risk_mode_ground_truth",
    "scenario_profile_synthetic",
    "missing_worker_ids_json",
    "unexpected_worker_ids_json",
    "baseline_tenaga_kerja_synthetic",
    "baseline_upah_synthetic_rp",
]

ALGORITHM_NAMES = [
    "Logistic Regression",
    "Random Forest",
    "LightGBM",
]
