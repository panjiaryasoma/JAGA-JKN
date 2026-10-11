"""
Stratified Group Partitioning by Enterprise Identifier (company_id).
"""

import hashlib
import json
import sys
import warnings
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

warnings.filterwarnings("ignore")

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from pipelines.ml.config import (
    ALL_FEATURES,
    COL_BINARY_LABEL,
    COL_COMPANY_ID,
    COL_PERIOD,
    COL_RAW_RISK_MODE,
    COL_TARGET,
    DATA_SPLITS_DIR,
    MANIFEST_PATH,
    SPLIT_SEED,
    TEST_PATH,
    TRAIN_PATH,
    VAL_PATH,
)

DATA_SPLITS_DIR.mkdir(parents=True, exist_ok=True)


def _compute_company_profiles(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate dominant risk mode and non-normal ratio for each enterprise."""
    dominant = (
        df.groupby(COL_COMPANY_ID)[COL_RAW_RISK_MODE]
        .agg(lambda x: x.mode()[0])
        .reset_index()
        .rename(columns={COL_RAW_RISK_MODE: "dominant_label"})
    )
    ratio = (
        df.groupby(COL_COMPANY_ID)[COL_BINARY_LABEL]
        .mean()
        .reset_index()
        .rename(columns={COL_BINARY_LABEL: "non_normal_ratio"})
    )
    return dominant.merge(ratio, on=COL_COMPANY_ID)


def split_companies(df: pd.DataFrame) -> tuple:
    """
    Partition 500 enterprises into Train (70%), Validation (15%), and Test (15%).
    """
    print("[Split] Computing enterprise risk profiles for stratification...")
    profiles  = _compute_company_profiles(df)
    companies = profiles[COL_COMPANY_ID].values
    strata    = profiles["dominant_label"].values

    # Step 1: Hold out 15% for final test set
    tv_ids, test_ids, tv_strata, _ = train_test_split(
        companies, strata, test_size=0.15, random_state=SPLIT_SEED, stratify=strata
    )

    # Step 2: From remaining 85%, isolate validation set (15% of total dataset)
    tv_profile_strata = profiles.set_index(COL_COMPANY_ID).loc[tv_ids, "dominant_label"].values
    train_ids, val_ids, _, _ = train_test_split(
        tv_ids, tv_profile_strata,
        test_size=0.15 / (1.0 - 0.15),
        random_state=SPLIT_SEED,
        stratify=tv_profile_strata,
    )

    print(f"   Enterprises -> Train: {len(train_ids)} | Validation: {len(val_ids)} | Test: {len(test_ids)}")

    # Verification: Ensure zero company overlap
    assert not (set(train_ids) & set(val_ids)),  "LEAKAGE ERROR: Overlap between train and val!"
    assert not (set(train_ids) & set(test_ids)), "LEAKAGE ERROR: Overlap between train and test!"
    assert not (set(val_ids)   & set(test_ids)), "LEAKAGE ERROR: Overlap between val and test!"
    print("   Leakage Verification: 0 enterprise ID overlap across partitions (PASSED)")

    return sorted(train_ids), sorted(val_ids), sorted(test_ids)


def _compute_label_distribution(df: pd.DataFrame, col: str) -> dict:
    vc = df[col].value_counts(normalize=True).to_dict()
    return {str(int(k)): round(float(v), 4) for k, v in vc.items()}


def _compute_sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    hasher.update(path.read_bytes())
    return hasher.hexdigest()[:16]


def save_splits(df: pd.DataFrame, train_ids, val_ids, test_ids) -> None:
    """Save cleaned partitions (train.csv, val.csv, test.csv) and split_manifest.json."""
    print("[Split] Saving partition CSV files...")

    save_cols = (
        [COL_COMPANY_ID, COL_PERIOD]
        + [c for c in ALL_FEATURES if c in df.columns]
        + [COL_BINARY_LABEL, COL_TARGET, COL_RAW_RISK_MODE]
    )
    save_cols = list(dict.fromkeys(save_cols))

    def subset_partition(ids):
        return df[df[COL_COMPANY_ID].isin(ids)][save_cols].dropna(subset=[COL_TARGET]).copy()

    train_df = subset_partition(train_ids)
    val_df   = subset_partition(val_ids)
    test_df  = subset_partition(test_ids)

    train_df.to_csv(TRAIN_PATH, index=False)
    val_df.to_csv(VAL_PATH,     index=False)
    test_df.to_csv(TEST_PATH,   index=False)

    print(f"   Record Counts -> Train: {len(train_df):,} | Val: {len(val_df):,} | Test: {len(test_df):,}")

    manifest = {
        "split_seed": SPLIT_SEED,
        "objective": "Early Warning Lead-1 Month (t+1)",
        "split_strategy": "StratifiedGroupSplit by company_id (dominant risk mode as stratum)",
        "dataset_commit": "9390d36a1adbef6f17aa6804dd6c56d290e06d04",
        "train_companies": len(train_ids),
        "val_companies":   len(val_ids),
        "test_companies":  len(test_ids),
        "train_rows": len(train_df),
        "val_rows":   len(val_df),
        "test_rows":  len(test_df),
        "train_target_distribution": _compute_label_distribution(train_df, COL_TARGET),
        "val_target_distribution":   _compute_label_distribution(val_df, COL_TARGET),
        "test_target_distribution":  _compute_label_distribution(test_df, COL_TARGET),
        "overlap_train_val":  0,
        "overlap_train_test": 0,
        "overlap_val_test":   0,
        "train_company_ids":  list(train_ids),
        "val_company_ids":    list(val_ids),
        "test_company_ids":   list(test_ids),
        "file_checksums": {
            "train.csv": _compute_sha256(TRAIN_PATH),
            "val.csv":   _compute_sha256(VAL_PATH),
            "test.csv":  _compute_sha256(TEST_PATH),
        },
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"   Partition manifest written to: {MANIFEST_PATH}")


def run(df: pd.DataFrame) -> tuple:
    """Execute complete data splitting pipeline. Returns (train_df, val_df, test_df)."""
    train_ids, val_ids, test_ids = split_companies(df)
    save_splits(df, train_ids, val_ids, test_ids)

    train = pd.read_csv(TRAIN_PATH)
    val   = pd.read_csv(VAL_PATH)
    test  = pd.read_csv(TEST_PATH)
    return train, val, test


if __name__ == "__main__":
    from pipelines.features.feature_engineering import build_full_dataset
    dataset = build_full_dataset()
    tr, va, te = run(dataset)
    print(f"Data partitioning complete: Train={len(tr)} rows, Val={len(va)} rows, Test={len(te)} rows")
