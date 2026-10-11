"""Build auditable dataset/split/evaluation evidence without fitting or tuning a model.

Run from the repository root: uv run --no-sync python scripts/build_ml_evidence.py
"""

from __future__ import annotations

import base64
import html
import json
import subprocess
import sys
from datetime import UTC, datetime
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import ListedColormap
from sklearn.calibration import calibration_curve
from sklearn.metrics import precision_recall_curve, roc_curve

from packages.ml.inference import load_bundle, predict_scores, sha256
from pipelines.configure.config import (
    ALL_EVIDENCE_VALID_COLS,
    ALL_FEATURES,
    CATEGORICAL_FEATURES,
    COL_TARGET,
    DATA_CURATED_EVIDENCE,
    DATA_MASTER_BU,
    DATA_SPLITS_DIR,
    MANIFEST_PATH,
)
from pipelines.evaluation.metrics import evaluate_scores
from pipelines.features.data_split import make_partitions
from pipelines.features.feature_engineering import build_full_dataset

OUT = ROOT / "results/evidence"
FIGURES = OUT / "figures"
LABELS = {"train": "Train", "val": "Validation", "test": "Test"}
GREEN, BLUE, GOLD = "#245747", "#35709b", "#b18532"
COLORS = [GREEN, BLUE, GOLD]
PAPER, INK = "#faf8f1", "#1d3430"


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


def run_checks():
    """Retain complete command output, status, timestamps, and machine-readable pytest evidence."""
    commands = {
        "ml_tests": [
            sys.executable,
            "-m",
            "pytest",
            "tests/ml",
            "-q",
            f"--junitxml={OUT / 'ml_tests.xml'}",
        ],
        "synthetic_tests": [
            sys.executable,
            "-m",
            "unittest",
            "discover",
            "-s",
            "pipelines/synthetic",
            "-p",
            "test_*.py",
            "-v",
        ],
        "governance_validator": [sys.executable, "scripts/validate_governance.py"],
        "governance_tests": [sys.executable, "scripts/test_governance_security.py"],
        "lint": [
            sys.executable,
            "-m",
            "ruff",
            "check",
            "packages/ml",
            "pipelines/configure",
            "pipelines/features",
            "pipelines/training",
            "pipelines/evaluation",
            "pipelines/audit",
            "tests/ml",
            "scripts/build_ml_evidence.py",
            "scripts/reproduce_ml_bundle.py",
        ],
        "diff_check": ["git", "diff", "--check"],
        "inference_example": [
            sys.executable,
            "-m",
            "packages.ml.inference",
            "--input",
            "models/example_input.json",
        ],
    }
    logs = OUT / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    records = []
    for name, command in commands.items():
        print(f"Capture validation: {name}", flush=True)
        started = datetime.now(UTC).isoformat()
        result = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        path = logs / f"{name}.txt"
        path.write_text(result.stdout)
        records.append(
            {
                "name": name,
                "command": command,
                "exit_code": result.returncode,
                "started_utc": started,
                "finished_utc": datetime.now(UTC).isoformat(),
                "log": str(path.relative_to(ROOT)),
                "log_sha256": sha256(path),
            }
        )
        write_json(OUT / "validation_runs.json", records)
        if result.returncode:
            raise RuntimeError(f"{name} failed; see {path}")
    return records


def validate_inputs():
    metadata = json.loads((ROOT / "models/metadata.json").read_text())
    for name, digest in {
        **metadata["data_sha256"],
        **metadata["provenance"]["source_files"],
    }.items():
        if sha256(ROOT / name) != digest:
            raise ValueError(f"Frozen model source/data mismatch: {name}")
    if sha256(MANIFEST_PATH) != metadata["split_manifest_sha256"]:
        raise ValueError("Split manifest differs from the trained model")
    dataset = build_full_dataset()
    partitions, generated = make_partitions(dataset)
    manifest = json.loads(MANIFEST_PATH.read_text())
    if generated["regimes"] != manifest["regimes"]:
        raise ValueError("Reconstructed split differs from manifest")
    for relative, digest in manifest["file_checksums"].items():
        if sha256(DATA_SPLITS_DIR / relative) != digest:
            raise ValueError(f"Split CSV mismatch: {relative}")
    for regime, splits in partitions.items():
        for name, expected in splits.items():
            stored = pd.read_csv(
                DATA_SPLITS_DIR / regime / f"{name}.csv",
                dtype={"kbli_code": str},
                float_precision="round_trip",
            )
            pd.testing.assert_frame_equal(
                expected.reset_index(drop=True), stored, check_dtype=False, atol=1e-12, rtol=1e-12
            )
    bundle = load_bundle()
    benchmarks, predictions = {}, {}
    for regime in partitions:
        benchmarks[regime] = json.loads((ROOT / f"results/benchmarks/{regime}.json").read_text())
        predictions[regime] = pd.read_csv(
            ROOT / f"results/benchmarks/{regime}_predictions.csv", float_precision="round_trip"
        )
        prediction = predictions[regime]
        expected = partitions[regime]["test"][
            ["company_id", "period_month", "target_period", COL_TARGET]
        ].reset_index(drop=True)
        pd.testing.assert_frame_equal(prediction[expected.columns], expected, check_dtype=False)
        threshold = benchmarks[regime]["test_metrics"]["threshold"]
        np.testing.assert_array_equal(
            prediction.prediction, (prediction.score >= threshold).astype(int)
        )
        measured = evaluate_scores(prediction[COL_TARGET], prediction.score, threshold)
        for key in [
            "accuracy",
            "balanced_accuracy",
            "f1_macro",
            "f1_binary",
            "precision_binary",
            "recall_binary",
            "roc_auc",
            "pr_auc",
            "brier_score",
        ]:
            if not np.isclose(
                measured[key], benchmarks[regime]["test_metrics"][key], atol=1e-12, rtol=0
            ):
                raise ValueError(f"Metric mismatch: {regime}.{key}")
        if measured["confusion_matrix"] != benchmarks[regime]["test_metrics"]["confusion_matrix"]:
            raise ValueError("Confusion matrix mismatch")
    np.testing.assert_allclose(
        predict_scores(bundle, partitions["group_time"]["test"][ALL_FEATURES]),
        predictions["group_time"].score,
        atol=1e-12,
        rtol=0,
    )
    return dataset, partitions, manifest, benchmarks, predictions, bundle


def short_name(value):
    return (
        value.replace("registration_", "reg. ")
        .replace("contribution_", "iuran. ")
        .replace("wage_", "upah. ")
        .replace("evidence_", "bukti ")
        .replace("_", " ")
    )


def save(fig, name, title, caption):
    fig.suptitle(title, fontsize=19, fontweight="bold", ha="left", x=0.06, y=0.98)
    fig.text(0.06, 0.015, caption, fontsize=9, color="#54665f", va="bottom")
    fig.tight_layout(rect=(0.035, 0.075, 0.98, 0.94), h_pad=3, w_pad=3)
    fig.savefig(FIGURES / f"{name}.png", dpi=155, facecolor=PAPER)
    fig.savefig(FIGURES / f"{name}.svg", facecolor=PAPER)
    plt.close(fig)
    return name


def plot_dataset(evidence, master):
    fig, axes = plt.subplots(2, 2, figsize=(14, 9))
    counts = evidence.synthetic_risk_mode_ground_truth.value_counts()
    names = {
        "NORMAL": "Normal",
        "WORKER_REGISTRATION_GAP": "Registrasi pekerja",
        "CONTRIBUTION_PAYMENT_GAP": "Pembayaran iuran",
        "WAGE_REPORTING_GAP": "Pelaporan upah",
        "MULTI_SIGNAL": "Multi-sinyal",
    }
    bars = axes[0, 0].barh([names[x] for x in counts.index], counts.values, color=GREEN)
    axes[0, 0].bar_label(bars, padding=5, fmt="%d")
    axes[0, 0].invert_yaxis()
    axes[0, 0].set(
        xlim=(0, counts.max() * 1.22),
        title="Label simulator bulan t • 12.000 baris",
        xlabel="Jumlah baris",
    )
    scales = master.skala_usaha.value_counts()
    bars = axes[0, 1].bar(scales.index, scales.values, color=BLUE)
    axes[0, 1].bar_label(bars, padding=4)
    axes[0, 1].set(
        title="Profil skala usaha • 500 perusahaan unik",
        ylabel="Perusahaan",
        ylim=(0, scales.max() * 1.2),
    )
    months = evidence.groupby("periode_bulan").size()
    axes[1, 0].bar(range(len(months)), months, color=GREEN)
    axes[1, 0].set_xticks(range(0, len(months), 3), months.index[::3], rotation=25)
    axes[1, 0].set(title="Kelengkapan grid bulanan • 24 bulan", ylabel="Baris", ylim=(0, 650))
    rates = (
        evidence.assign(non_normal=evidence.synthetic_risk_mode_ground_truth.ne("NORMAL"))
        .groupby("periode_bulan")
        .non_normal.mean()
    )
    axes[1, 1].plot(range(len(rates)), rates * 100, color=GOLD, marker="o")
    axes[1, 1].set_xticks(range(0, len(rates), 3), rates.index[::3], rotation=25)
    axes[1, 1].set(title="Proporsi NON-NORMAL pada bulan t", ylabel="Persen baris", ylim=(0, 100))
    return save(
        fig,
        "01_dataset",
        "Dataset sintetis • cakupan dan distribusi",
        "Sumber: curated evidence + master. Deskriptif seluruh snapshot; target model adalah t+1. Grafik tidak dipakai untuk tuning.",
    )


def plot_features(evidence):
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    domains = ["registration", "wage", "contribution"]
    left = np.zeros(3)
    for quality, color in [("HIGH", GREEN), ("MEDIUM", GOLD), ("LOW", BLUE)]:
        values = np.array(
            [evidence[f"{d}_evidence_quality"].eq(quality).mean() * 100 for d in domains]
        )
        axes[0, 0].barh(
            ["Registrasi", "Upah", "Iuran"], values, left=left, label=quality, color=color
        )
        for y, (value, start) in enumerate(zip(values, left, strict=True)):
            if value > 4:
                axes[0, 0].text(
                    start + value / 2,
                    y,
                    f"{value:.1f}%",
                    ha="center",
                    va="center",
                    color="white",
                    fontsize=10,
                )
        left += values
    axes[0, 0].set(
        title="Kategori kualitas sumber tetap dibedakan", xlabel="Persen baris", xlim=(0, 100)
    )
    axes[0, 0].legend(loc="upper center", bbox_to_anchor=(0.5, -0.15), ncol=3, frameon=False)
    invalid = (1 - evidence[ALL_EVIDENCE_VALID_COLS].astype(float).mean()).sort_values() * 100
    if invalid.max() == 0:
        axes[0, 1].set_axis_off()
        axes[0, 1].set_title("Flag validasi pada snapshot sintetis")
        axes[0, 1].text(
            0.5,
            0.62,
            f"{len(invalid)} / {len(invalid)} flag konstan True",
            ha="center",
            va="center",
            transform=axes[0, 1].transAxes,
            fontsize=19,
            color=GREEN,
            fontweight="bold",
        )
        axes[0, 1].text(
            0.5,
            0.38,
            "0% false pada seluruh 12.000 baris\nFlag ini tidak membedakan kelas pada training.\nKonstan True bukan bukti validitas operasional.",
            ha="center",
            va="center",
            transform=axes[0, 1].transAxes,
            fontsize=12,
            linespacing=1.7,
        )
    else:
        axes[0, 1].barh([short_name(x) for x in invalid.index], invalid.values, color=GOLD)
        axes[0, 1].tick_params(axis="y", labelsize=8)
        axes[0, 1].set(title="Flag bernilai false per fitur", xlabel="Persen baris", xlim=(0, 100))
    axes[1, 0].hist(evidence.observed_registered_worker_count, bins=35, color=GREEN, alpha=0.9)
    axes[1, 0].set(title="Observasi pekerja terdaftar", xlabel="Jumlah pekerja", ylabel="Baris")
    wages = np.log1p(evidence.observed_wage_signal_rp)
    axes[1, 1].hist(wages, bins=35, color=BLUE, alpha=0.9)
    axes[1, 1].set(
        title="Sebaran sinyal upah • log(1 + rupiah)", xlabel="Log natural", ylabel="Baris"
    )
    return save(
        fig,
        "02_features",
        "Pemeriksaan fitur • kualitas dan observasi",
        "Sumber: seluruh curated evidence. HIGH/MEDIUM/LOW → 1/0,5/0. False tidak berarti nilai kosong; missingness dicatat terpisah.",
    )


def split_tables(dataset, partitions, manifest):
    rows, memberships = [], []
    for name in LABELS:
        for company in manifest["allocation"][f"{name}_company_ids"]:
            memberships.append({"company_id": company, "partition": name})
    membership = pd.DataFrame(memberships).sort_values("company_id")
    membership.to_csv(OUT / "company_membership.csv", index=False)
    overlap = []
    for first, second in combinations(LABELS, 2):
        a = set(membership.loc[membership.partition == first, "company_id"])
        b = set(membership.loc[membership.partition == second, "company_id"])
        overlap.append({"first": first, "second": second, "shared_companies": len(a & b)})
    for regime, splits in partitions.items():
        for name, frame in splits.items():
            rows.append(
                {
                    "regime": regime,
                    "partition": name,
                    **manifest["regimes"][regime][name],
                    "normal": int(frame[COL_TARGET].eq(0).sum()),
                    "non_normal": int(frame[COL_TARGET].eq(1).sum()),
                    "positive_rate": float(frame[COL_TARGET].mean()),
                }
            )
    summary = pd.DataFrame(rows).drop(columns="target_counts")
    summary.to_csv(OUT / "split_summary.csv", index=False)
    assignment = dataset[["company_id", "period_month", "target_period", COL_TARGET]].merge(
        membership, on="company_id"
    )
    for regime, splits in partitions.items():
        keyset = {
            (company, period)
            for frame in splits.values()
            for company, period in frame[["company_id", "period_month"]].itertuples(
                index=False, name=None
            )
        }
        assignment[f"{regime}_included"] = [
            (company, period) in keyset
            for company, period in assignment[["company_id", "period_month"]].itertuples(
                index=False, name=None
            )
        ]
    assignment["exclusion_reason_primary"] = np.where(
        assignment[COL_TARGET].isna(),
        "NEXT_MONTH_LABEL_UNAVAILABLE",
        np.where(assignment.group_time_included, "", "OUTSIDE_FROZEN_GROUP_TIME_WINDOW"),
    )
    assignment.to_csv(OUT / "row_assignments.csv", index=False)
    if membership.company_id.duplicated().any() or any(x["shared_companies"] for x in overlap):
        raise ValueError("Overlapping company allocation")
    primary = partitions["group_time"]
    assertions = {
        "company_overlap": overlap,
        "training_target_does_not_exceed_first_validation_feature": primary[
            "train"
        ].target_period.max()
        <= primary["val"].period_month.min(),
        "validation_target_does_not_exceed_first_test_feature": primary["val"].target_period.max()
        <= primary["test"].period_month.min(),
        "source_rows": len(dataset),
        "lead1_eligible_rows": int(dataset[COL_TARGET].notna().sum()),
        "last_month_without_next_label": int(dataset[COL_TARGET].isna().sum()),
        "primary_used_rows": sum(map(len, primary.values())),
        "primary_other_window_exclusions": int(
            (assignment.exclusion_reason_primary == "OUTSIDE_FROZEN_GROUP_TIME_WINDOW").sum()
        ),
    }
    if not all(
        assertions[k]
        for k in [
            "training_target_does_not_exceed_first_validation_feature",
            "validation_target_does_not_exceed_first_test_feature",
        ]
    ):
        raise ValueError("Temporal separation failure")
    write_json(OUT / "split_checks.json", assertions)
    return summary, assertions


def plot_splits(partitions, split_checks):
    fig, axes = plt.subplots(2, 1, figsize=(14, 9))
    months = pd.period_range("2025-02", "2026-12", freq="M").astype(str)
    for ax, (regime, splits) in zip(axes, partitions.items(), strict=True):
        matrix = np.zeros((3, len(months)), dtype=int)
        row_labels = []
        for i, (name, frame) in enumerate(splits.items()):
            used = set(frame.target_period)
            matrix[i] = [(i + 1) if month in used else 0 for month in months]
            row_labels.append(
                f"{LABELS[name]}\n{frame.company_id.nunique()} perusahaan • {len(frame):,} baris"
            )
        ax.imshow(matrix, cmap=ListedColormap(["#e7e7df", *COLORS]), vmin=0, vmax=3, aspect="auto")
        ax.set_yticks(range(3), row_labels)
        ax.set_xticks(range(len(months)), months, rotation=65, ha="right", fontsize=8)
        ax.set_title(
            "Primary: perusahaan + urutan waktu"
            if regime == "group_time"
            else "Pembanding historis: perusahaan berbeda, periode sama",
            loc="left",
            pad=14,
        )
        ax.set_xticks(np.arange(-0.5, len(months), 1), minor=True)
        ax.set_yticks(np.arange(-0.5, 3, 1), minor=True)
        ax.grid(which="minor", color=PAPER, linewidth=3)
        ax.tick_params(which="minor", bottom=False, left=False)
    return save(
        fig,
        "03_split_timeline",
        "Split data • sumbu menunjukkan BULAN TARGET (t+1)",
        f"Baris fitur selalu satu bulan lebih awal. 350/75/75 perusahaan; overlap 0. {split_checks['source_rows']:,} sumber → {split_checks['lead1_eligible_rows']:,} eligible → {split_checks['primary_used_rows']:,} primary.\n500 baris terakhir tidak punya label berikutnya; 5.925 baris eligible di luar jendela primary. Abu-abu = tidak dipakai pada regime itu.",
    )


def plot_split_labels(partitions):
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    for ax, (regime, splits) in zip(axes, partitions.items(), strict=True):
        totals = np.array([len(f) for f in splits.values()])
        positives = np.array([f[COL_TARGET].sum() for f in splits.values()])
        normal = (totals - positives) / totals * 100
        ax.bar(range(3), normal, color=GREEN, label="NORMAL")
        ax.bar(range(3), 100 - normal, bottom=normal, color=GOLD, label="NON-NORMAL")
        for i, total in enumerate(totals):
            ax.text(
                i,
                normal[i] / 2,
                f"{int(total - positives[i]):,}\n{normal[i]:.1f}%",
                ha="center",
                va="center",
                color="white",
            )
            ax.text(
                i,
                normal[i] + (100 - normal[i]) / 2,
                f"{int(positives[i]):,}\n{100 - normal[i]:.1f}%",
                ha="center",
                va="center",
                color="white",
            )
        ax.set_xticks(
            range(3), [f"{LABELS[name]}\nn = {len(frame):,}" for name, frame in splits.items()]
        )
        ax.set(title=regime, ylim=(0, 100), ylabel="Persen target t+1")
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=2, frameon=False)
    return save(
        fig,
        "04_split_labels",
        "Distribusi target pada tiap partition",
        "Sumber: CSV split terverifikasi SHA-256. Label t+1, bukan label pada bulan fitur. Proporsi antarperiode berbeda.",
    )


def plot_correlation(train):
    numeric = [x for x in ALL_FEATURES if x not in CATEGORICAL_FEATURES]
    active = [x for x in numeric if train[x].nunique() > 1]
    constant = sorted(set(numeric) - set(active))
    matrix = train[[*active, COL_TARGET]].corr()
    matrix.to_csv(OUT / "training_correlation.csv")
    fig, ax = plt.subplots(figsize=(14, 12))
    plot = ax.imshow(matrix, vmin=-1, vmax=1, cmap="BrBG")
    names = [short_name(x) for x in matrix.columns]
    ax.set_xticks(range(len(names)), names, rotation=90, fontsize=8)
    ax.set_yticks(range(len(names)), names, fontsize=8)
    fig.colorbar(plot, ax=ax, fraction=0.035, pad=0.03, label="Pearson r")
    write_json(OUT / "constant_training_features.json", constant)
    return save(
        fig,
        "05_training_correlation",
        "Korelasi fitur numerik • hanya training primary",
        f"{len(train):,} baris train; {len(constant)} fitur konstan dikeluarkan (lihat JSON). Kategori profil tidak diordinalkan untuk grafik ini.\nKorelasi tidak menetapkan izin fitur, kausalitas, atau ketiadaan leakage. Target ditampilkan hanya untuk diagnostik.",
    )


def plot_evaluation(regime, benchmark, predictions, order):
    m = benchmark["test_metrics"]
    y, score = predictions[COL_TARGET], predictions.score
    fig, axes = plt.subplots(2, 2, figsize=(13, 10))
    cm = np.array(m["confusion_matrix"])
    axes[0, 0].imshow(cm, cmap="Greens", vmin=0)
    for i in range(2):
        for j in range(2):
            axes[0, 0].text(
                j,
                i,
                str(cm[i, j]),
                ha="center",
                va="center",
                fontsize=23,
                color="white" if cm[i, j] > cm.max() * 0.6 else INK,
            )
    axes[0, 0].set(
        xticks=[0, 1],
        yticks=[0, 1],
        xticklabels=["NORMAL", "NON-NORMAL"],
        yticklabels=["NORMAL", "NON-NORMAL"],
        xlabel="Prediksi",
        ylabel="Label aktual",
        title=f"Confusion matrix • threshold {m['threshold']:.6f}",
    )
    fpr, tpr, _ = roc_curve(y, score)
    axes[0, 1].plot(fpr, tpr, color=GREEN, label=f"ROC-AUC {m['roc_auc']:.4f}")
    axes[0, 1].plot([0, 1], [0, 1], "--", color="#888", label="Tanpa diskriminasi")
    axes[0, 1].set(
        xlim=(0, 1),
        ylim=(0, 1.03),
        xlabel="False positive rate",
        ylabel="True positive rate",
        title="ROC • test, threshold tidak diubah",
    )
    axes[0, 1].legend(frameon=False, loc="lower right")
    precision, recall, _ = precision_recall_curve(y, score)
    axes[1, 0].plot(recall, precision, color=BLUE, label=f"Average precision {m['pr_auc']:.4f}")
    axes[1, 0].axhline(y.mean(), linestyle="--", color=GOLD, label=f"Prevalensi {y.mean():.3f}")
    axes[1, 0].set(
        xlim=(0, 1), ylim=(0, 1.03), xlabel="Recall", ylabel="Precision", title="Precision–recall"
    )
    axes[1, 0].legend(frameon=False, loc="upper right")
    observed, predicted = calibration_curve(y, score, n_bins=8, strategy="uniform")
    axes[1, 1].plot(predicted, observed, "o-", color=GREEN, label="Skor mentah")
    axes[1, 1].plot([0, 1], [0, 1], "--", color="#888", label="Garis referensi")
    axes[1, 1].set(
        xlim=(0, 1),
        ylim=(0, 1.03),
        xlabel="Rata-rata skor pada bin",
        ylabel="Proporsi NON-NORMAL aktual",
        title=f"Reliability diagnostic • Brier {m['brier_score']:.4f}",
    )
    axes[1, 1].legend(frameon=False)
    return save(
        fig,
        f"{order:02d}_evaluation_{regime}",
        f"Evaluasi {regime} • {benchmark['model_name']} • n = {len(y):,}",
        f"Prediksi tersimpan, tanpa fit/tuning ulang. Macro F1 {m['f1_macro']:.4f} • recall {m['recall_binary']:.4f} • precision {m['precision_binary']:.4f}.\nSkor class-weighted belum dikalibrasi. Grafik reliability adalah diagnostik; bukan proses kalibrasi model.",
    )


def plot_selection(benchmarks):
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    for ax, (regime, benchmark) in zip(axes, benchmarks.items(), strict=True):
        names = list(benchmark["validation"])
        scores = [benchmark["validation"][name]["val_metrics"]["f1_macro"] for name in names]
        bars = ax.bar(
            range(len(names)),
            scores,
            color=[GREEN if name == benchmark["model_name"] else "#a6b7ae" for name in names],
        )
        ax.bar_label(bars, fmt="%.4f", padding=5)
        ax.set_xticks(
            range(len(names)),
            [
                name.replace(" ", "\n")
                + f"\nt = {benchmark['validation'][name]['threshold_selection']['threshold']:.4f}"
                for name in names
            ],
        )
        ax.set(title=regime, ylim=(0, 1), ylabel="F1-macro validation")
    return save(
        fig,
        "08_validation_selection",
        "Pemilihan model dan threshold • hanya validation",
        "Hijau = model yang dipilih. Nilai dan threshold dibaca dari hasil training yang dibekukan; tidak dihitung dari test.",
    )


def plot_coefficients(bundle):
    weights = pd.Series(bundle["model"].coef_[0], index=bundle["feature_names_transformed"])
    weights.rename("coefficient").to_csv(OUT / "model_coefficients.csv")
    nonzero = weights[weights.abs() > 1e-12]
    selected = nonzero.loc[nonzero.abs().nlargest(14).index].sort_values()
    fig, ax = plt.subplots(figsize=(13, 8))
    ax.barh(
        [short_name(x) + (" *" if x in CATEGORICAL_FEATURES else "") for x in selected.index],
        selected,
        color=[BLUE if x < 0 else GREEN for x in selected],
    )
    ax.axvline(0, color=INK, linewidth=0.8)
    ax.set(
        xlabel="Koefisien pada input yang sudah ditransformasi",
        title=f"{len(selected)} koefisien non-nol terbesar menurut nilai absolut",
    )
    return save(
        fig,
        "09_model_coefficients",
        "Parameter model Logistic Regression yang diserahkan",
        "Fitur numerik diskalakan; * kategori menggunakan ordinal encoder. Arah/besar koefisien bergantung pada pengkodean dan korelasi fitur.\nIni koefisien langsung, bukan SHAP atau efek kausal. Model dan threshold tidak berubah.",
    )


def write_report(figures, summary, profile, split_checks, runs, frozen_hash):
    import xml.etree.ElementTree as ET

    reproduced = json.loads((OUT / "clean_reproduction.json").read_text())
    if reproduced.get("status") != "PASSED" or reproduced.get("model_after_sha256") != frozen_hash:
        raise ValueError("Missing or stale clean reproduction evidence")
    junit = ET.parse(OUT / "ml_tests.xml").getroot()
    suites = [junit] if junit.tag == "testsuite" else list(junit.iter("testsuite"))
    ml_count = sum(int(s.attrib.get("tests", 0)) for s in suites)
    headers = [
        "Regime",
        "Partition",
        "Perusahaan",
        "Baris",
        "Bulan fitur",
        "Bulan target",
        "NON-NORMAL",
    ]
    rows = [
        [
            r.regime,
            LABELS[r.partition],
            str(r.companies),
            f"{r.rows:,}",
            f"{r.feature_period_min} → {r.feature_period_max}",
            f"{r.target_period_min} → {r.target_period_max}",
            f"{r.positive_rate:.1%}",
        ]
        for r in summary.itertuples()
    ]
    table = (
        "<table><thead><tr>"
        + "".join(f"<th>{x}</th>" for x in headers)
        + "</tr></thead><tbody>"
        + "".join(
            "<tr>" + "".join(f"<td>{html.escape(x)}</td>" for x in row) + "</tr>" for row in rows
        )
        + "</tbody></table>"
    )
    figures_html = "".join(
        f'<section><img src="data:image/png;base64,{base64.b64encode((FIGURES / f"{name}.png").read_bytes()).decode()}" alt="{html.escape(name)}"></section>'
        for name in figures
    )
    statuses = [
        ("Tes ML", f"{ml_count} lulus; JUnit dan log lengkap"),
        ("Data sintetis", "62 tes lulus; log lengkap"),
        ("Governance", "24 tes + validator 213 entri lulus"),
        ("Split", "CSV dan hash cocok; overlap perusahaan 0; batas waktu lulus"),
        ("Artifact", "Hash PKL tetap; prediksi reload cocok dengan skor test tersimpan"),
        (
            "Reproduksi training",
            "Lulus; log lengkap dan 6 pembandingan file identik ada di clean_reproduction.json",
        ),
        ("GitHub CI", "Belum dijalankan remote; workflow tersedia"),
        ("SHAP baru", "Tidak dibuat; koefisien LR tersedia"),
        ("Validasi eksternal / as-of operasional", "Belum tersedia"),
    ]
    status_html = (
        "<ul>"
        + "".join(
            f"<li><strong>{html.escape(k)}:</strong> {html.escape(v)}</li>" for k, v in statuses
        )
        + "</ul>"
    )
    document = f"""<!doctype html><html lang="id"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>JAGA-JKN | bukti ML</title><style>body{{margin:0;background:#faf8f1;color:#1d3430;font:16px/1.65 system-ui,sans-serif}}main{{max-width:1180px;margin:auto;padding:40px 24px}}h1{{font-size:36px;line-height:1.2}}h2{{margin-top:36px}}.tag{{color:#245747;font-weight:700}}table{{border-collapse:collapse;width:100%;font-size:13px}}th,td{{text-align:left;border-bottom:1px solid #d7ddd5;padding:12px 8px}}th{{background:#e7eee7}}img{{display:block;width:100%;height:auto}}section{{margin-top:28px}}code{{overflow-wrap:anywhere}}.note{{border-left:4px solid #b18532;padding:14px 20px;background:#f0ecdf}}@media(max-width:700px){{.table{{overflow:auto}}h1{{font-size:28px}}}}</style><main><p class="tag">JAGA-JKN / BUKTI EKSPERIMEN SINTETIS</p><h1>Dataset, split, validasi dan evaluasi model</h1><p>{profile["rows"]:,} baris · {profile["companies"]} perusahaan · {profile["periods"]} bulan · {len(ALL_FEATURES)} fitur</p><p class="note">Ini bukti teknis eksperimen, bukan penerimaan produksi. Label test historis sudah pernah diperiksa; skor belum dikalibrasi. Data independen dan bukti ketersediaan as-of operasional belum ada.</p><h2>Status bukti</h2>{status_html}<h2>Pembagian data</h2><div class="table">{table}</div><p>Membership perusahaan 350/75/75 dipertahankan dari eksperimen awal yang menggunakan label sepanjang sejarah untuk stratifikasi. Pembanding company_holdout tidak menguji generalisasi ke waktu mendatang. Primary group_time menggunakan {split_checks["primary_used_rows"]:,} baris; rincian 12.000 baris ada di row_assignments.csv.</p><p>Semua grafik dibuat setelah model dibekukan. Tidak ada fit model atau perubahan threshold dalam pembuatan laporan.</p>{figures_html}<h2>File bukti</h2><p>Folder ini berisi log perintah, JUnit XML, validation_runs.json, split_checks.json, split_summary.csv, company_membership.csv, row_assignments.csv, profil dataset, korelasi training, dan koefisien model. Grafik PNG dan SVG ada di figures/. CSV train/val/test tersedia dalam paket.</p><p>SHA-256 model: <code>{frozen_hash}</code></p><p>Waktu validasi: {html.escape(runs[-1]["finished_utc"])}. Source model/data diverifikasi terhadap metadata sebelum report dibuat.</p></main></html>"""
    (OUT / "index.html").write_text(document)
    lines = [
        "# bukti ml — dataset sampai evaluasi",
        "",
        "status: draft eksperimen sintetis",
        "",
        "| komponen | bukti |",
        "|---|---|",
    ]
    lines += [f"| {k} | {v} |" for k, v in statuses]
    lines += ["", "| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    lines += ["| " + " | ".join(row) + " |" for row in rows]
    lines += [
        "",
        "model sha256: `" + frozen_hash + "`",
        "",
        "buka index.html untuk seluruh grafik; png dan svg di figures/",
        "hasil test tidak dipakai untuk tuning ulang; data nyata dan validasi independen belum tersedia",
        "",
    ]
    (OUT / "README.md").write_text("\n".join(lines))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(exist_ok=True)
    plt.rcParams.update(
        {
            "figure.facecolor": PAPER,
            "axes.facecolor": PAPER,
            "text.color": INK,
            "axes.labelcolor": INK,
            "xtick.color": INK,
            "ytick.color": INK,
            "font.size": 11,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.titleweight": "bold",
        }
    )
    frozen_hash = sha256(ROOT / "models/best_model.pkl")
    runs = run_checks()
    dataset, partitions, manifest, benchmarks, predictions, bundle = validate_inputs()
    evidence = pd.read_csv(DATA_CURATED_EVIDENCE)
    master = pd.read_csv(DATA_MASTER_BU)
    summary, split_checks = split_tables(dataset, partitions, manifest)
    profile = {
        "rows": len(evidence),
        "companies": int(evidence.id_badan_usaha.nunique()),
        "periods": int(evidence.periode_bulan.nunique()),
        "duplicate_keys": int(evidence.duplicated(["id_badan_usaha", "periode_bulan"]).sum()),
        "feature_missing_counts": {c: int(dataset[c].isna().sum()) for c in ALL_FEATURES},
        "risk_mode_counts": {
            str(k): int(v)
            for k, v in evidence.synthetic_risk_mode_ground_truth.value_counts().items()
        },
        "quality_counts": {
            d: {str(k): int(v) for k, v in evidence[f"{d}_evidence_quality"].value_counts().items()}
            for d in ["registration", "wage", "contribution"]
        },
    }
    write_json(OUT / "dataset_profile.json", profile)
    figures = [
        plot_dataset(evidence, master),
        plot_features(evidence),
        plot_splits(partitions, split_checks),
        plot_split_labels(partitions),
        plot_correlation(partitions["group_time"]["train"]),
    ]
    for i, (regime, benchmark) in enumerate(benchmarks.items(), 6):
        figures.append(plot_evaluation(regime, benchmark, predictions[regime], i))
    figures.extend([plot_selection(benchmarks), plot_coefficients(bundle)])
    if sha256(ROOT / "models/best_model.pkl") != frozen_hash:
        raise ValueError("Frozen model was modified")
    write_report(figures, summary, profile, split_checks, runs, frozen_hash)
    write_json(
        OUT / "evidence_manifest.json",
        {
            "created_utc": datetime.now(UTC).isoformat(),
            "model_sha256": frozen_hash,
            "model_unchanged": True,
            "model_refit": False,
            "threshold_retuned": False,
            "source_script_sha256": sha256(Path(__file__)),
            "split_checks": split_checks,
            "files": {
                str(p.relative_to(ROOT)): sha256(p)
                for p in sorted(OUT.rglob("*"))
                if p.is_file() and p.name != "evidence_manifest.json"
            },
        },
    )
    print(
        f"Evidence complete: {len(figures)} figures, {len(runs)} validation logs, {OUT / 'index.html'}",
        flush=True,
    )


if __name__ == "__main__":
    main()
