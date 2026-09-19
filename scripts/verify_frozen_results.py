from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

EXPECTED_RELEASES = {
    "phase7_release_sha256": "e32432bd7c02c9defe1a40e42f94120ddc07e21a901b1f7d1b8dd166f815fac6",
    "phase8a_release_sha256": "cc65bec2fae71ea480f75df04c0d9fa254b9efa6df100f45910d906cea267790",
    "phase8b_release_sha256": "da003a672157b5a44e1c6f6cb17802e9735ab02626b0a0b6c89f235300b0b24b",
}
EXPECTED_SPEARMAN = 0.9240179379260456
EXPECTED_TOP5_CAPTURE = 0.9809876927692095
EXPECTED_PHASE8B_DECISION = "NO_CLEAR_ROUTABILITY_BENEFIT"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> None:
    metrics = json.loads(
        (ROOT / "results" / "final_metrics.json").read_text(encoding="utf-8")
    )

    require(
        metrics["frozen_releases"] == EXPECTED_RELEASES,
        "Frozen release SHA-256 identities do not match the canonical release.",
    )
    require(
        metrics["heldout_test"]["mst_spearman"] == EXPECTED_SPEARMAN,
        "Held-out MST Spearman drift detected.",
    )
    require(
        metrics["heldout_test"]["top5_cost_capture"] == EXPECTED_TOP5_CAPTURE,
        "Held-out Top-5 cost capture drift detected.",
    )
    require(
        metrics["phase8b"]["decision"] == EXPECTED_PHASE8B_DECISION,
        "Phase 8B frozen decision drift detected.",
    )

    print("PASS — frozen public results and release identities verified")


if __name__ == "__main__":
    main()
