"""Running a command and stopping the build when it fails."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

from .console import say


class CommandError(Exception):
    """A command that exited non-zero."""


def run(
    command: Sequence[str | Path],
    *,
    cwd: Path | None = None,
    extra_env: Mapping[str, str] | None = None,
) -> None:
    """Run `command`, echoing it first so a CI log says what was done."""
    spelled = [str(word) for word in command]
    say("+ " + " ".join(spelled))
    environment = {**os.environ, **extra_env} if extra_env else None
    # What cargo, opam and rustup have to say is narration too, so it joins the
    # rest of it on stderr rather than reaching whoever is reading ours.
    result = subprocess.run(spelled, cwd=cwd, env=environment, stdout=sys.stderr)
    if result.returncode != 0:
        raise CommandError(f"{spelled[0]} exited {result.returncode}")


def output(
    command: Sequence[str | Path],
    *,
    cwd: Path | None = None,
    extra_env: Mapping[str, str] | None = None,
) -> str:
    """Run `command` and return its standard output.

    `extra_env` reaches the lookup of the program as well as the program
    itself, so a PATH put here is the one the command is found on.
    """
    spelled = [str(word) for word in command]
    environment = {**os.environ, **extra_env} if extra_env else None
    result = subprocess.run(spelled, cwd=cwd, capture_output=True, text=True, env=environment)
    if result.returncode != 0:
        raise CommandError(f"{spelled[0]} exited {result.returncode}: {result.stderr.strip()}")
    return result.stdout


def require(program: str, advice: str) -> None:
    """Stop with an explanation when a program the build needs is absent."""
    if shutil.which(program) is None:
        raise CommandError(f"{program} not found: {advice}")
