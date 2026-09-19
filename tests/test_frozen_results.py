import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_public_frozen_metrics_are_unchanged():
    metrics = json.loads((ROOT / "results" / "final_metrics.json").read_text())
    assert metrics["heldout_test"]["mst_spearman"] == 0.9240179379260456
    assert (
        metrics["heldout_test"]["top5_cost_capture"]
        == 0.9809876927692095
    )
    assert (
        metrics["phase8b"]["decision"]
        == "NO_CLEAR_ROUTABILITY_BENEFIT"
    )
