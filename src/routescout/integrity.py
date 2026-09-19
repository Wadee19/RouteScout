from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from .io import sha256_file


def assert_sha256(path: str | Path, expected: str) -> None:
    actual = sha256_file(path)
    if actual != expected:
        raise RuntimeError(f"SHA-256 mismatch for {path}: {actual} != {expected}")


def load_locked_json(path: str | Path, expected_embedded_sha: str | None = None) -> dict[str, Any]:
    obj = json.loads(Path(path).read_text(encoding="utf-8"))
    if expected_embedded_sha is not None:
        candidates = [obj.get("preregistration_sha256"), obj.get("manifest_sha256")]
        if expected_embedded_sha not in candidates:
            raise RuntimeError(f"Locked JSON identity mismatch: {path}")
    return obj


def validate_phase8b_run_table(runs: pd.DataFrame, manifest: dict[str, Any]) -> None:
    """Validate the invariants used by the frozen Phase 8B paired analysis."""
    if runs["d3_id"].nunique() != len(manifest["boards"]):
        raise RuntimeError("Board count does not match locked manifest")
    expected_rows = len(manifest["boards"]) * 3
    if len(runs) != expected_rows:
        raise RuntimeError(f"Expected {expected_rows} policy rows, found {len(runs)}")
    api_error = runs["api_error"].fillna("").astype(str)
    if (api_error != "").any():
        raise RuntimeError("API errors present in frozen run table")
    if not runs["issued_order_exact"].astype(bool).all():
        raise RuntimeError("At least one run did not issue the locked order exactly")
