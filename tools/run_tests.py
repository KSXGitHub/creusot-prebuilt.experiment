#!/usr/bin/env python3
"""Run the unit tests, naming each one as it goes."""

from __future__ import annotations

import argparse
import sys

from lib import layout, test_report

TESTS = "tests"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "pattern",
        nargs="?",
        default=None,
        help="run only the tests whose module.Class.method name holds this",
    )
    arguments = parser.parse_args(argv)
    return test_report.run(layout.repository_root() / TESTS, arguments.pattern)


if __name__ == "__main__":
    sys.exit(main())
