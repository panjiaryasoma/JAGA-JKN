"""Versioned model/preprocessor bundles and portable, checksum-listed handoff archives."""

import hashlib
import json
import pickle
import subprocess
import zipfile
from pathlib import Path

from packages.ml.inference import ARTIFACT_SCHEMA_VERSION, runtime_versions, sha256
from pipelines.configure.config import ALL_FEATURES, PROJECT_ROOT


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


def source_provenance():
    files = sorted(
        p
        for folder in [
            "packages/ml",
            "pipelines/configure",
            "pipelines/features",
            "pipelines/training",
            "pipelines/evaluation",
            "pipelines/audit",
        ]
        for p in (PROJECT_ROOT / folder).glob("*.py")
    )
    files += [
        PROJECT_ROOT / "pyproject.toml",
        PROJECT_ROOT / "uv.lock",
        PROJECT_ROOT / "config/ml_company_partitions.json",
    ]
    hashes = {str(p.relative_to(PROJECT_ROOT)): sha256(p) for p in files}
    digest = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()
    try:
        head = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
        dirty = bool(
            subprocess.check_output(
                ["git", "status", "--porcelain"],
                cwd=PROJECT_ROOT,
                text=True,
                stderr=subprocess.DEVNULL,
            )
        )
    except (OSError, subprocess.CalledProcessError):
        head, dirty = None, None
    return {
        "git_head": head,
        "working_tree_dirty": dirty,
        "source_sha256": digest,
        "source_files": hashes,
    }


def export_bundle(bundle, path, context):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    provenance = source_provenance()
    identity = {
        "source": provenance["source_sha256"],
        "model": bundle["model_name"],
        "threshold": bundle["threshold"],
        "context": context,
        "runtime": runtime_versions(),
    }
    version = (
        "synthetic-"
        + hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()[:16]
    )
    bundle.update(artifact_schema_version=ARTIFACT_SCHEMA_VERSION, model_version=version)
    path.write_bytes(pickle.dumps(bundle, protocol=5))
    metadata = {
        "artifact_schema_version": ARTIFACT_SCHEMA_VERSION,
        "model_version": version,
        "artifact_file": path.name,
        "artifact_sha256": sha256(path),
        "runtime_versions": runtime_versions(),
        "best_model": bundle["model_name"],
        "threshold_used": bundle["threshold"],
        "threshold_selection_dataset": "validation",
        "threshold_selection_metric": "f1_macro",
        "operational_threshold": None,
        "feature_count": len(ALL_FEATURES),
        "features_admitted": list(ALL_FEATURES),
        "status": "EXPERIMENTAL_SYNTHETIC",
        "calibration_status": "NOT_CALIBRATED",
        "test_history": "PREVIOUSLY_INSPECTED_SYNTHETIC_BENCHMARK",
        "provenance": provenance,
        **context,
    }
    write_json(path.with_name("metadata.json"), metadata)
    return metadata


def build_handoff_archive():
    """Extract into a clean checkout of the repaired branch, then use its locked environment."""
    archive = PROJECT_ROOT / "artifacts/jaga-jkn-ml-handoff.zip"
    archive.parent.mkdir(exist_ok=True)
    files = [
        p
        for folder in [
            "packages/ml",
            "pipelines/configure",
            "pipelines/features",
            "pipelines/training",
            "pipelines/evaluation",
            "pipelines/audit",
        ]
        for p in (PROJECT_ROOT / folder).glob("*.py")
    ]
    files += [
        PROJECT_ROOT / p
        for p in [
            "models/best_model.pkl",
            "models/metadata.json",
            "models/example_input.json",
            "models/example_output.json",
            "models/input_schema.json",
            "models/README.md",
            "packages/ml/README.md",
            "pyproject.toml",
            "uv.lock",
            "config/ml_company_partitions.json",
            "data/synthetic/ml_splits/split_manifest.json",
            "docs/04_DATA_STRATEGY/ML_HANDOFF/ML_REPAIR_SPEC.md",
            "results/ml_repair_report.md",
            "results/ml_baseline_metrics.json",
            "results/threshold_analysis.json",
            "results/label_and_leakage_audit.md",
        ]
    ]
    files += list((PROJECT_ROOT / "results/benchmarks").glob("*.json"))
    files += list((PROJECT_ROOT / "results/benchmarks").glob("*.csv"))
    # The exact synthetic source snapshot makes the downloaded bundle independently rerunnable.
    files += [
        PROJECT_ROOT / "data/synthetic/curated" / name
        for name in ["curated_kepatuhan_evidence.csv", "curated_master_badan_usaha.csv"]
    ]
    checksums = {str(p.relative_to(PROJECT_ROOT)): sha256(p) for p in sorted(set(files))}
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as out:
        for p in sorted(set(files)):
            out.write(p, str(p.relative_to(PROJECT_ROOT)))
        out.writestr("CHECKSUMS.json", json.dumps(checksums, indent=2) + "\n")
    return archive
