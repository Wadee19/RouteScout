from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def paired_table(frame: pd.DataFrame, metric: str) -> pd.DataFrame:
    pivot = frame.pivot(
        index=["difficulty", "d3_id"],
        columns="policy",
        values=metric,
    )
    return pivot.dropna(subset=["natural", "mst_hard_first"])


def paired_bootstrap_mean_ci(
    delta: pd.Series | np.ndarray,
    *,
    resamples: int = 10_000,
    seed: int = 47,
) -> dict[str, Any]:
    values = np.asarray(delta, dtype=float)
    values = values[np.isfinite(values)]
    if len(values) == 0:
        return {"n": 0, "mean": None, "ci95": [None, None]}

    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(values), size=(resamples, len(values)))
    means = values[idx].mean(axis=1)
    return {
        "n": len(values),
        "mean": float(values.mean()),
        "ci95": [
            float(np.quantile(means, 0.025)),
            float(np.quantile(means, 0.975)),
        ],
    }


def analyze_phase8b(runs: pd.DataFrame) -> tuple[dict[str, Any], pd.DataFrame]:
    """Reproduce the frozen Phase 8B paired analysis from a validated run table."""
    rout = paired_table(runs, "target_routability")
    drc = paired_table(runs, "full_drc_errors")
    clean = paired_table(runs, "target_clean_success").astype(float)
    action_fail = paired_table(runs, "action_failure_count")

    rout_ci = paired_bootstrap_mean_ci(rout["mst_hard_first"] - rout["natural"])
    drc_ci = paired_bootstrap_mean_ci(drc["mst_hard_first"] - drc["natural"])
    clean_ci = paired_bootstrap_mean_ci(clean["mst_hard_first"] - clean["natural"])
    action_fail_ci = paired_bootstrap_mean_ci(
        action_fail["mst_hard_first"] - action_fail["natural"]
    )

    wide = runs.pivot(index=["difficulty", "d3_id"], columns="policy")
    common_valid = (
        wide["target_success"]["natural"].astype(bool)
        & wide["target_success"]["mst_hard_first"].astype(bool)
        & (wide["full_drc_errors"]["natural"] == 0)
        & (wide["full_drc_errors"]["mst_hard_first"] == 0)
    )
    common_idx = wide.index[common_valid]

    wire = paired_table(runs, "wirelength_mm")
    wire = wire.loc[wire.index.intersection(common_idx)]
    wire_ci = paired_bootstrap_mean_ci(wire["mst_hard_first"] - wire["natural"])

    vias = paired_table(runs, "via_count")
    vias = vias.loc[vias.index.intersection(common_idx)]
    via_ci = paired_bootstrap_mean_ci(vias["mst_hard_first"] - vias["natural"])

    ceiling = bool(
        (rout["natural"] >= 1 - 1e-12).all()
        and (rout["mst_hard_first"] >= 1 - 1e-12).all()
    )
    drc_harm = bool(drc_ci["ci95"][0] is not None and drc_ci["ci95"][0] > 0)

    if not ceiling:
        if rout_ci["ci95"][0] is not None and rout_ci["ci95"][0] > 0:
            decision = (
                "SUPPORTED_ROUTABILITY_GAIN_WITH_DRC_HARM"
                if drc_harm
                else "SUPPORTED_ROUTABILITY_GAIN_NO_CLEAR_DRC_HARM"
            )
        elif rout_ci["ci95"][1] is not None and rout_ci["ci95"][1] < 0:
            decision = "HARD_FIRST_WORSE_ON_ROUTABILITY"
        else:
            decision = "NO_CLEAR_ROUTABILITY_BENEFIT"
    else:
        if wire_ci["n"] >= 5 and wire_ci["ci95"][1] is not None and wire_ci["ci95"][1] < 0:
            decision = (
                "SUPPORTED_WIRELENGTH_GAIN_UNDER_ROUTABILITY_CEILING_WITH_DRC_HARM"
                if drc_harm
                else "SUPPORTED_WIRELENGTH_GAIN_UNDER_ROUTABILITY_CEILING"
            )
        elif wire_ci["n"] >= 5 and wire_ci["ci95"][0] is not None and wire_ci["ci95"][0] > 0:
            decision = "HARD_FIRST_WORSE_ON_WIRELENGTH_UNDER_ROUTABILITY_CEILING"
        else:
            decision = "NO_CLEAR_ENGINEERING_BENEFIT_UNDER_ROUTABILITY_CEILING"

    summary = (
        runs.groupby("policy", as_index=False)
        .agg(
            boards=("d3_id", "nunique"),
            target_routability=("target_routability", "mean"),
            target_success=("target_success", "mean"),
            target_clean_success=("target_clean_success", "mean"),
            full_drc_errors=("full_drc_errors", "mean"),
            action_failure_count=("action_failure_count", "mean"),
            wirelength_mm=("wirelength_mm", "mean"),
            via_count=("via_count", "mean"),
            elapsed_seconds=("elapsed_seconds", "mean"),
        )
    )

    result = {
        "decision": decision,
        "valid_boards": int(runs["d3_id"].nunique()),
        "common_valid_boards": len(common_idx),
        "routability_ceiling": ceiling,
        "hard_minus_natural": {
            "target_routability": rout_ci,
            "whole_board_drc_errors": drc_ci,
            "target_clean_success": clean_ci,
            "action_failure_count": action_fail_ci,
            "wirelength_mm_common_valid": wire_ci,
            "via_count_common_valid": via_ci,
        },
        "drc_harm_flag": drc_harm,
    }
    return result, summary
