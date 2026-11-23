#!/usr/bin/env python3
"""Render the body of a GitHub release from the metadata the build wrote.

These are not release notes and do not try to be. Nothing here narrates a
change: what changed upstream belongs to Creusot and is reached through the tag
this body links, and what changed between two build revisions of one version is
in this repository's commit log. What a consumer cannot get anywhere else is an
inventory, and that is what this renders: every asset, where it unpacks, how to
install a subset of them, what the build read, and how to check what was
downloaded.

The asset table is the one `tools/lib/manifest.py` holds, so it is generated
rather than kept in step by hand.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from lib import manifest

PREFIX_NOTES = {
    "creusot-data-home": "the Creusot data directory",
    "why3-prefix": "`{why3_prefix}`",
}


def human_size(size: int) -> str:
    """A size a reader can compare at a glance, in the unit that suits it."""
    return f"{size / 1e6:.1f} MB" if size >= 1_000_000 else f"{size / 1e3:.0f} kB"


def render(metadata: dict[str, Any]) -> str:
    why3_prefix = metadata["why3_prefix"]
    lines = [
        "Built from Creusot "
        f"[`{metadata['creusot_tag']}`](https://github.com/creusot-rs/creusot/releases/tag/{metadata['creusot_tag']})"
        f" (`{metadata['creusot_commit']}`). `pkgver` {metadata['pkgver']}, `pkgrel` {metadata['pkgrel']}.",
        "",
        "| asset | unpacks at | size | holds |",
        "| --- | --- | --- | --- |",
    ]
    for asset in metadata["assets"]:
        where = PREFIX_NOTES[asset["prefix"]].format(why3_prefix=why3_prefix)
        lines.append(f"| `{asset['file']}` | {where} | {human_size(asset['size'])} | {asset['summary']} |")
    lines += [
        "",
        "Every archive unpacks at the directory its row names, and needs no further moving.",
        "The Creusot data directory is `$CREUSOT_DATA_HOME`, else `$XDG_DATA_HOME/creusot`, else",
        "`~/.local/share/creusot`, which is where `cargo-creusot` looks for the tools it spawns.",
        f"`why3` compiles `{why3_prefix}` in, so it reads its theories from there wherever it",
        "is run from, and unpacking that archive anywhere else leaves it reading a directory",
        "that is not there.",
        "",
        "## Installing",
        "",
        "```bash",
        f"curl -fsSLO https://github.com/{metadata['repository']}/releases/download/{metadata['tag']}/install.py",
        f"python3 install.py --release {metadata['tag']} --list",
        f"python3 install.py --release {metadata['tag']} cargo-creusot creusot-rustc",
        "```",
        "",
        "## Build inputs",
        "",
        f"- Rust toolchain: `{metadata['rust_channel']}`",
        f"- Target: `{metadata['target']}`",
        "- opam pins: " + ", ".join(f"`{name} {version}`" for name, version in sorted(metadata["opam_pins"].items())),
        f"- `SOURCE_DATE_EPOCH`: `{metadata['source_date_epoch']}`",
        "",
        f"`{manifest.CHECKSUMS}` holds the checksum of every archive and of "
        f"`{manifest.INSTALLER}`, in the format `sha256sum --check` reads. "
        f"`{manifest.RELEASE_METADATA}` describes the same archives, and is what "
        f"`{manifest.INSTALLER}` reads to find them.",
        "",
        "Every uploaded file also has a GitHub build provenance attestation. It records the",
        "workflow run that produced the file, and is bound to the file's digest rather than",
        "its name, so a renamed download still verifies:",
        "",
        "```bash",
        f"gh attestation verify <file> --repo {metadata['repository']}",
        "```",
    ]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("metadata", type=Path, help=f"the {manifest.RELEASE_METADATA} the build wrote")
    parser.add_argument("--repository", required=True, help="owner/name, for the download and verification commands")
    arguments = parser.parse_args(argv)

    metadata = json.loads(arguments.metadata.read_text(encoding="utf-8"))
    metadata["repository"] = arguments.repository
    sys.stdout.write(render(metadata))
    return 0


if __name__ == "__main__":
    sys.exit(main())
