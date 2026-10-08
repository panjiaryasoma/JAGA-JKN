"""Prepare explicit Power BI presentation facts from curated evidence."""

from __future__ import annotations

import pandas as pd

from paths import (
    CURATED_DIR,
    POWERBI_DATA_DIR,
    POWERBI_PARAMETER_DIR,
    SCENARIO_DIR,
    ensure_output_dirs,
)

FACT_COLUMNS = [
    "id_badan_usaha",
    "periode_bulan",

    "registration_discrepancy_detected",
    "registration_rule_result",
    "registration_rule_reason",
    "registration_review_state",
    "registration_review_reason",
    "registration_evidence_quality",
    "registration_evidence_valid",
    "registration_rule_id",
    "registration_source_ids_json",
    "registration_lineage",
    "registration_authority_authorized",
    "registration_authority_id",
    "registration_rule_version",
    "registration_applicable_period_verified",

    "wage_discrepancy_detected",
    "wage_rule_result",
    "wage_rule_reason",
    "wage_review_state",
    "wage_review_reason",
    "wage_evidence_quality",
    "wage_evidence_valid",
    "wage_rule_id",
    "wage_source_ids_json",
    "wage_lineage",
    "wage_authority_authorized",
    "wage_authority_id",
    "wage_rule_version",
    "wage_applicable_period_verified",

    "contribution_payment_gap_observed",
    "contribution_rule_result",
    "contribution_rule_reason",
    "contribution_review_state",
    "contribution_review_reason",
    "contribution_evidence_quality",
    "contribution_evidence_valid",
    "contribution_rule_id",
    "contribution_source_ids_json",
    "contribution_lineage",
    "contribution_authority_authorized",
    "contribution_authority_id",
    "contribution_rule_version",
    "contribution_applicable_period_verified",

    "overall_review_state",
    "human_review_recommendation",
    "observed_discrepancy_types",
    "estimated_exposure_synthetic_rp",
    "exposure_decision_role",
    "is_synthetic",
]


def attach_attention_flags(fact: pd.DataFrame) -> pd.DataFrame:
    """Keep governance abstention distinct from the human-review queue."""
    output = fact.copy()
    states = output[[
        "registration_review_state", "wage_review_state",
        "contribution_review_state",
    ]]
    reasons = output[[
        "registration_rule_reason", "wage_rule_reason",
        "contribution_rule_reason",
    ]]
    output["flag_reviewable"] = states.eq("REVIEW").any(axis=1).astype(int)
    output["flag_needs_enrichment"] = (
        states.eq("NEEDS_ENRICHMENT").any(axis=1).astype(int)
    )
    output["flag_abstain"] = states.eq("ABSTAIN").any(axis=1).astype(int)
    output["flag_governance_blocked"] = reasons.isin({
        "AUTHORITY_OR_APPLICABLE_VERSION_UNRESOLVED",
        "POLICY_REQUIRED_BUT_UNRESOLVED",
    }).any(axis=1).astype(int)
    output["flag_needs_human_attention"] = (
        output["flag_reviewable"] | output["flag_needs_enrichment"]
    )
    return output


def prepare() -> dict[str, pd.DataFrame]:
    master = pd.read_csv(CURATED_DIR / "curated_master_badan_usaha.csv")
    curated = pd.read_csv(CURATED_DIR / "curated_kepatuhan_evidence.csv")
    reviews = pd.read_csv(SCENARIO_DIR / "log_review_petugas_synthetic.csv")

    missing = set(FACT_COLUMNS) - set(curated.columns)
    if missing:
        raise ValueError(f"curated evidence missing Power BI contract columns: {sorted(missing)}")

    dim_company = master[[
        "id_badan_usaha",
        "nama_badan_usaha_terstandarisasi",
        "bentuk_badan_hukum",
        "kode_kbli",
        "sektor_industri",
        "skala_usaha",
        "provinsi",
        "kantor_cabang_bpjs",
        "synthetic_assumption_version",
    ]].copy()
    dim_company["urutan_skala_usaha"] = dim_company["skala_usaha"].map(
        {"Mikro": 1, "Kecil": 2, "Menengah": 3, "Besar": 4}
    )

    dim_sector = (
        dim_company[["kode_kbli", "sektor_industri"]]
        .drop_duplicates()
        .sort_values("kode_kbli")
    )
    dim_sector["sector_prior_status"] = (
        "NO_EMPIRICAL_PRIOR__DO_NOT_INFER_SIGNAL_FROM_SECTOR_ALONE"
    )

    calendar = pd.DataFrame({
        "Tanggal": pd.date_range("2025-01-01", "2026-12-31", freq="D")
    })
    calendar["Tahun"] = calendar["Tanggal"].dt.year
    calendar["Nomor_Bulan"] = calendar["Tanggal"].dt.month
    calendar["Tahun_Bulan"] = calendar["Tanggal"].dt.strftime("%Y-%m")
    calendar["Urutan_Tahun_Bulan"] = (
        calendar["Tahun"] * 100 + calendar["Nomor_Bulan"]
    )
    calendar["Tanggal_Awal_Bulan"] = (
        calendar["Tanggal"].dt.to_period("M").dt.to_timestamp()
    )
    calendar["Tanggal"] = calendar["Tanggal"].dt.strftime("%Y-%m-%d")
    calendar["Tanggal_Awal_Bulan"] = calendar["Tanggal_Awal_Bulan"].dt.strftime(
        "%Y-%m-%d"
    )

    fact = curated[FACT_COLUMNS].copy()
    fact["tanggal_evaluasi"] = fact["periode_bulan"] + "-01"
    fact = attach_attention_flags(fact)
    fact["exposure_label"] = "SIMULATED_ESTIMATE__NOT_EMPIRICAL_LOSS"
    fact["presentation_contract"] = "OBSERVATION_RULE_WORKFLOW_V1"

    fact_review = reviews.copy()
    if not fact_review.empty:
        fact_review["tanggal_review"] = fact_review["periode_review"] + "-01"
        fact_review["outcome_label"] = (
            "SIMULATED_OUTCOME__NOT_MODEL_PERFORMANCE"
        )

    return {
        "Dim_Kalender.csv": calendar,
        "Dim_Badan_Usaha.csv": dim_company,
        "Dim_Sektor_KBLI.csv": dim_sector,
        "Fact_Risk_Evidence.csv": fact,
        "Fact_Human_Review_Synthetic.csv": fact_review,
    }


def write_power_query_parameter() -> None:
    template = (
        "// Power BI text parameter template.\n"
        "// Point DataRoot to the repository's root-level powerbi/data directory.\n"
        "// Never commit a machine-specific absolute path.\n"
        "let\n"
        "    DataRoot = \"<SET_IN_POWER_BI_PARAMETER_UI>\"\n"
        "in\n"
        "    DataRoot\n"
    )
    (POWERBI_PARAMETER_DIR / "DataRoot.pq").write_text(
        template,
        encoding="utf-8",
    )


def main() -> None:
    ensure_output_dirs()
    for filename, frame in prepare().items():
        path = POWERBI_DATA_DIR / filename
        frame.to_csv(path, index=False, encoding="utf-8-sig")
        print(f"wrote {path}: {len(frame):,} rows")
    write_power_query_parameter()
    print(f"Power BI root data directory: {POWERBI_DATA_DIR}")
    print("status: POWER BI PRESENTATION CONTRACT GENERATED FROM CURATED FACTS")


if __name__ == "__main__":
    main()
