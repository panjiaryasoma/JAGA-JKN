"""Create noisy raw synthetic evidence, including worker-set observations.

Registration evidence is represented as sets of worker IDs. Aggregate counts are
secondary projections of set reconciliation, never a substitute for identity-level
membership semantics.
"""

from __future__ import annotations

import json
import os
import random
import re

import numpy as np
import pandas as pd

from paths import RAW_DIR, SCENARIO_DIR, ensure_output_dirs

SEED = int(os.getenv("JAGA_SYNTHETIC_SEED", "42")) + 1


def _noisy_name(name: str, rng: random.Random) -> str:
    dice = rng.random()
    if dice < 0.10:
        return name.replace(" ", "  ")
    if dice < 0.20:
        return name.upper()
    if dice < 0.30:
        return re.sub(r"^(PT|CV) ", r"\1. ", name)
    return name


def _worker_ids(company_id: str, count: int) -> set[str]:
    return {f"{company_id}-W-{index:05d}" for index in range(1, count + 1)}


def _resize_reference_set(company_id: str, base: set[str], target_count: int) -> set[str]:
    ordered = sorted(base)
    if target_count <= len(ordered):
        return set(ordered[:target_count])
    result = set(ordered)
    for index in range(len(ordered) + 1, target_count + 1):
        result.add(f"{company_id}-EXT-{index:05d}")
    return result


def _observed_registration_set(
    company_id: str,
    period: str,
    reference_set: set[str],
    observed_count: int,
    rng: random.Random,
) -> set[str]:
    observed = set(sorted(reference_set)[: min(observed_count, len(reference_set))])
    while len(observed) < observed_count:
        observed.add(f"{company_id}-UNEXPECTED-{period}-{len(observed)+1:04d}")
    if observed and len(observed) == len(reference_set) and rng.random() < 0.05:
        replaced = sorted(observed)[0]
        observed.remove(replaced)
        observed.add(f"{company_id}-UNEXPECTED-{period}-SWAP")
    return observed


def serialize_worker_set(values: set[str]) -> str:
    return json.dumps(sorted(values), separators=(",", ":"))


def generate_raw() -> dict[str, pd.DataFrame]:
    rng = random.Random(SEED)
    master = pd.read_csv(SCENARIO_DIR / "master_badan_usaha.csv")
    monthly = pd.read_csv(SCENARIO_DIR / "kepatuhan_bulanan_badan_usaha.csv")

    raw_master = master.copy()
    raw_master["nama_badan_usaha_raw"] = raw_master["nama_badan_usaha"].map(
        lambda value: _noisy_name(str(value), rng)
    )
    raw_master["npwp_badan_usaha_raw"] = [
        np.nan if rng.random() < 0.08 else (
            f"{rng.randint(10,99)}.{rng.randint(100,999)}.{rng.randint(100,999)}."
            f"{rng.randint(1,9)}-{rng.randint(100,999)}.{rng.randint(100,999)}"
        )
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
        scenario_reference_count = int(row["reference_worker_count_scenario"])
        scenario_observed_count = int(row["observed_registered_worker_count_scenario"])

        scenario_reference_set = _worker_ids(company_id, scenario_reference_count)
        scenario_observed_set = _observed_registration_set(
            company_id, period, scenario_reference_set, scenario_observed_count, rng
        )

        month = int(period.split("-")[1])
        if month in {2, 3, 4, 5}:
            reporting_lag_months = month - 1
        elif month in {8, 9, 10, 11}:
            reporting_lag_months = month - 7
        else:
            reporting_lag_months = 0

        external_reference_count = scenario_reference_count
        if reporting_lag_months and rng.random() < 0.25:
            external_reference_count = max(3, scenario_reference_count + rng.randint(-4, 4))
        external_reference_set = _resize_reference_set(
            company_id, scenario_reference_set, external_reference_count
        )

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

        source_conflict = bool(reporting_lag_months > 0 and external_reference_set != scenario_reference_set)
        freshness = "STALE" if reporting_lag_months >= 2 else "CURRENT"

        raw_rows.append({
            "id_badan_usaha": company_id,
            "periode_bulan": period,
            "source_record_id": f"RAW-{company_id}-{period}",
            "reference_worker_set_json": serialize_worker_set(external_reference_set),
            "observed_registered_worker_set_json": serialize_worker_set(scenario_observed_set),
            "reference_worker_count_observed": len(external_reference_set),
            "observed_registered_worker_count": len(scenario_observed_set),
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
            "policy_status_metadata_only": row["policy_status_metadata_only"],
            "is_synthetic": True,
        })

    return {
        "raw_master_badan_usaha.csv": raw_master,
        "raw_kepatuhan_bulanan_badan_usaha.csv": pd.DataFrame(raw_rows),
    }


def main() -> None:
    ensure_output_dirs()
    for filename, frame in generate_raw().items():
        path = RAW_DIR / filename
        frame.to_csv(path, index=False, encoding="utf-8-sig")
        print(f"wrote {path}: {len(frame):,} rows")
    print("status: RAW SYNTHETIC EVIDENCE GENERATED WITH WORKER-SET SEMANTICS")


if __name__ == "__main__":
    main()
