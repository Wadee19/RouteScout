from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path

from bootstrap_common import run_command, sha256_file

MINIFORGE_VERSION = "26.7.2-0"
MINIFORGE_SHA256 = "281b0ac7d550802efc81af633225a5e6116d29ae72f3ab4eae7168c3931a4c05"
MINIFORGE_URL = (
    "https://github.com/conda-forge/miniforge/releases/download/"
    f"{MINIFORGE_VERSION}/Miniforge3-{MINIFORGE_VERSION}-Linux-x86_64.sh"
)
PCBWORLD_VERSION = "v1.0.0"
PCBWORLD_COMMIT = "ed411746224fb82d876248798a61db11b1ca3866"
ENGINE_COMMIT = "a6430fd44b65e0b6653fe49041a18d8d4d724890"
ENV_NAME = "pcbworld_phase8a"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="/content/routescout_phase8a")
    args = parser.parse_args()

    root = Path(args.root)
    root.mkdir(parents=True, exist_ok=True)
    repo = root / "PCBWorld"
    artifacts = root / "artifacts"
    artifacts.mkdir(exist_ok=True)

    code_root = Path(__file__).resolve().parents[1]
    env_file = code_root / "environment" / "phase8_conda.yml"
    requirements_file = code_root / "environment" / "phase8_pip.txt"

    miniforge = Path("/opt/miniforge3")
    conda = miniforge / "bin" / "conda"
    if not conda.exists():
        installer = root / f"Miniforge3-{MINIFORGE_VERSION}-Linux-x86_64.sh"
        run_command(["wget", "-q", MINIFORGE_URL, "-O", installer], timeout=900)
        if sha256_file(installer) != MINIFORGE_SHA256:
            raise RuntimeError("Miniforge installer SHA mismatch")
        run_command(["bash", installer, "-b", "-p", miniforge], timeout=900)

    # conda-forge only; no dependency on the Anaconda default-channel ToS.
    subprocess.run(
        [str(conda), "config", "--system", "--remove-key", "channels"],
        check=False,
    )
    run_command([conda, "config", "--system", "--add", "channels", "conda-forge"])
    run_command([conda, "config", "--system", "--set", "channel_priority", "strict"])
    run_command([conda, "config", "--system", "--set", "solver", "libmamba"])

    if not repo.exists():
        run_command(
            [
                "git",
                "clone",
                "--branch",
                PCBWORLD_VERSION,
                "--depth",
                "1",
                "https://github.com/LGAI-Research/PCBWorld.git",
                repo,
            ],
            timeout=1200,
        )

    run_command(
        ["git", "submodule", "update", "--init", "--recursive", "engine"],
        cwd=repo,
        timeout=2400,
    )

    repo_commit = run_command(["git", "rev-parse", "HEAD"], cwd=repo).strip().splitlines()[-1]
    engine_commit = (
        run_command(["git", "-C", "engine", "rev-parse", "HEAD"], cwd=repo)
        .strip()
        .splitlines()[-1]
    )
    if repo_commit != PCBWORLD_COMMIT or engine_commit != ENGINE_COMMIT:
        raise RuntimeError("PCBWorld/engine commit drift")

    environments = run_command([conda, "env", "list"])
    if not any(
        line.split() and line.split()[0] == ENV_NAME
        for line in environments.splitlines()
    ):
        run_command(
            [
                conda,
                "env",
                "create",
                "-n",
                ENV_NAME,
                "-f",
                env_file,
                "--solver",
                "libmamba",
                "-y",
            ],
            cwd=repo,
            timeout=4200,
        )

    run_command(
        [
            conda,
            "run",
            "-n",
            ENV_NAME,
            "python",
            "-m",
            "pip",
            "install",
            "-r",
            requirements_file,
        ],
        cwd=repo,
        timeout=1800,
    )

    router_modules = list((repo / "build_rl").rglob("kicad_rl_router*.so"))
    if not router_modules:
        env = os.environ.copy()
        env["BUILD_DIR"] = str(repo / "build_rl")
        process = subprocess.run(
            [
                str(conda),
                "run",
                "-n",
                ENV_NAME,
                "bash",
                "engine/build_rl_router.sh",
            ],
            cwd=repo,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=10800,
            check=False,
        )
        print(process.stdout[-20000:])
        if process.returncode:
            raise subprocess.CalledProcessError(
                process.returncode,
                process.args,
                output=process.stdout,
            )

    state = {
        "root": str(root),
        "repo": str(repo),
        "conda": str(conda),
        "env_name": ENV_NAME,
        "pcbworld_commit": repo_commit,
        "engine_commit": engine_commit,
    }
    (artifacts / "clean_bootstrap_state.json").write_text(
        json.dumps(state, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(state, indent=2))


if __name__ == "__main__":
    main()
