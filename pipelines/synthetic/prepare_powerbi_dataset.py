"""Prepare root-level Power BI star-schema data from curated evidence."""

from __future__ import annotations

import numpy as np
import pandas as pd

from paths import (
    CURATED_DIR,
    POWERBI_DATA_DIR,
    POWERBI_PARAMETER_DIR,
    SCENARIO_DIR,
    ensure_output_dirs,
)


def prepare() -> dict[str, pd.DataFrame]:
    master = pd.read_csv(CURATED_DIR / "curated_master_badan_usaha.csv")
    curated = pd.read_csv(CURATED_DIR / "curated_kepatuhan_evidence.csv")
    reviews = pd.read_csv(SCENARIO_DIR / "log_review_petugas_synthetic.csv")

    dim_company = master[[
        "id_badan_usaha", "nama_badan_usaha_terstandarisasi", "bentuk_badan_hukum",
        "kode_kbli", "sektor_industri", "skala_usaha", "provinsi", "kantor_cabang_bpjs",
        "synthetic_assumption_version",
    ]].copy()
    dim_company["urutan_skala_usaha"] = dim_company["skala_usaha"].map(
        {"Mikro": 1, "Kecil": 2, "Menengah": 3, "Besar": 4}
    )

    dim_sector = dim_company[["kode_kbli", "sektor_industri"]].drop_duplicates().sort_values("kode_kbli")
    dim_sector["sector_prior_status"] = "NO_EMPIRICAL_PRIOR__DO_NOT_INFER_RISK_FROM_SECTOR_ALONE"

    calendar = pd.DataFrame({"Tanggal": pd.date_range("2025-01-01", "2026-12-31", freq="D")})
    calendar["Tahun"] = calendar["Tanggal"].dt.year
    calendar["Nomor_Bulan"] = calendar["Tanggal"].dt.month
    calendar["Tahun_Bulan"] = calendar["Tanggal"].dt.strftime("%Y-%m")
    calendar["Urutan_Tahun_Bulan"] = calendar["Tahun"] * 100 + calendar["Nomor_Bulan"]
    calendar["Tanggal_Awal_Bulan"] = calendar["Tanggal"].dt.to_period("M").dt.to_timestamp()
    calendar["Tanggal"] = calendar["Tanggal"].dt.strftime("%Y-%m-%d")
    calendar["Tanggal_Awal_Bulan"] = calendar["Tanggal_Awal_Bulan"].dt.strftime("%Y-%m-%d")

    fact_risk = curated.copy()
    fact_risk["tanggal_evaluasi"] = fact_risk["periode_bulan"] + "-01"
    fact_risk["flag_needs_human_attention"] = np.where(
        fact_risk["overall_review_state"].isin(["REVIEW", "NEEDS_ENRICHMENT", "ABSTAIN", "PARTIAL"]),
        1,
        0,
    )
    fact_risk["flag_abstain"] = np.where(
        fact_risk[["registration_signal_state", "wage_signal_state", "contribution_signal_state"]]
        .eq("ABSTAIN")
        .any(axis=1),
        1,
        0,
    )
    fact_risk["exposure_label"] = "SIMULATED_ESTIMATE__NOT_EMPIRICAL_LOSS"

    fact_review = reviews.copy()
    if not fact_review.empty:
        fact_review["tanggal_review"] = fact_review["periode_review"] + "-01"
        fact_review["outcome_label"] = "SIMULATED_OUTCOME__NOT_MODEL_PERFORMANCE"

    return {
        "Dim_Kalender.csv": calendar,
        "Dim_Badan_Usaha.csv": dim_company,
        "Dim_Sektor_KBLI.csv": dim_sector,
        "Fact_Risk_Evidence.csv": fact_risk,
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
    (POWERBI_PARAMETER_DIR / "DataRoot.pq").write_text(template, encoding="utf-8")


def main() -> None:
    ensure_output_dirs()
    for filename, frame in prepare().items():
        path = POWERBI_DATA_DIR / filename
        frame.to_csv(path, index=False, encoding="utf-8-sig")
        print(f"wrote {path}: {len(frame):,} rows")
    write_power_query_parameter()
    print(f"Power BI root data directory: {POWERBI_DATA_DIR}")
    print("status: POWER BI DATA PREPARED FROM CURATED PER-SIGNAL EVIDENCE")


if __name__ == "__main__":
    main()
