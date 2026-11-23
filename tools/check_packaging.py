#!/usr/bin/env python3
"""Slice the build tree a second time and check the archives come out identical.

This catches the ordinary ways an archive stops being reproducible: a directory
walked in filesystem order, an mtime read off the disk, a gzip header carrying
the name and the time of the file it compressed.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from lib import layout, manifest, packaging
from lib.console import say


def main(argv: list[str] | None = None) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    target = arguments[0] if arguments and arguments[0] else None
    plan = layout.read()
    first = (plan.dist / manifest.CHECKSUMS).read_text(encoding="utf-8")

    with tempfile.TemporaryDirectory() as scratch:
        second = packaging.write_archives(plan, dist=Path(scratch) / "dist", target=target)
        again = (second / manifest.CHECKSUMS).read_text(encoding="utf-8")

    if first != again:
        say("✖ a second slice of the same build tree hashed differently")
        for line in sorted(set(again.splitlines()) - set(first.splitlines())):
            say(f"    {line}")
        return 1
    say("check-packaging: a second slice of the same build tree hashes the same")
    return 0


if __name__ == "__main__":
    sys.exit(main())
