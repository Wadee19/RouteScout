import pandas as pd
import pytest

from routescout.integrity import validate_phase8b_run_table


def _manifest():
    return {"boards": [{"d3_id": "a"}]}


def _runs():
    return pd.DataFrame(
        [
            {
                "d3_id": "a",
                "policy": "natural",
                "api_error": "",
                "issued_order_exact": True,
            },
            {
                "d3_id": "a",
                "policy": "mst_hard_first",
                "api_error": "",
                "issued_order_exact": True,
            },
            {
                "d3_id": "a",
                "policy": "mst_easy_first",
                "api_error": "",
                "issued_order_exact": True,
            },
        ]
    )


def test_valid_run_table_passes():
    validate_phase8b_run_table(_runs(), _manifest())


def test_api_error_fails():
    runs = _runs()
    runs.loc[0, "api_error"] = "boom"
    with pytest.raises(RuntimeError):
        validate_phase8b_run_table(runs, _manifest())
