import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def test_phase8a_frozen_evidence_is_clean():
    runs = pd.read_csv(ROOT / "results" / "phase8a_pilot_runs_frozen.csv")
    summary = json.loads(
        (ROOT / "results" / "phase8a_runner_summary_frozen.json").read_text()
    )

    assert summary == {
        "boards_scanned": 32,
        "eligible_boards": 3,
        "runs": 18,
        "api_error_runs": 0,
        "order_mismatch_runs": 0,
    }
    assert len(runs) == 18
    assert runs["board"].nunique() == 3
    assert set(runs["policy"]) == {
        "natural",
        "mst_hard_first",
        "mst_easy_first",
    }
    assert runs["order_exact"].astype(bool).all()
    assert runs["api_error"].isna().all()
