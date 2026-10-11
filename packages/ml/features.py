"""Single, deterministic raw-to-feature contract for training and inference."""

import numpy as np
import pandas as pd

from pipelines.configure.config import (
    ALL_EVIDENCE_VALID_COLS,
    ALL_FEATURES,
    CONTRIB_QUALITY_COLS,
    FEATURES_EVIDENCE_QUALITY,
    FEATURES_MASTER,
    FEATURES_OBSERVATION,
    REG_QUALITY_COLS,
    WAGE_QUALITY_COLS,
)

QUALITY_COLUMNS = [c for c in FEATURES_EVIDENCE_QUALITY if c.endswith("_evidence_quality")]
QUALITY_MAPPING = {"HIGH": 1.0, "MEDIUM": 0.5, "LOW": 0.0}
RAW_COLUMNS = ["period_month", *FEATURES_EVIDENCE_QUALITY, *FEATURES_OBSERVATION, *FEATURES_MASTER]


def require_columns(df, columns):
    missing = sorted(set(columns) - set(df.columns))
    if missing or df.columns.duplicated().any():
        raise ValueError(f"Missing or duplicate feature columns: {missing}")


def validate_periods(values):
    if not values.astype("string").str.fullmatch(r"\d{4}-(0[1-9]|1[0-2])").fillna(False).all():
        raise ValueError("period_month must be a non-null YYYY-MM calendar month")
    return pd.PeriodIndex(values, freq="M")


def cast_boolean_columns(df):
    for col in ALL_EVIDENCE_VALID_COLS:
        if col in df:
            mapped = (
                df[col]
                .astype("string")
                .str.lower()
                .map({"true": 1.0, "false": 0.0, "1": 1.0, "0": 0.0, "1.0": 1.0, "0.0": 0.0})
            )
            if mapped.isna().any():
                raise ValueError(f"Invalid or missing boolean in {col}")
            df[col] = mapped.astype(float)
    return df


def normalize_quality_columns(df):
    for col in QUALITY_COLUMNS:
        if col in df:
            mapped = df[col].map(QUALITY_MAPPING)
            if mapped.isna().any():
                raise ValueError(f"Invalid or missing evidence quality in {col}")
            df[col] = mapped.astype(float)
    return df


def build_features(raw: pd.DataFrame) -> pd.DataFrame:
    """Require the complete schema. Missing observations remain NaN for train-only imputation."""
    require_columns(raw, RAW_COLUMNS)
    df = raw[RAW_COLUMNS].copy()
    months = validate_periods(df.period_month)
    df = normalize_quality_columns(cast_boolean_columns(df))
    for col in FEATURES_OBSERVATION:
        try:
            values = pd.to_numeric(df[col], errors="raise").astype(float)
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Invalid numeric observation: {col}") from exc
        present = values.dropna()
        if not np.isfinite(present).all() or (present < 0).any():
            raise ValueError(f"Invalid nonnegative observation: {col}")
        if col.endswith("_count") and (present % 1 != 0).any():
            raise ValueError(f"Invalid integer count: {col}")
        df[col] = values
    for col in FEATURES_MASTER:
        if df[col].isna().any() or df[col].astype(str).str.strip().eq("").any():
            raise ValueError(f"Missing company profile: {col}")
        df[col] = df[col].astype(str)
    df["is_semester_end"] = np.isin(months.month, [6, 12]).astype(int)
    scores = []
    for domain, cols in [
        ("registration", REG_QUALITY_COLS),
        ("wage", WAGE_QUALITY_COLS),
        ("contribution", CONTRIB_QUALITY_COLS),
    ]:
        name = f"{domain}_quality_score"
        df[name] = df[cols].mean(axis=1)
        scores.append(name)
    df["evidence_quality_composite"] = df[scores].mean(axis=1)
    df["total_evidence_flags"] = len(ALL_EVIDENCE_VALID_COLS) - df[ALL_EVIDENCE_VALID_COLS].sum(
        axis=1
    )
    return df[ALL_FEATURES]
