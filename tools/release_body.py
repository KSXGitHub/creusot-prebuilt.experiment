#!/usr/bin/env python3
"""Render the body of a GitHub release from the metadata the build wrote."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from lib import inventory, manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("metadata", type=Path, help=f"the {manifest.RELEASE_METADATA} the build wrote")
    parser.add_argument("--repository", required=True, help="owner/name, for the download and verification commands")
    arguments = parser.parse_args(argv)

    metadata = json.loads(arguments.metadata.read_text(encoding="utf-8"))
    metadata["repository"] = arguments.repository
    # The deployment workflow redirects this into the file it hands to `gh`.
    sys.stdout.write(inventory.render(metadata))
    return 0


if __name__ == "__main__":
    sys.exit(main())
