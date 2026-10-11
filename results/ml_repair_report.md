# ML repair: reproducible synthetic benchmark

Status: DRAFT. The exported artifact is the primary group_time model.

| Regime | Selected model | Threshold | Test rows | Macro F1 | Recall | Precision | ROC-AUC | Accuracy | Normal baseline accuracy |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| group_time | Logistic Regression | 0.493846 | 450 | 0.5905 | 0.6078 | 0.5439 | 0.6023 | 0.5911 | 0.5467 |
| company_holdout | Logistic Regression | 0.487176 | 1725 | 0.5833 | 0.6651 | 0.4588 | 0.6279 | 0.5872 | 0.6313 |

- Preprocessing is fitted on training only. Models and thresholds are selected on validation macro F1.
- Both selections were completed before test scoring. Test predictions and class-imbalance baselines are saved in results/benchmarks/.
- The two regimes use different time windows; their metrics are not directly comparable estimates of improvement.
- Original company membership is frozen; its original full-history label stratification is disclosed in the manifest.
- Historical test labels were already inspected. These are regression benchmarks, not independent external validation.
- Class-weighted model scores are uncalibrated; Brier scores are diagnostic only.
- No operational point-in-time claim: source ingest/as-of completeness is unresolved.
- Synthetic simulator predictions cannot establish real JKN compliance or authorize sanctions.
- Backend integration is an offline adapter only. API ML status remains NOT_CONFIGURED; policy remains UNRESOLVED.
- SHAP from the old branch is archived, not recomputed or asserted valid for this model.

## Reproduce and inspect

```bash
uv sync --locked --group ml
uv run --no-sync python -m pipelines.training
uv run --no-sync python -m packages.ml.inference --input models/example_input.json
```

The binary and its fitted preprocessing are in models/best_model.pkl. Keep models/metadata.json alongside it.
Downloadable handoff: artifacts/jaga-jkn-ml-handoff.zip. It includes source, locked dependencies, exact synthetic inputs, and checksums.
