#!/usr/bin/env python3
"""Slice the build tree into one archive per tool under dist/."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from lib import layout, packaging


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    # Every path defaults to what `tools/lib/layout.py` says, so the usual call
    # takes no arguments at all.
    parser.add_argument("--repo", type=Path, default=None, help="the checkout holding pkgver and pkgrel")
    parser.add_argument("--build", type=Path, default=None, help="the assembled build tree")
    parser.add_argument("--dist", type=Path, default=None, help="where the archives are written")
    parser.add_argument("--source", type=Path, default=None, help="the Creusot checkout the build came from")
    parser.add_argument("--target", default=None, help="the target triple (default: this host's)")
    arguments = parser.parse_args(argv)

    plan = layout.read(arguments.repo)
    dist = packaging.write_archives(
        plan,
        build=arguments.build,
        dist=arguments.dist,
        source=arguments.source,
        target=arguments.target,
    )
    sys.stdout.write((dist / "SHA256SUMS").read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
