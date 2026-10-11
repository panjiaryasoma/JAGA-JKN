"""
Exploratory Data Analysis visualizations.
Generates publication-quality charts for label distribution,
evidence quality distributions, and feature correlation profiles.
"""

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from pipelines.configure.config import COL_BINARY_LABEL, COL_RAW_RISK_MODE, FIGURES_DIR

FIGURES_DIR.mkdir(parents=True, exist_ok=True)

PALETTE = ["#2ecc71", "#e74c3c", "#f39c12", "#3498db", "#9b59b6"]
DARK_BG = "#0f1117"
PANEL_BG = "#1a1d27"
AXIS_CLR = "#aaa"
SPINE_CLR = "#444"


def _style_axes(ax):
    ax.set_facecolor(PANEL_BG)
    ax.tick_params(colors="white")
    ax.spines[["top", "right"]].set_visible(False)
    for s in ["left", "bottom"]:
        ax.spines[s].set_color(SPINE_CLR)


def plot_label_distribution(df: pd.DataFrame) -> Path:
    """Generate side-by-side distribution plots for multi-class and binary targets."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.patch.set_facecolor(DARK_BG)

    # Subplot 1: 5-class ground truth
    ax1 = axes[0]
    _style_axes(ax1)
    vc = df[COL_RAW_RISK_MODE].value_counts()
    bars = ax1.bar(vc.index, vc.values, color=PALETTE)
    ax1.set_title(
        "Ground Truth Risk Mode Distribution (5 Classes)",
        color="white",
        fontsize=12,
        fontweight="bold",
    )
    ax1.set_xlabel("Risk Mode", color=AXIS_CLR)
    ax1.set_ylabel("Sample Count", color=AXIS_CLR)
    for bar, val in zip(bars, vc.values):
        ax1.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 40,
            f"{val:,}",
            ha="center",
            color="white",
            fontsize=9,
        )
    ax1.tick_params(axis="x", rotation=20)

    # Subplot 2: Binary target
    ax2 = axes[1]
    _style_axes(ax2)
    binary_counts = df[COL_BINARY_LABEL].value_counts().sort_index()
    bars2 = ax2.bar(
        ["NORMAL (0)", "NON-NORMAL (1)"],
        binary_counts.values,
        color=["#2ecc71", "#e74c3c"],
        width=0.5,
    )
    ax2.set_title(
        "Binary Target: NORMAL vs NON-NORMAL", color="white", fontsize=12, fontweight="bold"
    )
    ax2.set_xlabel("Target Class", color=AXIS_CLR)
    ax2.set_ylabel("Sample Count", color=AXIS_CLR)
    for bar, val in zip(bars2, binary_counts.values):
        pct = val / binary_counts.sum() * 100
        ax2.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 40,
            f"{val:,}\n({pct:.1f}%)",
            ha="center",
            color="white",
            fontsize=10,
        )

    plt.suptitle(
        "Dataset Label Distribution Overview", color="white", fontsize=14, fontweight="bold", y=1.02
    )
    plt.tight_layout()
    output_path = FIGURES_DIR / "eda_01_label_distribution.png"
    plt.savefig(output_path, dpi=150, bbox_inches="tight", facecolor=DARK_BG)
    plt.close()
    return output_path


def plot_evidence_quality(df: pd.DataFrame) -> Path:
    """Generate distribution histogram of composite evidence reliability across risk modes."""
    fig, ax = plt.subplots(figsize=(12, 5))
    fig.patch.set_facecolor(DARK_BG)
    _style_axes(ax)

    risk_mode_order = [
        "NORMAL",
        "WORKER_REGISTRATION_GAP",
        "CONTRIBUTION_PAYMENT_GAP",
        "WAGE_REPORTING_GAP",
        "MULTI_SIGNAL",
    ]
    for i, label in enumerate(risk_mode_order):
        subset = df[df[COL_RAW_RISK_MODE] == label]["evidence_quality_composite"].dropna()
        if len(subset):
            ax.hist(subset, bins=30, alpha=0.6, label=label, color=PALETTE[i])

    ax.set_title(
        "Composite Evidence Reliability Score by Risk Mode",
        color="white",
        fontsize=13,
        fontweight="bold",
    )
    ax.set_xlabel("Composite Reliability Score", color=AXIS_CLR)
    ax.set_ylabel("Frequency", color=AXIS_CLR)
    ax.legend(facecolor="#2a2d37", labelcolor="white", fontsize=8)

    plt.tight_layout()
    output_path = FIGURES_DIR / "eda_02_evidence_quality_per_label.png"
    plt.savefig(output_path, dpi=150, bbox_inches="tight", facecolor=DARK_BG)
    plt.close()
    return output_path


def plot_feature_correlation_heatmap(corr_df: pd.DataFrame) -> Path:
    """Generate horizontal bar chart of top candidate feature correlations vs binary label."""
    top_df = corr_df.dropna(subset=["abs_correlation"]).head(20).sort_values("abs_correlation")

    fig, ax = plt.subplots(figsize=(10, 7))
    fig.patch.set_facecolor(DARK_BG)
    _style_axes(ax)

    bar_colors = [
        "#e74c3c" if val > 0.4 else "#f39c12" if val > 0.2 else "#2ecc71"
        for val in top_df["abs_correlation"]
    ]
    ax.barh(top_df["feature"], top_df["abs_correlation"], color=bar_colors, alpha=0.85)
    ax.axvline(0.2, color="#f39c12", ls="--", lw=1, alpha=0.7, label="Moderate Threshold (0.2)")
    ax.axvline(
        0.4, color="#e74c3c", ls="--", lw=1, alpha=0.7, label="High / Leakage Threshold (0.4)"
    )
    ax.set_title(
        "Absolute Point-Biserial Correlation vs Binary Target",
        color="white",
        fontsize=12,
        fontweight="bold",
    )
    ax.set_xlabel("|Correlation|", color=AXIS_CLR)
    ax.tick_params(colors="white", labelsize=8)
    ax.legend(facecolor="#2a2d37", labelcolor="white", fontsize=9)

    plt.tight_layout()
    output_path = FIGURES_DIR / "eda_03_feature_correlation.png"
    plt.savefig(output_path, dpi=150, bbox_inches="tight", facecolor=DARK_BG)
    plt.close()
    return output_path


def run(df: pd.DataFrame, corr_df: pd.DataFrame = None) -> list:
    """Execute complete EDA plotting suite. Returns list of generated image paths."""
    print("[EDA] Generating label distribution plot")
    p1 = plot_label_distribution(df)

    print("[EDA] Generating evidence quality distribution plot")
    p2 = plot_evidence_quality(df)

    paths = [p1, p2]
    if corr_df is not None:
        print("[EDA] Generating feature correlation plot")
        p3 = plot_feature_correlation_heatmap(corr_df)
        paths.append(p3)

    print(f"   {len(paths)} visualization figures saved to: {FIGURES_DIR}")
    return paths


if __name__ == "__main__":
    from pipelines.audit.leakage_audit import audit_correlation
    from pipelines.features.feature_engineering import build_full_dataset

    dataset = build_full_dataset()
    correlations = audit_correlation(dataset)
    run(dataset, correlations)
