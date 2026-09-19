from __future__ import annotations

import math
import re
from typing import Any


def numeric_net_id(key: Any, obj: dict[str, Any]) -> int:
    """Return the numeric net id used by the pinned PCBWorld observations."""
    for candidate in (obj.get("net_id"), obj.get("id"), key):
        if isinstance(candidate, int):
            return candidate
        match = re.search(r"(\d+)$", str(candidate))
        if match:
            return int(match.group(1))
    raise ValueError(f"Cannot infer numeric net id from {key!r}")


def pads_by_key(net_obj: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    """Return pads in the frozen Phase 8 ordering: pad key, not geometry."""
    pads = net_obj.get("pads", {})
    if isinstance(pads, dict):
        return [(key, pads[key]) for key in sorted(pads)]
    if isinstance(pads, list):
        return [(str(i), pad) for i, pad in enumerate(pads)]
    return []


def pad_xy(pad: dict[str, Any]) -> tuple[float, float]:
    value = pad.get("center", {}).get("xy")
    if not (isinstance(value, (list, tuple)) and len(value) >= 2):
        raise ValueError(f"Pad has no center.xy: {pad}")
    return float(value[0]), float(value[1])


def two_pad_mst_mm(net_obj: dict[str, Any]) -> float:
    """For a two-pad net, terminal MST length equals Euclidean pad distance."""
    pads = pads_by_key(net_obj)
    if len(pads) != 2:
        raise ValueError("two_pad_mst_mm requires exactly two pads")
    (_, p0), (_, p1) = pads
    x0, y0 = pad_xy(p0)
    x1, y1 = pad_xy(p1)
    return math.hypot(x1 - x0, y1 - y0)
