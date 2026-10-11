"""Frozen company membership, with a primary forward-time evaluation window."""

import hashlib
import json

from pipelines.configure.config import (
    ALL_FEATURES,
    COL_TARGET,
    DATA_SPLITS_DIR,
    MANIFEST_PATH,
    PROJECT_ROOT,
)

PARTITION_FILE = PROJECT_ROOT / "config/ml_company_partitions.json"


def make_partitions(df):
    allocation = json.loads(PARTITION_FILE.read_text())
    ids = {name: set(allocation[f"{name}_company_ids"]) for name in ("train", "val", "test")}
    if any(ids[a] & ids[b] for a, b in [("train", "val"), ("train", "test"), ("val", "test")]):
        raise ValueError("Company overlap in frozen allocation")
    if set.union(*ids.values()) != set(df.company_id):
        raise ValueError("Dataset membership differs from frozen allocation")
    columns = [
        "company_id",
        "period_month",
        "target_period",
        *ALL_FEATURES,
        "label_binary",
        COL_TARGET,
        "risk_mode_ground_truth",
    ]
    known = df.dropna(subset=[COL_TARGET])[columns].copy()
    known[COL_TARGET] = known[COL_TARGET].astype(int)
    historical = {
        name: known[known.company_id.isin(members)].copy() for name, members in ids.items()
    }
    windows = {
        "train": ("0000-01", "2026-03"),
        "val": ("2026-04", "2026-06"),
        "test": ("2026-07", "2026-12"),
    }
    temporal = {
        name: frame[frame.target_period.between(*windows[name])].copy()
        for name, frame in historical.items()
    }
    if any(frame.empty for frame in temporal.values()):
        raise ValueError("Empty forward-time partition")
    if (
        temporal["train"].target_period.max() > temporal["val"].period_month.min()
        or temporal["val"].target_period.max() > temporal["test"].period_month.min()
    ):
        raise ValueError("Target/feature boundary overlap")
    partitions = {"group_time": temporal, "company_holdout": historical}
    manifest = {
        "schema_version": 1,
        "primary_regime": "group_time",
        "test_history": "PREVIOUSLY_INSPECTED_SYNTHETIC_BENCHMARK",
        "allocation": allocation,
        "company_overlap": 0,
        "allocation_warning": "Original membership was stratified using full-history labels; retained to avoid reshuffling a previously inspected test set.",
        "as_of_warning": "Monthly snapshots assumed available; complete ingestion timestamps are unavailable.",
        "regimes": {},
    }
    for regime, splits in partitions.items():
        manifest["regimes"][regime] = {
            name: {
                "rows": len(frame),
                "companies": int(frame.company_id.nunique()),
                "feature_period_min": frame.period_month.min(),
                "feature_period_max": frame.period_month.max(),
                "target_period_min": frame.target_period.min(),
                "target_period_max": frame.target_period.max(),
                "target_counts": {
                    str(k): int(v) for k, v in frame[COL_TARGET].value_counts().sort_index().items()
                },
            }
            for name, frame in splits.items()
        }
    return partitions, manifest


def save_partitions(partitions, manifest):
    manifest["file_checksums"] = {}
    for regime, splits in partitions.items():
        folder = DATA_SPLITS_DIR / regime
        folder.mkdir(parents=True, exist_ok=True)
        for name, frame in splits.items():
            path = folder / f"{name}.csv"
            frame.to_csv(path, index=False)
            manifest["file_checksums"][str(path.relative_to(DATA_SPLITS_DIR))] = hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n")


def run(df):
    partitions, manifest = make_partitions(df)
    save_partitions(partitions, manifest)
    return tuple(partitions["group_time"][name] for name in ("train", "val", "test"))


if __name__ == "__main__":
    from pipelines.features.feature_engineering import build_full_dataset

    run(build_full_dataset())
