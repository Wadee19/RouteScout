from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path

from bootstrap_common import run_command

PCBENCH_COMMIT = "dec3be75cbdef74787625f9043c7391cd473bb64"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    state = json.loads(Path(args.state).read_text(encoding="utf-8"))
    locked = json.loads(Path(args.manifest).read_text(encoding="utf-8"))

    root = Path(state["root"])
    repo = Path(state["repo"])
    build = Path(state["build_root"])
    conda = Path(state["conda"])
    env_name = state["env_name"]
    wrapper = Path(state["wrapper"])
    python = Path(state["python"])

    data_root = root / "data"
    pcbench = data_root / "PCBench_locked"
    work = data_root / "locked_work"
    samples = sorted({board["sample"] for board in locked["boards"]})

    if not pcbench.exists():
        run_command(
            [
                "git",
                "clone",
                "--filter=blob:none",
                "--no-checkout",
                "--no-tags",
                "https://github.com/PCBench/PCBench.git",
                pcbench,
            ],
            timeout=1800,
        )
        run_command(["git", "sparse-checkout", "init", "--cone"], cwd=pcbench)

    sparse_paths = "\n".join(f"PCBs/{sample}" for sample in samples) + "\n"
    subprocess.run(
        ["git", "-C", str(pcbench), "sparse-checkout", "set", "--stdin"],
        input=sparse_paths,
        text=True,
        check=True,
    )
    run_command(
        ["git", "fetch", "--depth", "1", "origin", PCBENCH_COMMIT],
        cwd=pcbench,
        timeout=1800,
    )
    run_command(
        ["git", "checkout", "--detach", PCBENCH_COMMIT],
        cwd=pcbench,
        timeout=600,
    )

    pcbs = pcbench / "PCBs"
    v9 = work / "v9"
    new_drc = work / "newdrc"
    v9.mkdir(parents=True, exist_ok=True)
    new_drc.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env.update(
        {
            "PYTHONPATH": f"{repo}:{build/'pcbnew/python/rl'}:{build/'pcbnew'}",
            "KICAD_CLI": str(wrapper),
            "PCBNEW_PYTHON": str(python),
            "KICAD_RUN_FROM_BUILD_DIR": "1",
            "KICAD_CLI_UNCAPPED": "1",
            "PCBWORLD_KICAD_RL_BUILD_DIR": str(build),
            "LD_LIBRARY_PATH": state["ld_library_path"],
            "PCBENCH_PCBS_ROOT": str(pcbs),
            "PCBENCH_V9_ROOT": str(v9),
            "PCBENCH_NEWDRC_OUT": str(new_drc),
        }
    )

    prep = repo / "tools/datagen/pcbench_prep"
    run_command(
        [
            conda,
            "run",
            "-n",
            env_name,
            "python",
            prep / "convert_v9.py",
            "--workers",
            str(args.workers),
        ],
        cwd=repo,
        env=env,
        timeout=5400,
    )
    run_command(
        [
            conda,
            "run",
            "-n",
            env_name,
            "python",
            prep / "drc_fix_v9.py",
            "--workers",
            str(args.workers),
        ],
        cwd=repo,
        env=env,
        timeout=5400,
    )
    run_command(
        [
            conda,
            "run",
            "-n",
            env_name,
            "python",
            prep / "make_guide.py",
            "--base-dir",
            new_drc,
            "--stem",
            "processed_v9",
            "--suffix",
            "_guide_v3",
            "--workers",
            str(args.workers),
            "--log",
            work / "guide_log.json",
        ],
        cwd=repo,
        env=env,
        timeout=10800,
    )

    runtime = json.loads(json.dumps(locked))
    for board in runtime["boards"]:
        folder = new_drc / board["sample"]
        guide = folder / "processed_v9_guide_v3.kicad_pcb"
        project = folder / "processed_v9_guide_v3.kicad_pro"
        if not guide.is_file() or not project.is_file():
            raise RuntimeError(f"Prepared board missing: {board['d3_id']}")
        board["guide_path"] = str(guide)
        board["pro_path"] = str(project)

    runtime["runtime_only_paths_rebound"] = True
    Path(args.output).write_text(
        json.dumps(runtime, indent=2),
        encoding="utf-8",
    )
    print("Runtime manifest written:", args.output)


if __name__ == "__main__":
    main()
