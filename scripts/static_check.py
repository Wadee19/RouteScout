from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "routescout"
FROZEN_RUNNER = SRC / "phase8b_runner.py"
FROZEN_RUNNER_SHA = "ad97beed8ca97ee98f50634724269987c260c2f764642c75c71b4722a15344a0"
PHASE8A_CLEAN_RUNNER = SRC / "phase8a_runner.py"
PHASE8A_CLEAN_RUNNER_SHA = "07e2b0968e3af398b1b231d8ed724faf07af2c54a15bcee5b2a20bb8c4c39782"

FORBIDDEN_NOTEBOOK_TOKENS = (
    "/content/",
    "pip install",
    "conda install",
    "apt-get",
    "wget -q",
    "shell=True",
)

STALE_PUBLIC_REFERENCES = (
    "`frozen_notebooks/`",
    "`audits/`",
    "phase8a_runner_frozen.py",
)

GENERATED_NAMES = {".pytest_cache", "__pycache__", ".ruff_cache", ".ipynb_checkpoints"}


def sha256_file(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


problems: list[str] = []

for folder in (ROOT / "src", ROOT / "scripts", ROOT / "tests"):
    for path in sorted(folder.rglob("*.py")):
        try:
            ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError as exc:
            problems.append(f"python syntax: {path.relative_to(ROOT)}: {exc}")

for path in sorted((ROOT / "notebooks").glob("*.ipynb")):
    notebook = json.loads(path.read_text(encoding="utf-8"))
    seen_ids: set[str] = set()
    for index, cell in enumerate(notebook.get("cells", [])):
        cell_id = cell.get("id")
        if cell_id and cell_id in seen_ids:
            problems.append(f"duplicate notebook cell id: {path.name}:{cell_id}")
        if cell_id:
            seen_ids.add(cell_id)

        source = cell.get("source", "")
        if isinstance(source, list):
            source = "".join(source)

        if cell.get("cell_type") == "markdown":
            for target in re.findall(r"\[[^]]*\]\(([^)]+)\)", source):
                if target.startswith(("http://", "https://", "#", "mailto:")):
                    continue
                local_target = target.split("#", 1)[0]
                if not local_target:
                    continue
                resolved = (path.parent / local_target).resolve()
                if not resolved.exists():
                    problems.append(
                        f"broken notebook link: {path.name} cell {index}: {target}"
                    )
            continue

        if cell.get("cell_type") != "code":
            continue

        try:
            ast.parse(source)
        except SyntaxError as exc:
            problems.append(f"notebook syntax: {path.name} cell {index}: {exc}")

        for output in cell.get("outputs", []):
            if output.get("output_type") == "error":
                problems.append(
                    f"notebook error output: {path.name} cell {index}: "
                    f"{output.get('ename')}: {output.get('evalue')}"
                )

        for token in FORBIDDEN_NOTEBOOK_TOKENS:
            if token in source:
                problems.append(f"notebook hygiene: {path.name} cell {index}: {token}")

        for token in STALE_PUBLIC_REFERENCES:
            if token in source:
                problems.append(
                    f"stale public reference: {path.name} cell {index}: {token}"
                )

for path in sorted((ROOT / "notebooks").glob("*.ipynb")):
    raw = path.read_text(encoding="utf-8", errors="ignore")
    if "/Users/" in raw or re.search(r"[A-Za-z]:\\\\Users\\\\", raw):
        problems.append(f"private workstation path in notebook: {path.name}")
    if re.search(r"\\bgh[pousr]_[A-Za-z0-9]{20,}", raw):
        problems.append(f"possible GitHub token in notebook: {path.name}")
    if re.search(r"\\bsk-[A-Za-z0-9_-]{20,}", raw):
        problems.append(f"possible OpenAI-style token in notebook: {path.name}")

if sha256_file(FROZEN_RUNNER) != FROZEN_RUNNER_SHA:
    problems.append("frozen Phase 8B runner SHA-256 drift")

if sha256_file(PHASE8A_CLEAN_RUNNER) != PHASE8A_CLEAN_RUNNER_SHA:
    problems.append("reviewed Phase 8A clean runner SHA-256 drift")

pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
init_text = (SRC / "__init__.py").read_text(encoding="utf-8")
project_version = re.search(r'^version\s*=\s*"([^"]+)"', pyproject, re.MULTILINE)
module_version = re.search(r'__version__\s*=\s*"([^"]+)"', init_text)
if not project_version or not module_version or project_version.group(1) != module_version.group(1):
    problems.append("package version mismatch between pyproject.toml and __init__.py")

PUBLIC_SCAN_ROOTS = (
    ROOT / "README.md",
    ROOT / "pyproject.toml",
    ROOT / ".github",
    ROOT / "configs",
    ROOT / "docs",
    ROOT / "notebooks",
    ROOT / "scripts",
    ROOT / "src",
    ROOT / "tests",
)

scan_files: list[Path] = []
for scan_root in PUBLIC_SCAN_ROOTS:
    if scan_root.is_file():
        scan_files.append(scan_root)
    elif scan_root.is_dir():
        scan_files.extend(path for path in scan_root.rglob("*") if path.is_file())

for path in sorted(set(scan_files)):
    if path.resolve() == Path(__file__).resolve():
        continue
    if path.suffix not in {".py", ".md", ".json", ".toml", ".yml", ".yaml"}:
        continue

    content = path.read_text(encoding="utf-8", errors="ignore")
    if re.search(r"\bsk-[A-Za-z0-9_-]{20,}", content):
        problems.append(
            f"possible OpenAI-style secret token: {path.relative_to(ROOT)}"
        )
    if re.search(r"\bgh[pousr]_[A-Za-z0-9]{20,}", content):
        problems.append(f"possible GitHub token: {path.relative_to(ROOT)}")
    if "/Users/" in content or re.search(r"[A-Za-z]:\\Users\\", content):
        problems.append(f"private workstation path: {path.relative_to(ROOT)}")

if problems:
    print("FAIL")
    for problem in problems:
        print("-", problem)
    sys.exit(1)

print("PASS — repository hygiene, syntax, versions and frozen runner identities")
