"""Create an observed/raw synthetic layer with realistic operational noise.

No spouse-based exemption is modeled. A worker's participation through a spouse is
not used as a reason to subtract an employer registration discrepancy.
"""

from __future__ import annotations

import os
import random
import re
from pathlib import Path

import numpy as np
import pandas as pd

SEED = int(os.getenv("JAGA_SYNTHETIC_SEED", "42")) + 1
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.getenv("JAGA_DATA_DIR", BASE_DIR / "data"))


def _noisy_name(name: str, rng: random.Random) -> str:
    dice = rng.random()
    if dice < 0.10:
        return name.replace(" ", "  ")
    if dice < 0.20:
        return name.upper()
    if dice < 0.30:
        return re.sub(r"^(PT|CV) ", r"\1. ", name)
    return name


def generate_raw() -> dict[str, pd.DataFrame]:
    rng = random.Random(SEED)

    master = pd.read_csv(DATA_DIR / "master_badan_usaha.csv")
    monthly = pd.read_csv(DATA_DIR / "kepatuhan_bulanan_badan_usaha.csv")

    raw_master = master.copy()
    raw_master["nama_badan_usaha_raw"] = raw_master["nama_badan_usaha"].map(lambda x: _noisy_name(str(x), rng))
    raw_master["npwp_badan_usaha_raw"] = [
        np.nan if rng.random() < 0.08 else f"{rng.randint(10,99)}.{rng.randint(100,999)}.{rng.randint(100,999)}.{rng.randint(1,9)}-{rng.randint(100,999)}.{rng.randint(100,999)}"
        for _ in range(len(raw_master))
    ]
    raw_master["nomor_telepon_pic_raw"] = [
        np.nan if rng.random() < 0.08 else f"08{rng.randint(11,99)}{rng.randint(10000000,99999999)}"
        for _ in range(len(raw_master))
    ]

    sector_map = dict(zip(master["id_badan_usaha"], master["kode_kbli"]))
    raw_rows: list[dict] = []

    for _, row in monthly.iterrows():
        company_id = row["id_badan_usaha"]
        period = row["periode_bulan"]
        sector = sector_map[company_id]
        reference_workers = int(row["reference_worker_count"])

        month = int(period.split("-")[1])
        if month in {2, 3, 4, 5}:
            reporting_lag_months = month - 1
        elif month in {8, 9, 10, 11}:
            reporting_lag_months = month - 7
        else:
            reporting_lag_months = 0

        if reporting_lag_months and rng.random() < 0.25:
            external_workers = max(3, reference_workers + rng.randint(-4, 4))
        else:
            external_workers = reference_workers

        seasonal_change = (
            sector in {"F", "A"}
            and row["synthetic_risk_mode_ground_truth"] == "NORMAL"
            and rng.random() < 0.08
        )

        payment_state = row["observed_payment_state"]
        settlement_delay = False
        if payment_state == "PAID_ON_TIME" and rng.random() < 0.15:
            settlement_delay = True
            payer_timestamp = f"{period}-10 23:{rng.randint(10,58):02d}:00"
            bank_timestamp = f"{period}-11 00:{rng.randint(10,58):02d}:00"
            bank_observed_state = "POSTED_NEXT_DAY"
        elif payment_state == "PAID_ON_TIME":
            payer_timestamp = f"{period}-{rng.randint(2,9):02d} 10:00:00"
            bank_timestamp = payer_timestamp
            bank_observed_state = "POSTED_ON_TIME"
        elif payment_state == "PAYMENT_PENDING":
            payer_timestamp = f"{period}-10 16:00:00"
            bank_timestamp = np.nan
            bank_observed_state = "SETTLEMENT_PENDING"
        else:
            payer_timestamp = np.nan
            bank_timestamp = np.nan
            bank_observed_state = "NO_PAYMENT_EVIDENCE"

        source_conflict = bool(reporting_lag_months > 0 and external_workers != reference_workers)
        freshness = "STALE" if reporting_lag_months >= 2 else "CURRENT"

        raw_rows.append({
            "id_badan_usaha": company_id,
            "periode_bulan": period,
            "source_record_id": f"RAW-{company_id}-{period}",
            "naker_external_reference_observed": external_workers,
            "naker_registered_observed": int(row["observed_registered_worker_count"]),
            "worker_discrepancy_raw": max(0, external_workers - int(row["observed_registered_worker_count"])),
            "reference_wage_signal_rp": int(row["reference_wage_signal_rp"]),
            "observed_wage_signal_rp": int(row["observed_wage_signal_rp"]),
            "wage_discrepancy_raw_rp": int(row["wage_discrepancy_signal_rp"]),
            "reference_contribution_synthetic_rp": int(row["reference_contribution_synthetic_rp"]),
            "paid_contribution_synthetic_rp": int(row["paid_contribution_synthetic_rp"]),
            "estimated_exposure_synthetic_rp": int(row["estimated_exposure_synthetic_rp"]),
            "payment_state_observed": payment_state,
            "payer_timestamp_synthetic": payer_timestamp,
            "bank_posting_timestamp_synthetic": bank_timestamp,
            "bank_observed_state": bank_observed_state,
            "flag_bank_settlement_delay": settlement_delay,
            "external_reporting_lag_months": reporting_lag_months,
            "external_source_freshness": freshness,
            "external_source_conflict": source_conflict,
            "seasonal_or_project_change_indicator": seasonal_change,
            "seasonal_or_project_reason": "PROJECT_OR_SEASON_END_SYNTHETIC" if seasonal_change else "NONE",
            "synthetic_risk_mode_ground_truth": row["synthetic_risk_mode_ground_truth"],
            "policy_status": row["policy_status"],
            "is_synthetic": True,
        })

    return {
        "raw_master_badan_usaha.csv": raw_master,
        "raw_kepatuhan_bulanan_badan_usaha.csv": pd.DataFrame(raw_rows),
    }


def main() -> None:
    outputs = generate_raw()
    for filename, frame in outputs.items():
        frame.to_csv(DATA_DIR / filename, index=False, encoding="utf-8-sig")
        print(f"wrote {filename}: {len(frame):,} rows")
    print("status: RAW SYNTHETIC LAYER GENERATED; SPOUSE STATUS IS NOT AN EXEMPTION SIGNAL")


if __name__ == "__main__":
    main()
