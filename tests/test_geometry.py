import pytest

from routescout.geometry import numeric_net_id, pads_by_key, two_pad_mst_mm


def test_pad_key_order_is_frozen_semantics():
    net = {
        "pads": {
            "b": {"center": {"xy": [3, 4]}},
            "a": {"center": {"xy": [0, 0]}},
        }
    }
    assert [key for key, _ in pads_by_key(net)] == ["a", "b"]
    assert two_pad_mst_mm(net) == pytest.approx(5.0)


def test_numeric_net_id_falls_back_to_key_suffix():
    assert numeric_net_id("net_17", {}) == 17
