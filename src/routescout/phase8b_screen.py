from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from pcb_world.core.env import PCBWorld

from routescout.constants import ENGINE_SEED, RESET_SEED
from routescout.geometry import numeric_net_id
from routescout.io import canonical_sha256, read_json, sha256_file, write_json


def pad_records(net_obj: dict[str, Any]) -> list[dict[str, Any]]:
    pads = net_obj.get("pads", {})
    if isinstance(pads, dict):
        items = [(str(key), pads[key]) for key in sorted(pads)]
    elif isinstance(pads, list):
        items = [(str(index), pad) for index, pad in enumerate(pads)]
    else:
        return []

    records = []
    for key, pad in items:
        xy = pad.get("center", {}).get("xy")
        layer = pad.get("layer")
        if not isinstance(xy, (list, tuple)) or len(xy) < 2 or layer is None:
            continue
        records.append(
            {
                "key": key,
                "x": float(xy[0]),
                "y": float(xy[1]),
                "layer": int(layer),
            }
        )
    return records


def screen_board(
    row: dict[str, Any],
    min_targets: int,
    max_targets: int,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    guide = Path(row["guide_path"])
    pro = Path(row["pro_path"])
    if not guide.is_file() or not pro.is_file():
        return None, {**row, "reason": "d3_prepare_missing"}

    env = PCBWorld(
        board_path=str(guide),
        max_steps=64,
        engine_seed=ENGINE_SEED,
        seed=RESET_SEED,
        drc_penalty=0.0,
        emit_drc_tokens=False,
    )
    try:
        obs, _ = env.reset(seed=RESET_SEED, options={"preserve_routing": True})
        geometry: dict[int, dict[str, Any]] = {}
        for key, obj in obs["board_static"]["nets"].items():
            pads = pad_records(obj)
            if len(pads) != 2 or pads[0]["layer"] != pads[1]["layer"]:
                continue
            distance = math.hypot(
                pads[1]["x"] - pads[0]["x"],
                pads[1]["y"] - pads[0]["y"],
            )
            if distance <= 1e-9:
                continue
            net_id = numeric_net_id(key, obj)
            geometry[net_id] = {"mst_mm": distance, "pads": pads}
    finally:
        env.close()

    if len(geometry) < min_targets:
        return None, {
            **row,
            "reason": "too_few_same_layer_two_pad_nets",
            "count": len(geometry),
        }

    candidates = set(geometry)
    env = PCBWorld(
        board_path=str(guide),
        target_nets=candidates,
        preserve_nontarget_routing=True,
        max_steps=max(64, 4 * len(candidates) + 20),
        engine_seed=ENGINE_SEED,
        seed=RESET_SEED,
        drc_penalty=0.0,
        emit_drc_tokens=False,
    )
    try:
        env.reset(seed=RESET_SEED)
        born_closed = {int(value) for value in (env._born_closed_nets or [])}
    finally:
        env.close()

    active = sorted(candidates - born_closed)
    if len(active) < min_targets:
        return None, {
            **row,
            "reason": "too_few_active_after_target_strip",
            "count": len(active),
        }

    if len(active) > max_targets:
        active = sorted(
            active,
            key=lambda net_id: hashlib.sha256(
                f"{row['d3_id']}|{net_id}".encode()
            ).hexdigest(),
        )[:max_targets]
        active = sorted(active)

    natural = sorted(active)
    hard = sorted(active, key=lambda net_id: (-geometry[net_id]["mst_mm"], net_id))
    easy = sorted(active, key=lambda net_id: (geometry[net_id]["mst_mm"], net_id))

    if hard == natural:
        return None, {
            **row,
            "reason": "hard_order_equals_natural",
            "count": len(active),
        }

    return (
        {
            **row,
            "guide_sha256": sha256_file(guide),
            "pro_sha256": sha256_file(pro),
            "target_nets": active,
            "target_count": len(active),
            "terminal_mst_mm": {str(net_id): geometry[net_id]["mst_mm"] for net_id in active},
            "pad_geometry": {str(net_id): geometry[net_id]["pads"] for net_id in active},
            "orders": {
                "natural": natural,
                "mst_hard_first": hard,
                "mst_easy_first": easy,
            },
            "born_closed_excluded": sorted(born_closed & candidates),
        },
        None,
    )


def build_manifest(payload: dict[str, Any]) -> dict[str, Any]:
    boards = []
    skips = []
    for row in payload["boards"]:
        board, skip = screen_board(
            row,
            min_targets=int(payload["min_targets"]),
            max_targets=int(payload["max_targets"]),
        )
        if board is not None:
            boards.append(board)
        if skip is not None:
            skips.append(skip)

    manifest = {
        "phase": "08B",
        "protocol_sha256": payload["protocol_sha256"],
        "selection_pre_outcome": True,
        "boards": boards,
        "skips": skips,
    }
    manifest["manifest_sha256"] = canonical_sha256(manifest)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_json")
    parser.add_argument("output_json")
    args = parser.parse_args()

    manifest = build_manifest(read_json(args.input_json))
    write_json(args.output_json, manifest, sort_keys=False)
    print(
        json.dumps(
            {
                "eligible_boards": len(manifest["boards"]),
                "skipped_boards": len(manifest["skips"]),
                "manifest_sha256": manifest["manifest_sha256"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
