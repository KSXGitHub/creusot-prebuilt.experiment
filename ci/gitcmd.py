"""Running `git` and reading its output."""

from __future__ import annotations

import subprocess
from pathlib import Path


class GitError(Exception):
    """A `git` invocation that exited non-zero."""


def git_output(args: list[str], cwd: Path | None = None) -> str:
    """Run `git` with the given arguments and return its standard output.

    The output keeps whatever trailing newline git wrote: a caller that compares
    a commit message needs those bytes, and a caller that wants a single line
    strips them itself.
    """
    process = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    if process.returncode != 0:
        command = " ".join(["git", *args])
        raise GitError(f"{command} exited {process.returncode}: {process.stderr.strip()}")
    return process.stdout
