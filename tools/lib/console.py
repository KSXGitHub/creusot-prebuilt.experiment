"""Writing to the person running the command.

Narration goes to stderr: progress, what was assembled, which switch was
reused, why a check failed. stdout carries only what another program consumes,
so a caller can redirect it without catching commentary, and a hook's
explanation cannot end up in whatever was reading its output.

Nothing here writes to stdout. The places that do are the ones with a reader:
`tools/release_body.py`, whose markdown the deployment workflow redirects into
a file, and `tools/reproduce.py`, which writes a step output and a workflow
command the runner parses. Both use `sys.stdout.write` directly, and ruff's
`T20` rules reject `print` so that neither channel is chosen by accident.
"""

from __future__ import annotations

import sys


def say(message: str = "") -> None:
    """Tell the person something. Never the program reading stdout."""
    sys.stderr.write(f"{message}\n")
    sys.stderr.flush()
