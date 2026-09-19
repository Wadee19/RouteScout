from __future__ import annotations

import hashlib
import os
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path


def sha256_file(path: str | Path) -> str:
    """Return the SHA-256 digest of a file without loading it all into memory."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_command(
    args: Sequence[object],
    *,
    cwd: str | Path | None = None,
    env: Mapping[str, str] | None = None,
    timeout: int | None = None,
    stream: bool = False,
) -> str:
    """Run a command without shell=True and return combined stdout/stderr."""
    command = [str(value) for value in args]
    print("$", " ".join(command), flush=True)

    merged_env = os.environ.copy()
    if env:
        merged_env.update({str(key): str(value) for key, value in env.items()})

    if stream:
        process = subprocess.Popen(
            command,
            cwd=str(cwd) if cwd else None,
            env=merged_env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
        )
        lines: list[str] = []
        if process.stdout is None:
            raise RuntimeError("subprocess stdout pipe was not created")
        for line in process.stdout:
            print(line, end="", flush=True)
            lines.append(line)

        return_code = process.wait(timeout=timeout)
        output = "".join(lines)
        if return_code:
            raise subprocess.CalledProcessError(return_code, command, output=output)
        return output

    process = subprocess.run(
        command,
        cwd=str(cwd) if cwd else None,
        env=merged_env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=True,
        timeout=timeout,
    )
    if process.stdout:
        print(process.stdout[-12000:])
    return process.stdout
