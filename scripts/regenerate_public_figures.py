"""Regenerate RouteScout public SVG figures from frozen release tables.

Presentation-only: no training, tuning, held-out reopening, or router rerun occurs here.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
FIGURES = ROOT / "figures"


def _save(fig: plt.Figure, name: str) -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(FIGURES / name, format="svg")
    plt.close(fig)


def plot_validation_to_test() -> None:
    df = pd.read_csv(RESULTS / "phase7_validation_to_test_generalization_frozen.csv")
    mst = df[df["model"].eq("MST-only")].set_index("metric")
    metrics = ["mean_board_spearman", "mean_top5_cost_capture", "mean_top5_overlap"]
    labels = ["Board Spearman", "Top-5 cost capture", "Top-5 overlap"]
    validation = [float(mst.loc[m, "validation"]) for m in metrics]
    heldout = [float(mst.loc[m, "test"]) for m in metrics]

    x = np.arange(len(labels))
    width = 0.36
    fig, ax = plt.subplots(figsize=(9.5, 5.0))
    bars_validation = ax.bar(x - width / 2, validation, width, label="Validation")
    bars_heldout = ax.bar(x + width / 2, heldout, width, label="Held-out test")
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Metric value")
    ax.set_title("Validation to held-out test")
    ax.set_xticks(x, labels)
    ax.legend(frameon=False)
    ax.grid(axis="y", alpha=0.2)
    ax.spines[["top", "right"]].set_visible(False)
    for bars in (bars_validation, bars_heldout):
        for bar in bars:
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.018,
                f"{bar.get_height():.3f}",
                ha="center",
                va="bottom",
                fontsize=9,
            )
    _save(fig, "phase9_01_validation_to_test.svg")


def plot_heldout_spearman_cdf() -> None:
    df = pd.read_csv(RESULTS / "phase7_heldout_board_metrics_frozen.csv")
    values = np.sort(
        pd.to_numeric(
            df.loc[df["model"].eq("MST-only"), "spearman"], errors="coerce"
        ).dropna().to_numpy()
    )
    cdf = np.arange(1, len(values) + 1) / len(values)

    fig, ax = plt.subplots(figsize=(8.0, 5.0))
    ax.plot(values, cdf, linewidth=2)
    ax.axvline(
        0.9240179379260456,
        linestyle="--",
        linewidth=1.2,
        label="Mean board Spearman",
    )
    ax.set_xlabel("Board-wise Spearman")
    ax.set_ylabel("Empirical CDF")
    ax.set_title("Held-out board-wise ranking")
    ax.grid(alpha=0.18)
    ax.legend(frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    _save(fig, "phase7_heldout_board_spearman_cdf.svg")


def plot_heldout_magnitude() -> None:
    metrics = json.loads((RESULTS / "final_metrics.json").read_text(encoding="utf-8"))
    mst_mae = float(metrics["heldout_test"]["mst_log_mae"])
    catboost_mae = float(metrics["heldout_test"]["catboost_log_mae"])

    fig, ax = plt.subplots(figsize=(6.8, 4.5))
    bars = ax.bar(["MST", "CatBoost residual"], [mst_mae, catboost_mae])
    ax.set_ylabel("Held-out log-MAE")
    ax.set_title("Magnitude estimation on held-out boards")
    ax.grid(axis="y", alpha=0.18)
    ax.spines[["top", "right"]].set_visible(False)
    for bar in bars:
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.003,
            f"{bar.get_height():.4f}",
            ha="center",
            va="bottom",
        )
    _save(fig, "phase7_heldout_catboost_magnitude.svg")


def plot_phase8a_feasibility() -> None:
    summary = json.loads(
        (RESULTS / "phase8a_runner_summary_frozen.json").read_text(encoding="utf-8")
    )
    runs = int(summary["runs"])
    api_success = runs - int(summary["api_error_runs"])
    exact_order = runs - int(summary["order_mismatch_runs"])
    boards_scanned = int(summary["boards_scanned"])
    eligible_boards = int(summary["eligible_boards"])

    api_pct = 100 * api_success / runs
    exact_pct = 100 * exact_order / runs
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="760" height="420"
     viewBox="0 0 760 420">
  <rect width="760" height="420" fill="white"/>
  <text x="380" y="38" text-anchor="middle" font-family="Arial, sans-serif" font-size="20"
        font-weight="600">Phase 8A engineering feasibility gate</text>
  <line x1="90" y1="320" x2="700" y2="320" stroke="#333" stroke-width="1"/>
  <line x1="90" y1="80" x2="90" y2="320" stroke="#333" stroke-width="1"/>
  <text x="42" y="202" text-anchor="middle" font-family="Arial, sans-serif" font-size="13"
        transform="rotate(-90 42 202)">Runs passing gate (%)</text>
  <rect x="180" y="{320 - 2.4 * api_pct:.1f}" width="150" height="{2.4 * api_pct:.1f}"
        fill="#4c78a8"/>
  <rect x="450" y="{320 - 2.4 * exact_pct:.1f}" width="150" height="{2.4 * exact_pct:.1f}"
        fill="#4c78a8"/>
  <text x="255" y="346" text-anchor="middle" font-family="Arial, sans-serif"
        font-size="14">API-success runs</text>
  <text x="525" y="346" text-anchor="middle" font-family="Arial, sans-serif"
        font-size="14">Exact-order runs</text>
  <text x="255" y="{312 - 2.4 * api_pct:.1f}" text-anchor="middle" font-family="Arial, sans-serif"
        font-size="15" font-weight="600">{api_success}/{runs}</text>
  <text x="525" y="{312 - 2.4 * exact_pct:.1f}" text-anchor="middle" font-family="Arial, sans-serif"
        font-size="15" font-weight="600">{exact_order}/{runs}</text>
  <text x="380" y="386" text-anchor="middle" font-family="Arial, sans-serif" font-size="13">
    {eligible_boards} eligible boards from {boards_scanned} scanned · {runs} pilot runs
  </text>
</svg>
"""
    (FIGURES / "phase8a_feasibility_gate.svg").write_text(svg, encoding="utf-8")


def _phase8b_runs() -> pd.DataFrame:
    df = pd.read_csv(RESULTS / "phase8b_policy_runs_frozen.csv")
    df["api_error"] = df["api_error"].fillna("")
    return df


def plot_phase8b_paired_routability() -> None:
    runs = _phase8b_runs()
    paired = runs.pivot(
        index=["difficulty", "d3_id"],
        columns="policy",
        values="target_routability",
    ).reset_index()

    fig, ax = plt.subplots(figsize=(6.8, 6.0))
    markers = {"easy": "o", "medium": "s", "hard": "^"}
    for difficulty, marker in markers.items():
        subset = paired[paired["difficulty"].eq(difficulty)]
        ax.scatter(
            subset["natural"],
            subset["mst_hard_first"],
            s=55,
            marker=marker,
            alpha=0.82,
            label=difficulty,
        )
    lower = float(min(paired["natural"].min(), paired["mst_hard_first"].min(), 0))
    ax.plot([lower, 1], [lower, 1], "--", linewidth=1.1)
    ax.set_xlabel("Natural-order target routability")
    ax.set_ylabel("MST hard-first target routability")
    ax.set_title("Paired real-board routability")
    ax.legend(frameon=False)
    ax.grid(alpha=0.15)
    ax.spines[["top", "right"]].set_visible(False)
    _save(fig, "phase8b_01_paired_routability.svg")


def plot_phase8b_primary_ci() -> None:
    frozen = json.loads(
        (RESULTS / "phase8b_frozen_result.json").read_text(encoding="utf-8")
    )
    primary = frozen["hard_minus_natural"]["target_routability"]
    mean = float(primary["mean"])
    low, high = map(float, primary["ci95"])

    fig, ax = plt.subplots(figsize=(8.0, 3.4))
    ax.axvline(0, linestyle="--", linewidth=1)
    ax.errorbar(
        [mean],
        [0],
        xerr=[[mean - low], [high - mean]],
        fmt="o",
        capsize=5,
    )
    ax.set_yticks([0], ["MST hard-first − natural"])
    ax.set_xlabel("Mean paired target-routability delta")
    ax.set_title("Primary effect — 95% paired-bootstrap CI")
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.grid(axis="x", alpha=0.18)
    _save(fig, "phase8b_02_primary_delta_ci.svg")


def plot_phase8b_drc_delta() -> None:
    runs = _phase8b_runs()
    paired = runs.pivot(
        index=["difficulty", "d3_id"],
        columns="policy",
        values="full_drc_errors",
    ).reset_index()
    paired["delta"] = paired["mst_hard_first"] - paired["natural"]

    fig, ax = plt.subplots(figsize=(8.0, 4.4))
    ax.scatter(range(len(paired)), paired["delta"])
    ax.axhline(0, linestyle="--", linewidth=1)
    ax.set_xlabel("Paired board")
    ax.set_ylabel("Whole-board DRC ERROR delta\n(hard-first − natural)")
    ax.set_title("Safety diagnostic — DRC error change by board")
    ax.grid(axis="y", alpha=0.18)
    ax.spines[["top", "right"]].set_visible(False)
    _save(fig, "phase8b_03_drc_delta.svg")


def main() -> None:
    plot_validation_to_test()
    plot_heldout_spearman_cdf()
    plot_heldout_magnitude()
    plot_phase8a_feasibility()
    plot_phase8b_paired_routability()
    plot_phase8b_primary_ci()
    plot_phase8b_drc_delta()
    print("Regenerated 7 public SVG figures from frozen results.")


if __name__ == "__main__":
    main()
