"""One-command, reproducible synthetic benchmark and model handoff."""

import json

import numpy as np
import pandas as pd

from packages.ml.features import QUALITY_MAPPING, RAW_COLUMNS
from packages.ml.inference import load_bundle, predict_record, predict_scores, sha256
from pipelines.audit.leakage_audit import run as audit
from pipelines.configure.config import (
    ALL_FEATURES,
    BEST_MODEL_PATH,
    COL_TARGET,
    COLUMN_RENAME_MAP,
    DATA_CURATED_EVIDENCE,
    DATA_MASTER_BU,
    MANIFEST_PATH,
    METRICS_PATH,
    MODEL_SEED,
    PROJECT_ROOT,
    RESULTS_DIR,
    THRESHOLD_PATH,
)
from pipelines.evaluation.metrics import baseline_metrics, evaluate_scores
from pipelines.features.data_split import make_partitions, save_partitions
from pipelines.features.feature_engineering import build_full_dataset
from pipelines.training.artifacts import build_handoff_archive, export_bundle, write_json
from pipelines.training.train import fit_and_select


def write_report(benchmarks):
    lines = [
        "# ML repair: reproducible synthetic benchmark",
        "",
        "Status: DRAFT. The exported artifact is the primary group_time model.",
        "",
        "| Regime | Selected model | Threshold | Test rows | Macro F1 | Recall | Precision | ROC-AUC | Accuracy | Normal baseline accuracy |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for name, result in benchmarks.items():
        m = result["test_metrics"]
        baseline = result["baselines"]["always_normal"]
        lines.append(
            f"| {name} | {result['model_name']} | {m['threshold']:.6f} | {m['n']} | {m['f1_macro']:.4f} | {m['recall_binary']:.4f} | {m['precision_binary']:.4f} | {m['roc_auc']:.4f} | {m['accuracy']:.4f} | {baseline['accuracy']:.4f} |"
        )
    lines += [
        "",
        "- Preprocessing is fitted on training only. Models and thresholds are selected on validation macro F1.",
        "- Both selections were completed before test scoring. Test predictions and class-imbalance baselines are saved in results/benchmarks/.",
        "- The two regimes use different time windows; their metrics are not directly comparable estimates of improvement.",
        "- Original company membership is frozen; its original full-history label stratification is disclosed in the manifest.",
        "- Historical test labels were already inspected. These are regression benchmarks, not independent external validation.",
        "- Class-weighted model scores are uncalibrated; Brier scores are diagnostic only.",
        "- No operational point-in-time claim: source ingest/as-of completeness is unresolved.",
        "- Synthetic simulator predictions cannot establish real JKN compliance or authorize sanctions.",
        "- Backend integration is an offline adapter only. API ML status remains NOT_CONFIGURED; policy remains UNRESOLVED.",
        "- SHAP from the old branch is archived, not recomputed or asserted valid for this model.",
        "",
        "## Reproduce and inspect",
        "",
        "```bash",
        "uv sync --locked --group ml",
        "uv run --no-sync python -m pipelines.training",
        "uv run --no-sync python -m packages.ml.inference --input models/example_input.json",
        "```",
        "",
        "The binary and its fitted preprocessing are in models/best_model.pkl. Keep models/metadata.json alongside it.",
        "Downloadable handoff: artifacts/jaga-jkn-ml-handoff.zip. It includes source, locked dependencies, exact synthetic inputs, and checksums.",
        "",
    ]
    (RESULTS_DIR / "ml_repair_report.md").write_text("\n".join(lines))


def write_examples(bundle):
    evidence = pd.read_csv(DATA_CURATED_EVIDENCE).rename(columns=COLUMN_RENAME_MAP)
    master = pd.read_csv(DATA_MASTER_BU, dtype={"kode_kbli": str}).rename(columns=COLUMN_RENAME_MAP)
    row = evidence.merge(master, on="company_id", suffixes=("", "_master")).iloc[0]
    record = {
        key: row[key].item() if hasattr(row[key], "item") else row[key] for key in RAW_COLUMNS
    }
    record["is_synthetic"] = True
    output = predict_record(bundle, record)
    write_json(BEST_MODEL_PATH.with_name("example_input.json"), record)
    write_json(BEST_MODEL_PATH.with_name("example_output.json"), output)
    write_json(
        BEST_MODEL_PATH.with_name("input_schema.json"),
        {
            "schema_version": 1,
            "required_columns": RAW_COLUMNS + ["is_synthetic"],
            "feature_order": ALL_FEATURES,
            "quality_mapping": QUALITY_MAPPING,
            "synthetic_only": True,
            "missing_inference": "REJECT_AND_ABSTAIN",
            "score_semantics": output["score_semantics"],
            "horizon": "next calendar month",
        },
    )


def run():
    RESULTS_DIR.mkdir(exist_ok=True)
    print("Validate snapshot, build features, and freeze company/time partitions", flush=True)
    partitions, manifest = make_partitions(build_full_dataset())
    save_partitions(partitions, manifest)
    audit(partitions["group_time"]["train"])
    selections = {}
    for regime, frames in partitions.items():
        print(f"Select on validation: {regime}", flush=True)
        selections[regime] = fit_and_select(frames["train"], frames["val"])
    # No training or selection takes place after this boundary.
    benchmarks = {}
    for regime, frames in partitions.items():
        bundle, selection = selections[regime]
        test = frames["test"]
        scores = predict_scores(bundle, test[ALL_FEATURES])
        metrics = evaluate_scores(test[COL_TARGET], scores, bundle["threshold"])
        benchmarks[regime] = {
            "regime": regime,
            "model_name": bundle["model_name"],
            "validation": selection,
            "test_history": manifest["test_history"],
            "test_metrics": metrics,
            "baselines": baseline_metrics(frames["train"][COL_TARGET], test[COL_TARGET]),
        }
        write_json(RESULTS_DIR / "benchmarks" / f"{regime}.json", benchmarks[regime])
        predictions = test[["company_id", "period_month", "target_period", COL_TARGET]].copy()
        predictions["score"] = scores
        predictions["prediction"] = (scores >= bundle["threshold"]).astype(int)
        predictions.to_csv(RESULTS_DIR / "benchmarks" / f"{regime}_predictions.csv", index=False)
        print(
            f"{regime}: {bundle['model_name']} threshold={bundle['threshold']:.6f}; test macro-F1={metrics['f1_macro']:.4f}",
            flush=True,
        )
    primary, selection = selections["group_time"]
    write_json(
        METRICS_PATH, {**benchmarks["group_time"], "n_test": len(partitions["group_time"]["test"])}
    )
    write_json(
        THRESHOLD_PATH,
        {
            "regime": "group_time",
            "selected_model": primary["model_name"],
            **selection[primary["model_name"]]["threshold_selection"],
        },
    )
    context = {
        "regime": "group_time",
        "model_seed": MODEL_SEED,
        "dataset_commit": manifest["allocation"]["dataset_commit"],
        "data_sha256": {
            str(p.relative_to(PROJECT_ROOT)): sha256(p)
            for p in [DATA_CURATED_EVIDENCE, DATA_MASTER_BU]
        },
        "split_manifest_sha256": sha256(MANIFEST_PATH),
        "validation": selection,
        "test_metrics": benchmarks["group_time"]["test_metrics"],
        "baselines": benchmarks["group_time"]["baselines"],
    }
    metadata = export_bundle(primary, BEST_MODEL_PATH, context)
    reloaded = load_bundle()
    test_features = partitions["group_time"]["test"][ALL_FEATURES]
    np.testing.assert_array_equal(
        predict_scores(primary, test_features), predict_scores(reloaded, test_features)
    )
    write_examples(reloaded)
    write_report(benchmarks)
    archive = build_handoff_archive()
    print(
        json.dumps(
            {
                "model": str(BEST_MODEL_PATH),
                "sha256": metadata["artifact_sha256"],
                "reload_prediction_parity": "PASSED",
                "handoff": str(archive),
            },
            indent=2,
        ),
        flush=True,
    )
    return benchmarks


if __name__ == "__main__":
    run()
