"""
Feature leakage and target correlation audit.
"""

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.feature_selection import mutual_info_classif
from sklearn.preprocessing import LabelEncoder

warnings.filterwarnings("ignore")

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from pipelines.ml.config import (
    COL_BINARY_LABEL,
    COL_COMPANY_ID,
    COL_PERIOD,
    COL_RAW_RISK_MODE,
    FEATURES_ENGINEERED,
    FEATURES_EVIDENCE_QUALITY,
    FEATURES_OBSERVATION,
    FORBIDDEN_FEATURES,
    LEAKAGE_AUDIT_PATH,
    RESULTS_DIR,
)

RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def audit_correlation(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate Point-Biserial correlation for each candidate feature against the binary label.
    Classifies risk tier and governance decision.
    """
    y = df[COL_BINARY_LABEL]
    candidate_features = (
        FEATURES_EVIDENCE_QUALITY
        + FEATURES_OBSERVATION
        + FEATURES_ENGINEERED
        + [f for f in FORBIDDEN_FEATURES[:10] if f in df.columns]
    )

    rows = []
    for col in candidate_features:
        if col not in df.columns:
            continue
        try:
            series = df[col].copy()
            if series.dtype == object or str(series.dtype) == "bool":
                series = pd.Series(
                    LabelEncoder().fit_transform(series.astype(str).fillna("MISSING")),
                    index=df.index,
                )
            series = pd.to_numeric(series, errors="coerce").fillna(0)

            if series.nunique() <= 1:
                corr, pval = 0.0, 1.0
            else:
                corr, pval = stats.pointbiserialr(series, y)
                if np.isnan(corr):
                    corr, pval = 0.0, 1.0

            abs_c = abs(corr)
            if abs_c > 0.6:
                risk, decision = "VERY_HIGH", "FORBIDDEN"
            elif abs_c > 0.4:
                risk, decision = "HIGH", "FORBIDDEN"
            elif abs_c > 0.2:
                risk, decision = "MEDIUM", "HOLD"
            else:
                risk, decision = "LOW", "ALLOWED"

            if col in FORBIDDEN_FEATURES:
                decision = "FORBIDDEN (Policy)"

            rows.append({
                "feature": col,
                "correlation": round(corr, 4),
                "abs_correlation": round(abs_c, 4),
                "p_value": round(pval, 6),
                "leakage_risk": risk,
                "decision": decision,
            })
        except Exception as exc:
            rows.append({
                "feature": col,
                "correlation": None,
                "abs_correlation": None,
                "p_value": None,
                "leakage_risk": "ERROR",
                "decision": str(exc),
            })

    return pd.DataFrame(rows).sort_values("abs_correlation", ascending=False, na_position="last")


def audit_mutual_information(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate Mutual Information scores for candidate features against binary label."""
    candidate_features = [
        c for c in FEATURES_EVIDENCE_QUALITY + FEATURES_OBSERVATION + FEATURES_ENGINEERED
        if c in df.columns
    ]
    X = df[candidate_features].copy()
    for col in X.columns:
        if X[col].dtype == object or str(X[col].dtype) == "bool":
            X[col] = LabelEncoder().fit_transform(X[col].astype(str).fillna("MISSING"))
        X[col] = pd.to_numeric(X[col], errors="coerce").fillna(0)

    scores = mutual_info_classif(X, df[COL_BINARY_LABEL], random_state=42)
    return (
        pd.DataFrame({"feature": candidate_features, "mutual_info": scores})
        .sort_values("mutual_info", ascending=False)
    )


def write_audit_report(df: pd.DataFrame, corr_df: pd.DataFrame, mi_df: pd.DataFrame) -> None:
    """Export comprehensive Markdown audit and EDA governance report."""
    total_records = len(df)
    n_normal     = (df[COL_BINARY_LABEL] == 0).sum()
    n_non_normal = (df[COL_BINARY_LABEL] == 1).sum()

    risk_icons = {
        "VERY_HIGH": "🔴",
        "HIGH": "🟠",
        "MEDIUM": "🟡",
        "LOW": "🟢",
        "ERROR": "⚪",
    }

    lines = [
        "# JAGA-JKN | Feature Leakage Audit & EDA Report",
        "",
        "**Lead ML Engineer:** Haidir (Dir)  ",
        "**Dataset Commit Reference:** `9390d36a1adbef6f17aa6804dd6c56d290e06d04`  ",
        f"**Total Records:** {total_records:,} | **Enterprises:** {df[COL_COMPANY_ID].nunique()} "
        f"| **Observation Period:** {df[COL_PERIOD].min()} to {df[COL_PERIOD].max()}  ",
        "",
        "---",
        "",
        "## 1. Ground Truth Label Distribution",
        "",
        "| Original Ground Truth Risk Mode | Sample Count | Proportion |",
        "|---|---:|---:|",
    ]
    for label, count in df[COL_RAW_RISK_MODE].value_counts().items():
        lines.append(f"| `{label}` | {count:,} | {count / total_records * 100:.1f}% |")

    lines += [
        "",
        "| Binary Classification Target | Sample Count | Proportion |",
        "|---|---:|---:|",
        f"| `NORMAL (0)` | {n_normal:,} | {n_normal / total_records * 100:.1f}% |",
        f"| `NON-NORMAL (1)` | {n_non_normal:,} | {n_non_normal / total_records * 100:.1f}% |",
        "",
        "> Dataset exhibits mild imbalance (~63:37). Managed using `class_weight='balanced'`.",
        "",
        "---",
        "",
        "## 2. Point-Biserial Correlation Audit vs Binary Target",
        "",
        "> Classification Thresholds: |corr| > 0.6 = VERY HIGH (Leakage) | > 0.4 = HIGH | > 0.2 = MEDIUM | <= 0.2 = LOW",
        "",
        "| Feature | Correlation | Leakage Risk | Policy Decision |",
        "|---|---:|---|---|",
    ]
    for _, row in corr_df.iterrows():
        c = f"{row['correlation']:.4f}" if row["correlation"] is not None else "N/A"
        icon = risk_icons.get(row["leakage_risk"], "⚪")
        lines.append(f"| `{row['feature']}` | {c} | {icon} {row['leakage_risk']} | {row['decision']} |")

    lines += [
        "",
        "---",
        "",
        "## 3. Mutual Information Scores (Top 20 Features)",
        "",
        "| Feature | Mutual Information Score |",
        "|---|---:|",
    ]
    for _, row in mi_df.head(20).iterrows():
        lines.append(f"| `{row['feature']}` | {row['mutual_info']:.4f} |")

    lines += [
        "",
        "---",
        "",
        "## 4. Final Admitted Feature Vector (32 Features)",
        "",
        "- **16 Evidence Quality Flags:** `*_evidence_valid`, `*_evidence_quality`, `*_metadata_valid`, etc.",
        "- **3 Pre-adjudication Observations:** `observed_registered_worker_count` (-0.037), "
        "`unexpected_worker_count` (-0.105), `observed_wage_signal_rp` (-0.031)",
        "- **6 Enterprise Demographics:** `business_scale`, `industry_sector`, `kbli_code`, "
        "`legal_entity_type`, `province`, `bpjs_branch_office`",
        "- **7 Engineered Temporal & Composite Metrics:** `month_index`, `is_semester_end`, "
        "`evidence_quality_composite`, `total_evidence_flags`, `*_quality_score`",
        "",
        "## 5. Strictly Prohibited Features (Data Leakage & Post-adjudication Outputs)",
        "",
        "- `contribution_payment_gap_observed` — Perfect correlation 1.0",
        "- `registration_discrepancy_detected` — Deterministic with label",
        "- `wage_discrepancy_signal_rp` — High correlation 0.453",
        "- `missing_worker_count` — Moderate correlation 0.340",
        "- All `*_rule_result`, `*_review_state`, `overall_review_state` — Downstream adjudication outputs",
        "",
        "---",
        "",
        "> Disclaimer: Synthetic benchmark dataset. Strictly forbidden for real JKN operational sanctions.",
    ]

    LEAKAGE_AUDIT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"   Audit governance report generated: {LEAKAGE_AUDIT_PATH}")


def run(df: pd.DataFrame) -> tuple:
    """Execute complete leakage audit and generate documentation. Returns (corr_df, mi_df)."""
    print("[Audit] Computing Point-Biserial correlation...")
    corr_df = audit_correlation(df)

    print("[Audit] Computing Mutual Information scores...")
    mi_df = audit_mutual_information(df)

    print("[Audit] Writing formal audit documentation...")
    write_audit_report(df, corr_df, mi_df)

    return corr_df, mi_df


if __name__ == "__main__":
    from pipelines.features.feature_engineering import build_full_dataset
    dataset = build_full_dataset()
    run(dataset)
