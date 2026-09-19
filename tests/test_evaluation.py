import numpy as np
import pandas as pd

from routescout.evaluation import paired_bootstrap_mean_ci, paired_table


def test_bootstrap_is_deterministic():
    values = np.array([0.0, 0.1, -0.1, 0.2])
    first = paired_bootstrap_mean_ci(values, resamples=500, seed=47)
    second = paired_bootstrap_mean_ci(values, resamples=500, seed=47)
    assert first == second


def test_paired_table_keeps_complete_natural_hard_pairs():
    frame = pd.DataFrame(
        [
            {
                "difficulty": "easy",
                "d3_id": "a",
                "policy": "natural",
                "metric": 0.4,
            },
            {
                "difficulty": "easy",
                "d3_id": "a",
                "policy": "mst_hard_first",
                "metric": 0.5,
            },
            {
                "difficulty": "easy",
                "d3_id": "a",
                "policy": "mst_easy_first",
                "metric": 0.3,
            },
        ]
    )
    out = paired_table(frame, "metric")
    assert len(out) == 1
    assert out.iloc[0]["mst_hard_first"] == 0.5
