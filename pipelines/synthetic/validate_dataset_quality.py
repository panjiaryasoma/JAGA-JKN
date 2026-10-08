"""Descriptive synthetic data-quality profiling, independent of legal policy readiness.

Outputs are synthetic software-test evidence, not empirical JKN statistics.
Do not infer enforcement, fraud, sanctions, or actionable legal violations.
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
from matplotlib import pyplot as plt
import pandas as pd

from paths import CANDIDATE_ML_DIR, CURATED_DIR, DATA_ROOT, POWERBI_DATA_DIR, RAW_DIR, ROOT_DIR, SCENARIO_DIR

VALIDATION_DIR = DATA_ROOT / "validation"
REPORT_DIR = Path(os.getenv("JAGA_DATA_QUALITY_REPORT_DIR", ROOT_DIR / "reports" / "data_quality"))
EXPECTED_PERIODS = tuple(pd.period_range("2025-01", "2026-12", freq="M").astype(str))
KEYS = ("id_badan_usaha", "periode_bulan")
CONTRACT_NUMERIC_NONNEGATIVE = {
    "reference_worker_count_scenario",
    "observed_registered_worker_count_scenario",
    "worker_count_delta_scenario",
    "reference_wage_signal_rp",
    "observed_wage_signal_rp",
    "wage_discrepancy_signal_rp",
    "reference_contribution_synthetic_rp",
    "observed_contribution_synthetic_rp",
    "paid_contribution_synthetic_rp",
    "estimated_exposure_synthetic_rp",
    "reference_worker_count",
    "observed_registered_worker_count",
    "missing_worker_count",
    "unexpected_worker_count",
    "wage_discrepancy_signal_rp",
    "estimated_exposure_synthetic_rp",
}

TABLE_PATHS = {
    "scenario_master": SCENARIO_DIR / "master_badan_usaha.csv",
    "scenario_monthly": SCENARIO_DIR / "kepatuhan_bulanan_badan_usaha.csv",
    "scenario_reviews": SCENARIO_DIR / "log_review_petugas_synthetic.csv",
    "raw_master": RAW_DIR / "raw_master_badan_usaha.csv",
    "raw_monthly": RAW_DIR / "raw_kepatuhan_bulanan_badan_usaha.csv",
    "curated_master": CURATED_DIR / "curated_master_badan_usaha.csv",
    "curated_monthly": CURATED_DIR / "curated_kepatuhan_evidence.csv",
    "candidate_ml": CANDIDATE_ML_DIR / "dataset_candidate_ml_audit.csv",
    "powerbi_fact": POWERBI_DATA_DIR / "Fact_Risk_Evidence.csv",
}


def missing_classification(table_name: str, column: str) -> str:
    allowed = {
        "raw_master": {"npwp_badan_usaha_raw", "nomor_telepon_pic_raw"},
        # Curated master intentionally preserves the original noisy raw fields
        # for traceability; normalization outputs live in separate columns.
        "curated_master": {"npwp_badan_usaha_raw", "nomor_telepon_pic_raw"},
        "raw_monthly": {
            "payer_timestamp_synthetic",
            "bank_posting_timestamp_synthetic",
        },
        "curated_monthly": {
            f"{domain}_authority_effective_{edge}"
            for domain in ("registration", "wage", "contribution")
            for edge in ("from", "to")
        },
    }
    if column in allowed.get(table_name, set()):
        return "EXPECTED_SYNTHETIC_ABSENCE"
    return "REVIEW_UNEXPECTED_MISSING"


def key_issues(frame: pd.DataFrame, columns: tuple[str, ...]) -> dict[str, int]:
    if any(column not in frame.columns for column in columns):
        return {"missing_key_columns": 1, "null_key_rows": 0, "duplicate_key_rows": 0}
    return {
        "missing_key_columns": 0,
        "null_key_rows": int(frame[list(columns)].isna().any(axis=1).sum()),
        "duplicate_key_rows": int(frame.duplicated(subset=list(columns), keep=False).sum()),
    }


def month_grid_issues(
    frame: pd.DataFrame, company_ids: set[str], periods: tuple[str, ...]
) -> dict[str, int]:
    if any(column not in frame.columns for column in KEYS):
        return {"missing_company_period_pairs": len(company_ids) * len(periods), "unexpected_pairs": 0}
    actual = set(zip(frame["id_badan_usaha"].astype(str), frame["periode_bulan"].astype(str)))
    expected = {(company, period) for company in company_ids for period in periods}
    return {
        "missing_company_period_pairs": len(expected - actual),
        "unexpected_pairs": len(actual - expected),
    }


def observation_labels(column: pd.Series) -> pd.Series:
    """Keep unknown evidence separate from observed False."""
    def classify(value: object) -> str:
        if pd.isna(value):
            return "UNKNOWN"
        if isinstance(value, bool):
            return "TRUE" if value else "FALSE"
        if str(value) == "True":
            return "TRUE"
        if str(value) == "False":
            return "FALSE"
        return "UNKNOWN"
    return column.map(classify)


def _distribution_by_month(frame: pd.DataFrame, column: str) -> pd.DataFrame:
    temp = frame[["periode_bulan", column]].copy()
    temp["observation_state"] = observation_labels(temp[column])
    return (
        temp.groupby(["periode_bulan", "observation_state"], dropna=False)
        .size().rename("count").reset_index()
        .sort_values(["periode_bulan", "observation_state"])
        .reset_index(drop=True)
    )


def _numeric_profile(tables: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict] = []
    problems: list[dict] = []
    for table, frame in tables.items():
        for column in frame.select_dtypes(include="number").columns:
            values = pd.to_numeric(frame[column], errors="coerce")
            finite = values[values.map(lambda x: pd.isna(x) or math.isfinite(float(x)))].dropna()
            nonfinite_count = int(values.notna().sum() - len(finite))
            lower = float(finite.quantile(0.25)) if len(finite) else None
            upper = float(finite.quantile(0.75)) if len(finite) else None
            iqr_outliers = (
                int(((finite < lower - 1.5 * (upper - lower)) |
                     (finite > upper + 1.5 * (upper - lower))).sum())
                if len(finite) and lower is not None and upper is not None else 0
            )
            negative = int((finite < 0).sum())
            rows.append({
                "dataset": table, "column": column,
                "valid_numeric_count": len(finite),
                "null_count": int(values.isna().sum()),
                "min": float(finite.min()) if len(finite) else None,
                "p25": lower,
                "median": float(finite.median()) if len(finite) else None,
                "mean": float(finite.mean()) if len(finite) else None,
                "p75": upper,
                "p95": float(finite.quantile(0.95)) if len(finite) else None,
                "max": float(finite.max()) if len(finite) else None,
                "iqr_outliers_descriptive": iqr_outliers,
                "nonfinite_count": nonfinite_count,
            })
            if nonfinite_count:
                problems.append({"dataset": table, "column": column, "issue": "NONFINITE_NUMBER", "count": nonfinite_count})
            if column in CONTRACT_NUMERIC_NONNEGATIVE and negative:
                problems.append({"dataset": table, "column": column, "issue": "NEGATIVE_VALUE", "count": negative})
    return (
        pd.DataFrame(rows),
        pd.DataFrame(problems, columns=["dataset", "column", "issue", "count"]),
    )


def _plot_outputs(
    profile: pd.DataFrame,
    discrepancies: dict[str, pd.DataFrame],
    evidence_quality: pd.DataFrame,
    payments: pd.DataFrame,
) -> list[Path]:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    files: list[Path] = []
    fig, ax = plt.subplots(figsize=(10, 5))
    if not profile.empty:
        ax.bar(profile["scenario_profile_synthetic"], profile["count"])
    ax.tick_params(axis="x", rotation=30)
    ax.set(title="Synthetic Scenario Profile Distribution", xlabel="Scenario", ylabel="Companies")
    fig.tight_layout()
    p = REPORT_DIR / "scenario_profile_distribution.png"
    fig.savefig(p, dpi=140)
    plt.close(fig)
    files.append(p)

    fig, ax = plt.subplots(figsize=(11, 5))
    for label, frame in discrepancies.items():
        positive = frame[frame["observation_state"] == "TRUE"]
        ax.plot(positive["periode_bulan"], positive["count"], label=label, marker=".", markersize=3)
    ax.set(title="Observed Synthetic Discrepancies by Month", xlabel="Month", ylabel="Observed count")
    ax.tick_params(axis="x", rotation=70)
    ax.legend()
    fig.tight_layout()
    p = REPORT_DIR / "observed_discrepancy_by_month.png"
    fig.savefig(p, dpi=140)
    plt.close(fig)
    files.append(p)

    fig, ax = plt.subplots(figsize=(9, 5))
    if not evidence_quality.empty:
        grouped = evidence_quality.groupby(["domain", "quality"])["count"].sum().unstack(fill_value=0)
        grouped.plot(kind="bar", stacked=True, ax=ax)
    ax.set(title="Evidence Quality (Synthetic)", xlabel="Domain", ylabel="Rows")
    ax.tick_params(axis="x", rotation=0)
    fig.tight_layout()
    p = REPORT_DIR / "evidence_quality_distribution.png"
    fig.savefig(p, dpi=140)
    plt.close(fig)
    files.append(p)

    fig, ax = plt.subplots(figsize=(10, 5))
    if not payments.empty:
        totals = payments.groupby("observed_payment_state")["count"].sum()
        ax.bar(totals.index.astype(str), totals.values)
    ax.set(title="Observed Synthetic Payment States", xlabel="Payment evidence state", ylabel="Rows")
    ax.tick_params(axis="x", rotation=20)
    fig.tight_layout()
    p = REPORT_DIR / "payment_state_distribution.png"
    fig.savefig(p, dpi=140)
    plt.close(fig)
    files.append(p)
    return files


def validate_and_profile() -> dict[str, object]:
    """Write diagnostics even on failure; fail only hard integrity invariants."""
    tables: dict[str, pd.DataFrame] = {
        name: pd.read_csv(path) for name, path in TABLE_PATHS.items()
    }
    issues: list[str] = []
    descriptive_warnings: list[str] = []

    expected_companies = int(os.getenv("JAGA_N_COMPANIES", "500"))
    master = tables["scenario_master"]
    if len(master) != expected_companies:
        issues.append(f"company count expected {expected_companies}, got {len(master)}")
    if "id_badan_usaha" not in master:
        raise ValueError("scenario master missing id_badan_usaha")
    company_ids = set(master["id_badan_usaha"].dropna().astype(str))
    if len(company_ids) != expected_companies:
        issues.append("company IDs not complete/unique")

    key_by_table = {
        "scenario_master": ("id_badan_usaha",),
        "raw_master": ("id_badan_usaha",),
        "curated_master": ("id_badan_usaha",),
        "candidate_ml": ("id_badan_usaha",),
        "scenario_monthly": KEYS,
        "raw_monthly": KEYS,
        "curated_monthly": KEYS,
        "powerbi_fact": KEYS,
        "scenario_reviews": ("id_review",),
    }

    summary_rows = []
    missing_rows = []
    duplicate_rows = []
    for name, frame in tables.items():
        integrity = key_issues(frame, key_by_table[name])
        if any(integrity.values()):
            issues.append(f"{name} key integrity: {integrity}")
        duplicate_rows.append({"dataset": name, **integrity, "duplicate_full_rows": int(frame.duplicated().sum())})
        if frame.duplicated().any():
            issues.append(f"{name} contains identical duplicate full rows")
        summary_rows.append({
            "dataset": name, "rows": len(frame), "columns": len(frame.columns),
            "null_cells": int(frame.isna().sum().sum()),
            "duplicate_full_rows": int(frame.duplicated().sum()),
            "unique_companies": (
                int(frame["id_badan_usaha"].nunique()) if "id_badan_usaha" in frame else None
            ),
        })
        for column, count in frame.isna().sum().items():
            if count:
                cls = missing_classification(name, column)
                missing_rows.append({
                    "dataset": name, "column": column,
                    "missing_count": int(count),
                    "missing_percent": round(count * 100 / len(frame), 3) if len(frame) else 0,
                    "classification": cls,
                })
                if cls == "REVIEW_UNEXPECTED_MISSING":
                    descriptive_warnings.append(f"{name}.{column}: {count} unexpected missing values")

    monthly = [name for name in ("scenario_monthly", "raw_monthly", "curated_monthly", "powerbi_fact")]
    grid_rows = []
    canonical = None
    for name in monthly:
        frame = tables[name]
        grid = month_grid_issues(frame, company_ids, EXPECTED_PERIODS)
        if any(grid.values()):
            issues.append(f"{name} month grid: {grid}")
        if canonical is None:
            canonical = set(zip(frame["id_badan_usaha"].astype(str), frame["periode_bulan"].astype(str)))
        else:
            actual = set(zip(frame["id_badan_usaha"].astype(str), frame["periode_bulan"].astype(str)))
            if actual != canonical:
                issues.append(f"{name} has keys inconsistent with scenario monthly")
        for period, subset in frame.groupby("periode_bulan"):
            grid_rows.append({
                "dataset": name, "periode_bulan": period,
                "rows": len(subset),
                "unique_companies": subset["id_badan_usaha"].nunique(),
                "expected_companies": expected_companies,
                "is_complete": len(subset) == expected_companies and subset["id_badan_usaha"].nunique() == expected_companies,
            })
    if tables["candidate_ml"]["id_badan_usaha"].astype(str).pipe(set) != company_ids:
        issues.append("ML candidate company population mismatch (CANDIDATE ONLY)")

    scenario = tables["scenario_monthly"]
    numeric, numeric_issues = _numeric_profile(tables)
    if len(numeric_issues):
        issues.append(f"{len(numeric_issues)} numeric integrity groups have invalid values")
    for target, observed, delta in (
        ("reference_worker_count_scenario", "observed_registered_worker_count_scenario", "worker_count_delta_scenario"),
        ("reference_wage_signal_rp", "observed_wage_signal_rp", "wage_discrepancy_signal_rp"),
    ):
        if not {target, observed, delta}.issubset(scenario.columns):
            issues.append(f"scenario missing cross-field columns: {target}/{observed}/{delta}")
            continue
        diff = (scenario[target] - scenario[observed]).clip(lower=0)
        mismatch_count = int(diff.ne(scenario[delta]).sum())
        if mismatch_count:
            issues.append(f"scenario cross-field mismatch {delta}: {mismatch_count} rows")

    profile = (
        master["scenario_profile_synthetic"].value_counts()
        .rename_axis("scenario_profile_synthetic").reset_index(name="count")
        .sort_values("scenario_profile_synthetic")
    )
    anomaly = (
        scenario.groupby(["periode_bulan", "synthetic_risk_mode_ground_truth"])
        .size().rename("count").reset_index()
        .sort_values(["periode_bulan", "synthetic_risk_mode_ground_truth"])
    )
    curated = tables["curated_monthly"]
    discrepancies = {
        "registration": _distribution_by_month(curated, "registration_discrepancy_detected"),
        "wage": _distribution_by_month(curated, "wage_discrepancy_detected"),
        "contribution": _distribution_by_month(curated, "contribution_payment_gap_observed"),
    }
    evidence = pd.concat([
        curated.groupby(["periode_bulan", f"{domain}_evidence_quality"])
        .size().rename("count").reset_index()
        .rename(columns={f"{domain}_evidence_quality": "quality"})
        .assign(domain=domain)[["periode_bulan", "domain", "quality", "count"]]
        for domain in ("registration", "wage", "contribution")
    ], ignore_index=True)
    payments = (
        tables["raw_monthly"].groupby(["periode_bulan", "payment_state_observed"])
        .size().rename("count").reset_index()
        .rename(columns={"payment_state_observed": "observed_payment_state"})
    )
    # Descriptive signal distributions are not compliance prevalence estimates.
    VALIDATION_DIR.mkdir(parents=True, exist_ok=True)
    outputs = {
        "dataset_summary.csv": pd.DataFrame(summary_rows),
        "missing_values.csv": pd.DataFrame(
            missing_rows,
            columns=["dataset", "column", "missing_count", "missing_percent", "classification"],
        ),
        "duplicate_keys.csv": pd.DataFrame(duplicate_rows),
        "numeric_range_summary.csv": numeric,
        "numeric_range_issues.csv": numeric_issues,
        "anomaly_distribution.csv": anomaly,
        "scenario_profile_distribution.csv": profile,
        "registration_discrepancy_distribution.csv": discrepancies["registration"],
        "wage_discrepancy_distribution.csv": discrepancies["wage"],
        "contribution_payment_distribution.csv": discrepancies["contribution"],
        "temporal_consistency.csv": pd.DataFrame(grid_rows),
        "evidence_quality_distribution.csv": evidence,
        "payment_state_distribution.csv": payments,
    }
    for filename, frame in outputs.items():
        frame.to_csv(VALIDATION_DIR / filename, index=False, encoding="utf-8-sig")

    plots = _plot_outputs(profile, discrepancies, evidence, payments)
    report = {
        "status": "FAIL" if issues else "PASS_WITH_WARNINGS" if descriptive_warnings else "PASS",
        "scope": "SYNTHETIC_SANDBOX_DATA_QUALITY_ONLY",
        "seed": int(os.getenv("JAGA_SYNTHETIC_SEED", "42")),
        "raw_seed_offset": 1,
        "companies": expected_companies,
        "months": len(EXPECTED_PERIODS),
        "scenario_monthly_rows": len(scenario),
        "curated_monthly_rows": len(curated),
        "issues": issues,
        "descriptive_warnings": descriptive_warnings,
        "observed_discrepancies_are_not_legal_findings": True,
        "no_policy_authorization": True,
        "ml_status": "CANDIDATE_ONLY",
        "generated_tables": sorted(outputs),
        "generated_plots": [p.name for p in plots],
    }
    (VALIDATION_DIR / "dataset_summary.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    lines = [
        "# Synthetic Data Quality Findings: JAGA-JKN", "",
        f"Status: **{report['status']}**", "",
        f"Seed: **{report['seed']}**, raw generator seed: **{report['seed'] + 1}**.",
        f"Companies: **{expected_companies}**, months: **{len(EXPECTED_PERIODS)}**.",
        f"Monthly scenario rows: **{len(scenario)}**, curated rows: **{len(curated)}**.", "",
        "## Integrity findings", "",
        *([f"- {issue}" for issue in issues] or ["- No hard integrity violations detected."]),
        "", "## Descriptive missing-data observations", "",
        *([f"- {warning}" for warning in descriptive_warnings] or [
            "- No unclassified missing values detected. Expected evidence absences are separately classified in missing_values.csv."
        ]),
        "", "## Interpretation limits", "",
        "- This is a seeded synthetic sandbox, NOT empirical BPJS/JKN data.",
        "- Observed discrepancies are factual simulated observations, NOT legal determinations.",
        "- IQR outliers are descriptive and do not trigger compliance decisions.",
        "- B1/B2 registration/policy authority is unresolved; rule outputs remain ABSTAIN.",
        "- Synthetic exposure is not measured financial loss and must not affect decisions.",
        "- ML candidate files are not training-ready; label/leakage audits are pending.",
        "- Power BI PBIX rebind is pending.", "",
        "## Generated evidence", "",
        *[f"- {name}" for name in sorted(outputs)],
        *[f"- reports/data_quality/{p.name}" for p in plots], "",
    ]
    (VALIDATION_DIR / "data_quality_findings.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if issues:
        raise ValueError("SYNTHETIC DATA QUALITY INTEGRITY FAILED: " + "; ".join(issues))
    return report


def main() -> None:
    validate_and_profile()
    print("STATUS: SYNTHETIC DATA QUALITY VALIDATED (NOT EMPIRICAL JKN)")


if __name__ == "__main__":
    main()
