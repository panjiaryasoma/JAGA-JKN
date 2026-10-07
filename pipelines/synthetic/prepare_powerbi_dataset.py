"""Prepare portable Power BI-ready star-schema data from curated evidence.

The dashboard consumes curated evidence, not pre-disambiguation monthly facts.
No hardcoded sector risk verdict is emitted. Synthetic outcome fields are labeled.
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
SOURCE_DATA_DIR = Path(os.getenv("JAGA_DATA_DIR", BASE_DIR / "data"))
POWERBI_ROOT = Path(os.getenv("JAGA_POWERBI_DIR", BASE_DIR / "powerbi"))
POWERBI_DATA_DIR = Path(os.getenv("JAGA_POWERBI_DATA_DIR", POWERBI_ROOT / "data"))
POWERBI_DATA_DIR.mkdir(parents=True, exist_ok=True)


def prepare() -> dict[str, pd.DataFrame]:
    master = pd.read_csv(SOURCE_DATA_DIR / "curated_master_badan_usaha.csv")
    curated = pd.read_csv(SOURCE_DATA_DIR / "curated_kepatuhan_evidence.csv")
    reviews = pd.read_csv(SOURCE_DATA_DIR / "log_review_petugas_synthetic.csv")

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
        fact_risk["decision_state"].isin(["REVIEW", "NEEDS_ENRICHMENT", "ABSTAIN"]), 1, 0
    )
    fact_risk["flag_abstain"] = np.where(fact_risk["decision_state"] == "ABSTAIN", 1, 0)
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
    param_dir = POWERBI_ROOT / "parameters"
    param_dir.mkdir(parents=True, exist_ok=True)
    template = (
        "// Create a Power BI text parameter named DataRoot and point it to the local extracted data folder.\n"
        "// Example only; do not commit a user-specific absolute path.\n"
        "let\n"
        "    DataRoot = \"<SET_IN_POWER_BI_PARAMETER_UI>\"\n"
        "in\n"
        "    DataRoot\n"
    )
    (param_dir / "DataRoot.pq").write_text(template, encoding="utf-8")


def main() -> None:
    outputs = prepare()
    for filename, frame in outputs.items():
        frame.to_csv(POWERBI_DATA_DIR / filename, index=False, encoding="utf-8-sig")
        print(f"wrote {filename}: {len(frame):,} rows")
    write_power_query_parameter()
    print(f"Power BI DataRoot: set at refresh time; generated data dir={POWERBI_DATA_DIR}")
    print("status: POWER BI DATA PREPARED FROM CURATED EVIDENCE")


if __name__ == "__main__":
    main()
