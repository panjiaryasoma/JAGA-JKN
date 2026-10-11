"""Training-only association diagnostics; correlation does not authorize a feature."""

import pandas as pd
from sklearn.feature_selection import mutual_info_classif

from pipelines.configure.config import (
    ALL_FEATURES,
    CATEGORICAL_FEATURES,
    COL_TARGET,
    FORBIDDEN_FEATURES,
    LEAKAGE_AUDIT_PATH,
    MODEL_SEED,
)


def audit_correlation(train):
    rows = []
    for col in ALL_FEATURES:
        s = train[col]
        constant = s.nunique(dropna=True) <= 1
        value = (
            None if col in CATEGORICAL_FEATURES or constant else float(s.corr(train[COL_TARGET]))
        )
        rows.append(
            {
                "feature": col,
                "correlation": value,
                "constant_in_train": bool(constant),
                "decision": "CANDIDATE_SYNTHETIC_ONLY",
            }
        )
    return pd.DataFrame(rows)


def audit_mutual_information(train):
    usable = [c for c in ALL_FEATURES if train[c].nunique(dropna=True) > 1]
    X = train[usable].copy()
    discrete = []
    for col in usable:
        is_discrete = col in CATEGORICAL_FEATURES or X[col].nunique() <= 20
        discrete.append(is_discrete)
        if is_discrete:
            X[col] = pd.factorize(X[col])[0]
        else:
            X[col] = X[col].fillna(X[col].median())
    values = mutual_info_classif(
        X, train[COL_TARGET], discrete_features=discrete, random_state=MODEL_SEED
    )
    return pd.DataFrame({"feature": usable, "mutual_info": values}).sort_values(
        "mutual_info", ascending=False
    )


def run(train):
    corr, mi = audit_correlation(train), audit_mutual_information(train)
    lines = [
        "# Training-only feature diagnostics",
        "",
        "Status: DRAFT — synthetic experiment only.",
        "",
        f"Rows: {len(train)}; companies: {train.company_id.nunique()}; target: `{COL_TARGET}`.",
        f"Feature count: {len(ALL_FEATURES)}. Source: primary group_time training partition only.",
        "",
        "Association is not evidence of leakage or of safe admission. No feature is automatically allowed or removed by a correlation cutoff.",
        "month_index remains excluded (prior HOLD). All features require operational availability/domain review before real-data use.",
        "Complete ingest/as-of timestamps are missing. Period separation cannot prove all features were available at prediction time.",
        "",
        "| Feature | Pearson correlation | Constant |",
        "|---|---:|---|",
    ]
    for row in corr.itertuples():
        value = "N/A" if pd.isna(row.correlation) else f"{row.correlation:.6f}"
        lines.append(f"| {row.feature} | {value} | {row.constant_in_train} |")
    lines += [
        "",
        "Categorical Pearson values are omitted; constant columns have undefined association.",
        "",
        "| Feature | Mutual information |",
        "|---|---:|",
    ]
    lines += [f"| {row.feature} | {row.mutual_info:.6f} |" for row in mi.itertuples()]
    lines += [
        "",
        "MI is a finite-sample diagnostic, not a causal or governance decision. Constant features are excluded from MI estimation.",
        "",
        "Excluded features: " + ", ".join(f"`{c}`" for c in FORBIDDEN_FEATURES),
        "",
    ]
    LEAKAGE_AUDIT_PATH.write_text("\n".join(lines))
    return corr, mi


if __name__ == "__main__":
    from pipelines.features.data_split import make_partitions
    from pipelines.features.feature_engineering import build_full_dataset

    run(make_partitions(build_full_dataset())[0]["group_time"]["train"])
