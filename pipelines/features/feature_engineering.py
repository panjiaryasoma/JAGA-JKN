"""Validate synthetic snapshots and join the exact next calendar-month target."""

import pandas as pd

from packages.ml.features import (
    build_features,
    require_columns,
    validate_periods,
)
from packages.ml.features import (
    cast_boolean_columns as _cast_boolean_columns,
)
from packages.ml.features import (
    normalize_quality_columns as _normalize_quality_columns,
)

__all__ = [
    "_cast_boolean_columns",
    "_normalize_quality_columns",
    "build_full_dataset",
    "prepare_dataset",
]
from pipelines.configure.config import (
    ALL_FEATURES,
    COL_BINARY_LABEL,
    COL_COMPANY_ID,
    COL_PERIOD,
    COL_RAW_RISK_MODE,
    COL_TARGET,
    COLUMN_RENAME_MAP,
    DATA_CURATED_EVIDENCE,
    DATA_MASTER_BU,
    FEATURES_MASTER,
)

RISK_MODES = {
    "NORMAL",
    "WORKER_REGISTRATION_GAP",
    "WAGE_REPORTING_GAP",
    "CONTRIBUTION_PAYMENT_GAP",
    "MULTI_SIGNAL",
}


def prepare_dataset(evidence: pd.DataFrame, master: pd.DataFrame) -> pd.DataFrame:
    evidence = evidence.rename(columns=COLUMN_RENAME_MAP).copy()
    master = master.rename(columns=COLUMN_RENAME_MAP).copy()
    require_columns(evidence, [COL_COMPANY_ID, COL_PERIOD, COL_RAW_RISK_MODE, "is_synthetic"])
    require_columns(master, [COL_COMPANY_ID, *FEATURES_MASTER])
    if not evidence.is_synthetic.astype(str).str.lower().eq("true").all():
        raise ValueError("Only synthetic evidence is permitted in this experiment")
    if evidence.company_id.isna().any() or master.company_id.isna().any():
        raise ValueError("Missing company_id")
    if (
        evidence.duplicated([COL_COMPANY_ID, COL_PERIOD]).any()
        or master.company_id.duplicated().any()
    ):
        raise ValueError("Duplicate company-month or master company")
    months = validate_periods(evidence.period_month)
    expected = set(pd.period_range(months.min(), months.max(), freq="M").astype(str))
    if any(set(group.period_month) != expected for _, group in evidence.groupby(COL_COMPANY_ID)):
        raise ValueError("Incomplete company-month grid: missing calendar month")
    if not evidence[COL_RAW_RISK_MODE].isin(RISK_MODES).all():
        raise ValueError("Invalid or missing ground-truth label")
    if set(evidence.company_id) != set(master.company_id):
        raise ValueError("Evidence and master company membership differ")
    df = evidence.merge(
        master[[COL_COMPANY_ID, *FEATURES_MASTER]],
        on=COL_COMPANY_ID,
        how="left",
        validate="many_to_one",
    )
    df = df.sort_values([COL_COMPANY_ID, COL_PERIOD]).reset_index(drop=True)
    features = build_features(df)
    df[ALL_FEATURES] = features
    df[COL_BINARY_LABEL] = (df[COL_RAW_RISK_MODE] != "NORMAL").astype(int)
    df["target_period"] = (pd.PeriodIndex(df.period_month, freq="M") + 1).astype(str)
    labels = df[[COL_COMPANY_ID, COL_PERIOD, COL_BINARY_LABEL]].rename(
        columns={COL_PERIOD: "target_period", COL_BINARY_LABEL: COL_TARGET}
    )
    return df.merge(labels, on=[COL_COMPANY_ID, "target_period"], how="left", validate="one_to_one")


def build_full_dataset() -> pd.DataFrame:
    return prepare_dataset(
        pd.read_csv(DATA_CURATED_EVIDENCE, dtype={"kode_kbli": str}),
        pd.read_csv(DATA_MASTER_BU, dtype={"kode_kbli": str}),
    )


if __name__ == "__main__":
    print(build_full_dataset().shape)
