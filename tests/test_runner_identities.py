import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PHASE8A_SHA = "07e2b0968e3af398b1b231d8ed724faf07af2c54a15bcee5b2a20bb8c4c39782"
PHASE8B_SHA = "ad97beed8ca97ee98f50634724269987c260c2f764642c75c71b4722a15344a0"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_locked_runner_identities():
    assert _sha(ROOT / "src" / "routescout" / "phase8a_runner.py") == PHASE8A_SHA
    assert _sha(ROOT / "src" / "routescout" / "phase8b_runner.py") == PHASE8B_SHA
