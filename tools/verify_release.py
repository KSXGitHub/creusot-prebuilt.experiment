#!/usr/bin/env python3
"""Check that a tag, the commit it points at, and pkgver/pkgrel all agree."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from lib import layout, release_contract


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=None, help="the checkout to read")
    parser.add_argument("ref", help="the tag, or the refs/tags/... ref")
    parser.add_argument("commit", nargs="?", default="HEAD", help="the commit the tag points at")
    arguments = parser.parse_args(argv)
    repo = arguments.repo if arguments.repo is not None else layout.repository_root()
    return release_contract.check_tag(repo, arguments.ref, arguments.commit)


if __name__ == "__main__":
    sys.exit(main())
