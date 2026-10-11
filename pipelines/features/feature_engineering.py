"""
pipelines/features/feature_engineering.py
==========================================
Phase 2a: Load raw curated datasets, merge company master profile,
standardize column names to English, engineer temporal and composite features,
and construct the binary target as well as lead-1 (t+1) early warning target.

Lead ML Engineer: Haidir (Dir)
"""

import sys
import warnings
from pathlib import Path

import pandas as pd

warnings.filterwarnings("ignore")

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from pipelines.ml.config import (
    ALL_EVIDENCE_VALID_COLS,
    COL_BINARY_LABEL,
    COL_COMPANY_ID,
    COL_PERIOD,
    COL_RAW_RISK_MODE,
    COL_TARGET,
    COLUMN_RENAME_MAP,
    CONTRIB_QUALITY_COLS,
    DATA_CURATED_EVIDENCE,
    DATA_MASTER_BU,
    FEATURES_MASTER,
    REG_QUALITY_COLS,
    WAGE_QUALITY_COLS,
)


def _cast_boolean_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Convert boolean and string True/False representations into binary float (0.0 / 1.0)."""
    for col in ALL_EVIDENCE_VALID_COLS:
        if col in df.columns:
            df[col] = (
                df[col]
                .astype(str)
                .map({"True": 1.0, "False": 0.0, "1": 1.0, "0": 0.0})
                .fillna(0.0)
            )
    return df


def _normalize_quality_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Min-max scale numeric quality scores to a standardized [0, 1] interval."""
    for col in [
        "registration_evidence_quality",
        "wage_evidence_quality",
        "contribution_evidence_quality",
    ]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
            low, high = df[col].min(), df[col].max()
            if high > low:
                df[col] = (df[col] - low) / (high - low)
    return df


def _add_temporal_features(df: pd.DataFrame) -> pd.DataFrame:
    """Generate sequential month index and end-of-semester boundary indicator."""
    df["month_index"] = (
        df.groupby(COL_COMPANY_ID)[COL_PERIOD]
        .rank(method="dense")
        .astype(int)
    )
    df["is_semester_end"] = (
        df[COL_PERIOD].astype(str).str.endswith(("-06", "-12")).astype(int)
    )
    return df


def _add_quality_scores(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate composite evidence reliability scores per domain and aggregate."""
    reg_cols   = [c for c in REG_QUALITY_COLS   if c in df.columns]
    wage_cols  = [c for c in WAGE_QUALITY_COLS  if c in df.columns]
    cont_cols  = [c for c in CONTRIB_QUALITY_COLS if c in df.columns]
    valid_cols = [c for c in ALL_EVIDENCE_VALID_COLS if c in df.columns]

    df["registration_quality_score"] = df[reg_cols].mean(axis=1)
    df["wage_quality_score"]         = df[wage_cols].mean(axis=1)
    df["contribution_quality_score"] = df[cont_cols].mean(axis=1)
    df["evidence_quality_composite"] = df[
        ["registration_quality_score", "wage_quality_score", "contribution_quality_score"]
    ].mean(axis=1)
    df["total_evidence_flags"] = len(valid_cols) - df[valid_cols].sum(axis=1)
    return df


def build_full_dataset() -> pd.DataFrame:
    """
    Load curated evidence and master company tables, apply English column mappings,
    engineer composite features, and generate target variables.
    Returns complete DataFrame ready for stratified partitioning.
    """
    print("[Feature Engineering] Loading raw curated data...")
    evidence_df = pd.read_csv(DATA_CURATED_EVIDENCE)
    master_df   = pd.read_csv(DATA_MASTER_BU)

    # Rename raw Indonesian columns to English
    evidence_df = evidence_df.rename(columns=COLUMN_RENAME_MAP)
    master_df   = master_df.rename(columns=COLUMN_RENAME_MAP)

    # Retain permissible company demographic attributes
    master_cols_keep = [COL_COMPANY_ID] + [c for c in FEATURES_MASTER if c in master_df.columns]
    master_clean = master_df[master_cols_keep].copy()

    df = evidence_df.merge(master_clean, on=COL_COMPANY_ID, how="left")
    df = df.sort_values([COL_COMPANY_ID, COL_PERIOD]).reset_index(drop=True)

    print("[Feature Engineering] Constructing binary target variable...")
    df[COL_BINARY_LABEL] = (df[COL_RAW_RISK_MODE] != "NORMAL").astype(int)

    print("[Feature Engineering] Engineering temporal and composite features...")
    df = _cast_boolean_columns(df)
    df = _normalize_quality_columns(df)
    df = _add_temporal_features(df)
    df = _add_quality_scores(df)

    print("[Feature Engineering] Constructing lead-1 (t+1 early warning) target...")
    df[COL_TARGET] = df.groupby(COL_COMPANY_ID)[COL_BINARY_LABEL].shift(-1)

    print(f"   Final dataset shape: {df.shape} | Period span: {df[COL_PERIOD].min()} to {df[COL_PERIOD].max()}")
    return df


if __name__ == "__main__":
    df = build_full_dataset()
    sample_cols = [COL_COMPANY_ID, COL_PERIOD, COL_BINARY_LABEL, COL_TARGET,
                   "evidence_quality_composite", "month_index"]
    print(df[sample_cols].head(10))
