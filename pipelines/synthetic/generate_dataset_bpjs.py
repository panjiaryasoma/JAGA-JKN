"""Generate deterministic synthetic JAGA-JKN employer-risk demo data.

This is a scenario generator, not a policy or decision engine.
Synthetic monetary assumptions may support visual storytelling only and MUST NOT
influence risk strength, prioritization, review state, sanction, or enforcement.
"""

from __future__ import annotations

import os
import random
from pathlib import Path

import numpy as np
import pandas as pd

SEED = int(os.getenv("JAGA_SYNTHETIC_SEED", "42"))
N_COMPANIES = int(os.getenv("JAGA_N_COMPANIES", "500"))
MONTHS = pd.period_range("2025-01", "2026-12", freq="M").astype(str).tolist()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.getenv("JAGA_DATA_DIR", BASE_DIR / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

SYNTHETIC_ASSUMPTION_VERSION = "SYN-2026-10-08-v2"
SYNTHETIC_CONTRIBUTION_RATE = 0.05
SYNTHETIC_WAGE_CAP_RP = 12_000_000.0
POLICY_STATUS = "SYNTHETIC_ASSUMPTION_ONLY__B2_POLICY_NOT_AUTHORIZED"

SECTORS = [
    ("C", "Industri Pengolahan / Manufaktur"),
    ("F", "Konstruksi & Infrastruktur"),
    ("G", "Perdagangan Besar dan Eceran"),
    ("N", "Jasa Penunjang Usaha / Outsourcing / Security"),
    ("I", "Penyediaan Akomodasi dan F&B"),
    ("H", "Transportasi, Pergudangan & Logistik"),
    ("J", "Informasi dan Komunikasi / Teknologi"),
    ("Q", "Pelayanan Kesehatan Swasta"),
    ("A", "Pertanian / Perkebunan / Kehutanan"),
    ("K", "Jasa Keuangan / Pembiayaan / Asuransi"),
]
REGIONS = [
    ("DKI Jakarta", "KC Jakarta Pusat"),
    ("Jawa Barat", "KC Bandung"),
    ("Banten", "KC Tangerang"),
    ("Jawa Timur", "KC Surabaya"),
    ("Jawa Tengah", "KC Semarang"),
    ("Sumatera Utara", "KC Medan"),
    ("Riau", "KC Pekanbaru"),
    ("Kalimantan Timur", "KC Balikpapan"),
    ("Sulawesi Selatan", "KC Makassar"),
    ("Bali", "KC Denpasar"),
]
PROFILES = [
    "NORMAL",
    "WORKER_REGISTRATION_GAP",
    "WAGE_REPORTING_GAP",
    "CONTRIBUTION_PAYMENT_GAP",
    "MULTI_SIGNAL",
    "RECURRENCE",
]
PROFILE_WEIGHTS = [0.52, 0.16, 0.12, 0.10, 0.06, 0.04]
NAME_1 = [
    "Nusantara", "Bina", "Cipta", "Mandiri", "Sentosa", "Prima", "Makmur",
    "Sejahtera", "Daya", "Karya", "Mega", "Inti", "Mitra", "Surya",
]
NAME_2 = [
    "Tekstil", "Logistik", "Konstruksi", "Pangan", "Solusindo", "Teknologi",
    "Hospitality", "Distribusindo", "Plastindo", "Multi Karya", "Sarana Jaya",
]


def _rng() -> tuple[random.Random, np.random.Generator]:
    return random.Random(SEED), np.random.default_rng(SEED)


def generate() -> dict[str, pd.DataFrame]:
    py_rng, np_rng = _rng()
    master_rows: list[dict] = []
    monthly_rows: list[dict] = []
    review_rows: list[dict] = []

    for i in range(1, N_COMPANIES + 1):
        company_id = f"BU-{i:04d}"
        legal_form = py_rng.choice(["PT", "PT", "PT", "CV", "CV", "Koperasi", "Yayasan"])
        company_name = f"{legal_form} {py_rng.choice(NAME_1)} {py_rng.choice(NAME_2)}"
        kbli, sector = py_rng.choice(SECTORS)
        province, branch = py_rng.choice(REGIONS)
        scale = np_rng.choice(["Mikro", "Kecil", "Menengah", "Besar"], p=[0.15, 0.40, 0.32, 0.13])
        profile = np_rng.choice(PROFILES, p=PROFILE_WEIGHTS)

        if scale == "Mikro":
            baseline_workers = py_rng.randint(4, 9)
            baseline_wage = py_rng.randint(3_000_000, 5_500_000)
        elif scale == "Kecil":
            baseline_workers = py_rng.randint(10, 49)
            baseline_wage = py_rng.randint(3_500_000, 7_500_000)
        elif scale == "Menengah":
            baseline_workers = py_rng.randint(50, 199)
            baseline_wage = py_rng.randint(4_500_000, 10_000_000)
        else:
            baseline_workers = py_rng.randint(200, 850)
            baseline_wage = py_rng.randint(5_500_000, 15_000_000)

        master_rows.append({
            "id_badan_usaha": company_id,
            "nama_badan_usaha": company_name,
            "bentuk_badan_hukum": legal_form,
            "kode_kbli": kbli,
            "sektor_industri": sector,
            "skala_usaha": scale,
            "provinsi": province,
            "kantor_cabang_bpjs": branch,
            "scenario_profile_synthetic": profile,
            "baseline_tenaga_kerja_synthetic": baseline_workers,
            "baseline_upah_synthetic_rp": baseline_wage,
            "synthetic_assumption_version": SYNTHETIC_ASSUMPTION_VERSION,
        })

        reference_workers = baseline_workers
        reference_wage = float(baseline_wage)
        episode_active = False
        episode_duration = 0
        trigger_month = None if profile == "NORMAL" else py_rng.randint(2, 8)
        recurrence_started = False

        for month_index, period in enumerate(MONTHS):
            reference_workers = max(3, reference_workers + py_rng.choice([-2, -1, 0, 0, 0, 1, 2]))
            if period == "2026-01":
                reference_wage = round(reference_wage * py_rng.uniform(1.03, 1.07), -3)

            if trigger_month is not None and month_index >= trigger_month and not episode_active:
                episode_active = True
                episode_duration = 0
            if profile == "RECURRENCE" and month_index >= 16 and not recurrence_started:
                episode_active = True
                recurrence_started = True
                episode_duration = 0

            observed_workers = reference_workers
            observed_wage = reference_wage
            payment_state = "PAID_ON_TIME"
            mode = "NORMAL"

            if episode_active:
                episode_duration += 1
                synthetic_severity = min(1.0, 0.25 + episode_duration * 0.15)

                if profile in {"WORKER_REGISTRATION_GAP", "RECURRENCE", "MULTI_SIGNAL"}:
                    hidden_fraction = min(0.45, 0.08 + episode_duration * 0.06)
                    observed_workers = max(1, reference_workers - max(1, round(reference_workers * hidden_fraction)))
                    mode = "WORKER_REGISTRATION_GAP"

                if profile in {"WAGE_REPORTING_GAP", "MULTI_SIGNAL"}:
                    observed_wage = round(reference_wage * (1.0 - 0.18 * synthetic_severity), -3)
                    mode = "WAGE_REPORTING_GAP" if mode == "NORMAL" else "MULTI_SIGNAL"

                if profile in {"CONTRIBUTION_PAYMENT_GAP", "MULTI_SIGNAL"}:
                    payment_state = "UNPAID" if episode_duration >= 2 else "PAYMENT_PENDING"
                    mode = "CONTRIBUTION_PAYMENT_GAP" if mode == "NORMAL" else "MULTI_SIGNAL"

            synthetic_reference_base = min(reference_wage, SYNTHETIC_WAGE_CAP_RP)
            synthetic_observed_base = min(observed_wage, SYNTHETIC_WAGE_CAP_RP)
            reference_contribution = round(
                reference_workers * synthetic_reference_base * SYNTHETIC_CONTRIBUTION_RATE
            )
            observed_contribution = round(
                observed_workers * synthetic_observed_base * SYNTHETIC_CONTRIBUTION_RATE
            )
            paid_contribution = 0 if payment_state == "UNPAID" else observed_contribution

            worker_gap = max(0, reference_workers - observed_workers)
            wage_gap = max(0.0, reference_wage - observed_wage)
            exposure = max(0.0, float(reference_contribution - paid_contribution))

            monthly_rows.append({
                "id_badan_usaha": company_id,
                "periode_bulan": period,
                "reference_worker_count": reference_workers,
                "observed_registered_worker_count": observed_workers,
                "worker_discrepancy_count": worker_gap,
                "reference_wage_signal_rp": int(reference_wage),
                "observed_wage_signal_rp": int(observed_wage),
                "wage_discrepancy_signal_rp": int(wage_gap),
                "reference_contribution_synthetic_rp": reference_contribution,
                "observed_contribution_synthetic_rp": observed_contribution,
                "paid_contribution_synthetic_rp": paid_contribution,
                "estimated_exposure_synthetic_rp": int(exposure),
                "observed_payment_state": payment_state,
                "synthetic_risk_mode_ground_truth": mode,
                "episode_duration_synthetic_months": episode_duration,
                "synthetic_demo_severity": "NON_NORMATIVE_VISUAL_ONLY",
                "policy_status": POLICY_STATUS,
                "synthetic_assumption_version": SYNTHETIC_ASSUMPTION_VERSION,
                "is_synthetic": True,
            })

            # Purely synthetic narrative event for dashboard storytelling.
            # It is intentionally random and is NOT triggered by a score, threshold,
            # exposure, duration requirement, policy rule, or system recommendation.
            if episode_active and py_rng.random() < 0.06:
                review_rows.append({
                    "id_review": f"REV-{period}-{company_id}-{len(review_rows)+1:04d}",
                    "id_badan_usaha": company_id,
                    "periode_review": period,
                    "system_recommendation": "NOT_GENERATED__SYNTHETIC_NARRATIVE_ONLY",
                    "human_review_outcome_synthetic": np_rng.choice(
                        ["REVIEW_CONFIRMED", "REQUEST_MORE_EVIDENCE", "NO_ACTION_AFTER_REVIEW"],
                        p=[0.62, 0.28, 0.10],
                    ),
                    "simulated_resolution_state": np_rng.choice(
                        ["OPEN", "MONITORING", "RESOLVED_SYNTHETIC"], p=[0.35, 0.35, 0.30]
                    ),
                    "synthetic_outcome_assumption": True,
                    "is_synthetic": True,
                })

    master = pd.DataFrame(master_rows)
    monthly = pd.DataFrame(monthly_rows)
    reviews = pd.DataFrame(
        review_rows,
        columns=[
            "id_review", "id_badan_usaha", "periode_review", "system_recommendation",
            "human_review_outcome_synthetic", "simulated_resolution_state",
            "synthetic_outcome_assumption", "is_synthetic",
        ],
    )

    ml_rows: list[dict] = []
    for company_id, group in monthly.groupby("id_badan_usaha", sort=True):
        group = group.sort_values("periode_bulan")
        last = group.iloc[-1]
        master_row = master.loc[master["id_badan_usaha"] == company_id].iloc[0]
        ml_rows.append({
            "id_badan_usaha": company_id,
            "kode_kbli": master_row["kode_kbli"],
            "sektor_industri": master_row["sektor_industri"],
            "skala_usaha": master_row["skala_usaha"],
            "provinsi": master_row["provinsi"],
            "worker_gap_current": int(last["worker_discrepancy_count"]),
            "wage_gap_current_rp": int(last["wage_discrepancy_signal_rp"]),
            "estimated_exposure_current_synthetic_rp": int(last["estimated_exposure_synthetic_rp"]),
            "payment_state_current": last["observed_payment_state"],
            "max_worker_gap_24m": int(group["worker_discrepancy_count"].max()),
            "max_wage_gap_24m_rp": int(group["wage_discrepancy_signal_rp"].max()),
            "total_estimated_exposure_24m_synthetic_rp": int(
                group["estimated_exposure_synthetic_rp"].sum()
            ),
            "months_with_payment_gap": int(
                (group["observed_payment_state"] != "PAID_ON_TIME").sum()
            ),
            "synthetic_target_risk_mode": last["synthetic_risk_mode_ground_truth"],
            "ml_status": "CANDIDATE_ONLY__REQUIRES_LEAKAGE_LABEL_AND_EVALUATION_AUDIT",
            "is_synthetic": True,
        })

    return {
        "master_badan_usaha.csv": master,
        "kepatuhan_bulanan_badan_usaha.csv": monthly,
        "log_review_petugas_synthetic.csv": reviews,
        "dataset_candidate_ml_audit.csv": pd.DataFrame(ml_rows),
    }


def main() -> None:
    outputs = generate()
    for filename, frame in outputs.items():
        frame.to_csv(DATA_DIR / filename, index=False, encoding="utf-8-sig")
        print(f"wrote {filename}: {len(frame):,} rows")
    print("status: SYNTHETIC DEMO DATA GENERATED; NO DECISION/POLICY READINESS CLAIMED")


if __name__ == "__main__":
    main()
