from __future__ import annotations

import argparse
import contextlib
import json
import os
import shutil
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
ENV_NAME = "routescout_phase8b"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="/content/routescout_phase8b_clean")
    parser.add_argument(
        "--build-jobs",
        type=int,
        default=max(1, min(os.cpu_count() or 2, 4)),
    )
    args = parser.parse_args()

    root = Path(args.root)
    root.mkdir(parents=True, exist_ok=True)
    repo = root / "PCBWorld"
    artifacts = root / "artifacts"
    artifacts.mkdir(exist_ok=True)

    code_root = Path(__file__).resolve().parents[1]
    env_file = code_root / "environment" / "phase8_conda.yml"
    requirements_file = code_root / "environment" / "phase8_pip.txt"

    if shutil.which("rsync") is None:
        run_command(["apt-get", "-qq", "update"], timeout=900)
        run_command(["apt-get", "-qq", "install", "-y", "rsync"], timeout=900)

    miniforge = Path("/opt/miniforge3")
    conda = miniforge / "bin" / "conda"
    if not conda.exists():
        installer = root / f"Miniforge3-{MINIFORGE_VERSION}-Linux-x86_64.sh"
        run_command(["wget", "-q", MINIFORGE_URL, "-O", installer], timeout=900)
        if sha256_file(installer) != MINIFORGE_SHA256:
            raise RuntimeError("Miniforge installer SHA mismatch")
        run_command(
            ["bash", installer, "-b", "-p", miniforge],
            timeout=1200,
            stream=True,
        )

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
            stream=True,
        )

    run_command(
        ["git", "submodule", "update", "--init", "--recursive", "engine"],
        cwd=repo,
        timeout=2400,
        stream=True,
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
            stream=True,
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
        stream=True,
    )

    build = repo / "build_rl"
    cli = build / "kicad" / "kicad-cli"
    pcbnew_py = build / "pcbnew" / "pcbnew.py"
    pcbnew_so = build / "pcbnew" / "_pcbnew.so"
    router_modules = list((build / "pcbnew/python/rl").glob("kicad_rl_router*.so"))

    if not (
        router_modules
        and cli.is_file()
        and pcbnew_py.is_file()
        and pcbnew_so.is_file()
    ):
        build_script = repo / "engine" / "build_rl_router.sh"
        original = build_script.read_text(encoding="utf-8")
        patched = original.replace(
            "ninja $NINJA_TARGETS",
            'ninja -j "${ROUTESCOUT_BUILD_JOBS:-2}" $NINJA_TARGETS',
            1,
        )
        if patched == original:
            raise RuntimeError("Pinned build script changed")

        build_script.write_text(patched, encoding="utf-8")
        try:
            env = os.environ.copy()
            env.update(
                {
                    "BUILD_CLI": "1",
                    "BUILD_PCBNEW": "1",
                    "BUILD_DIR": str(build),
                    "ROUTESCOUT_BUILD_JOBS": str(args.build_jobs),
                }
            )
            run_command(
                [
                    conda,
                    "run",
                    "-n",
                    ENV_NAME,
                    "bash",
                    "engine/build_rl_router.sh",
                    "--conda",
                ],
                cwd=repo,
                env=env,
                timeout=14400,
                stream=True,
            )
        finally:
            build_script.write_text(original, encoding="utf-8")

    schemas = build / "schemas"
    schemas.mkdir(exist_ok=True)
    for target in (
        "schema_build_copy",
        "api_schema_build_copy",
        "remote_provider_schema_build_copy",
    ):
        with contextlib.suppress(subprocess.CalledProcessError):
            run_command(["ninja", target], cwd=build, timeout=300, stream=True)

    if not list(schemas.glob("*.json")):
        schema_sources = (
            build / "kicad_src/kicad/pcm/schemas",
            build / "kicad_src/api/schemas",
            build / "kicad_src/resources/schemas",
        )
        for source_dir in schema_sources:
            if source_dir.is_dir():
                for source in source_dir.glob("*.json"):
                    shutil.copy2(source, schemas / source.name)

    if not list(schemas.glob("*.json")):
        raise RuntimeError("KiCad build-tree schemas missing")

    conda_prefix = miniforge / "envs" / ENV_NAME
    library_dirs = [
        conda_prefix / "lib",
        build / "common",
        build / "common/gal",
        build / "pcbnew",
        build / "kicad",
    ]
    ld_library_path = ":".join(map(str, library_dirs))

    wrapper = root / "kicad-cli-buildtree-wrapper.sh"
    wrapper.write_text(
        f"""#!/usr/bin/env bash
set -euo pipefail
export KICAD_RUN_FROM_BUILD_DIR=1
export KICAD_CLI_UNCAPPED=1
export PCBWORLD_KICAD_RL_BUILD_DIR='{build}'
export LD_LIBRARY_PATH='{ld_library_path}':${{LD_LIBRARY_PATH:-}}
exec '{cli}' "$@"
""",
        encoding="utf-8",
    )
    wrapper.chmod(0o755)

    env = os.environ.copy()
    env.update(
        {
            "KICAD_RUN_FROM_BUILD_DIR": "1",
            "KICAD_CLI_UNCAPPED": "1",
            "PCBWORLD_KICAD_RL_BUILD_DIR": str(build),
            "LD_LIBRARY_PATH": ld_library_path
            + (":" + env["LD_LIBRARY_PATH"] if env.get("LD_LIBRARY_PATH") else ""),
        }
    )
    version = run_command(
        [wrapper, "--version"],
        cwd=repo,
        env=env,
        timeout=120,
    ).strip()

    state = {
        "root": str(root),
        "repo": str(repo),
        "build_root": str(build),
        "conda": str(conda),
        "env_name": ENV_NAME,
        "wrapper": str(wrapper),
        "python": str(conda_prefix / "bin/python"),
        "pcbworld_commit": repo_commit,
        "engine_commit": engine_commit,
        "kicad_cli_version": version,
        "ld_library_path": env["LD_LIBRARY_PATH"],
    }
    (artifacts / "clean_bootstrap_state.json").write_text(
        json.dumps(state, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(state, indent=2))


if __name__ == "__main__":
    main()
