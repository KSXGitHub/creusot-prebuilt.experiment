"""Slice the build tree a second time and check the archives come out identical.

This catches the ordinary ways an archive stops being reproducible: a directory
walked in filesystem order, an mtime read off the disk, a gzip header carrying
the name and the time of the file it compressed.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import layout
import manifest
import package


def main(argv: list[str] | None = None) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    target = arguments[0] if arguments and arguments[0] else None
    plan = layout.read()
    first = (plan.dist / manifest.CHECKSUMS).read_text(encoding="utf-8")

    with tempfile.TemporaryDirectory() as scratch:
        second = Path(scratch) / "dist"
        package.main(
            [
                "--repo",
                str(plan.repo),
                "--source",
                str(plan.source),
                "--dist",
                str(second),
                *(["--target", target] if target else []),
            ]
        )
        again = (second / manifest.CHECKSUMS).read_text(encoding="utf-8")

    if first != again:
        print("✖ a second slice of the same build tree hashed differently", file=sys.stderr)
        for line in sorted(set(again.splitlines()) - set(first.splitlines())):
            print(f"    {line}", file=sys.stderr)
        return 1
    print("check-packaging: a second slice of the same build tree hashes the same")
    return 0


if __name__ == "__main__":
    sys.exit(main())
