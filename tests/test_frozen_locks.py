import hashlib
import json
from pathlib import Path

import pandas as pd

from routescout.evaluation import analyze_phase8b
from routescout.integrity import validate_phase8b_run_table


ROOT = Path(__file__).resolve().parents[1]

EXPECTED_PROTOCOL = "7cbea24ee392b7b29ebf134beb3744135f7038b9a25ee5f2b0898e99bdc8f732"
EXPECTED_MANIFEST = "692357feeaba88bdf978337acd3579233b69cac0edca9172cff1b1b67287fb54"
EXPECTED_RUNNER = "ad97beed8ca97ee98f50634724269987c260c2f764642c75c71b4722a15344a0"


def _canonical_sha256(obj, embedded_key):
    value = dict(obj)
    value.pop(embedded_key, None)
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def test_phase8b_protocol_and_manifest_locks():
    protocol = json.loads(
        (ROOT / "configs" / "phase8b_preregistration_v4.json").read_text()
    )
    manifest = json.loads(
        (ROOT / "configs" / "phase8b_exact_manifest_v4.json").read_text()
    )

    assert protocol["preregistration_sha256"] == EXPECTED_PROTOCOL
    assert _canonical_sha256(protocol, "preregistration_sha256") == EXPECTED_PROTOCOL

    assert manifest["protocol_sha256"] == EXPECTED_PROTOCOL
    assert manifest["manifest_sha256"] == EXPECTED_MANIFEST
    assert _canonical_sha256(manifest, "manifest_sha256") == EXPECTED_MANIFEST

    assert len(manifest["boards"]) == 24
    counts = pd.Series([board["difficulty"] for board in manifest["boards"]]).value_counts()
    assert counts.to_dict() == {"easy": 10, "hard": 8, "medium": 6}


def test_phase8b_frozen_runner_identity():
    runner = ROOT / "src" / "routescout" / "phase8b_runner.py"
    assert hashlib.sha256(runner.read_bytes()).hexdigest() == EXPECTED_RUNNER


def test_phase8b_frozen_run_table_reproduces_decision():
    runs = pd.read_csv(ROOT / "results" / "phase8b_policy_runs_frozen.csv")
    runs["api_error"] = runs["api_error"].fillna("")
    manifest = json.loads(
        (ROOT / "configs" / "phase8b_exact_manifest_v4.json").read_text()
    )
    expected = json.loads(
        (ROOT / "results" / "phase8b_frozen_result.json").read_text()
    )

    validate_phase8b_run_table(runs, manifest)
    result, _ = analyze_phase8b(runs)

    assert result["decision"] == expected["decision"]
    assert (
        result["hard_minus_natural"]["target_routability"]
        == expected["hard_minus_natural"]["target_routability"]
    )
    assert (
        result["hard_minus_natural"]["whole_board_drc_errors"]
        == expected["hard_minus_natural"]["whole_board_drc_errors"]
    )
