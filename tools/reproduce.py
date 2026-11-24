#!/usr/bin/env python3
"""Deciding which release to rebuild, and comparing a rebuild against it.

Both halves were shell in the reproducibility workflow. Resolving the release is
a three-way decision over a JSON field, and comparing is a parse of two
`sha256sum` files followed by a verdict per asset. `sha256sum --check` gets the
first three verdicts below and cannot reach the fourth, because it only looks up
the names the published file lists.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from lib.console import say
from lib.take import take_literal, take_while

HEX = frozenset("0123456789abcdef")
DIGEST_LENGTH = 64
CHECKSUMS = "SHA256SUMS"


class ChecksumsError(Exception):
    """A checksum file that is not in the format `sha256sum` writes."""


class Verdict(Enum):
    MATCHES = "matches"
    DIFFERS = "differs"
    MISSING = "missing from the rebuild"
    UNPUBLISHED = "produced by the rebuild but not in the release"


@dataclass(frozen=True)
class Comparison:
    name: str
    verdict: Verdict


def parse_checksums(text: str) -> dict[str, str]:
    """Read `sha256sum` output: a hex digest, a two-character separator, a name."""
    entries: dict[str, str] = {}
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        digest = take_while(line, HEX)
        if digest is None or len(digest[0]) != DIGEST_LENGTH:
            raise ChecksumsError(f"line {number} does not begin with a {DIGEST_LENGTH}-character digest: {line!r}")
        value, rest = digest
        # `sha256sum` separates with two spaces, or a space and an asterisk for
        # a file it read in binary mode.
        separator = take_literal(rest, "  ") or take_literal(rest, " *")
        if separator is None:
            raise ChecksumsError(f"line {number} has no separator after the digest: {line!r}")
        _, name = separator
        if not name:
            raise ChecksumsError(f"line {number} names no file: {line!r}")
        entries[name] = value
    if not entries:
        raise ChecksumsError("the checksum file is empty")
    return entries


def compare(published: dict[str, str], rebuilt: dict[str, str]) -> list[Comparison]:
    """One verdict per file, in the order the release lists them, then the extras."""
    results = [
        Comparison(
            name=name,
            verdict=Verdict.MISSING
            if name not in rebuilt
            else Verdict.MATCHES
            if rebuilt[name] == digest
            else Verdict.DIFFERS,
        )
        for name, digest in published.items()
    ]
    results += [Comparison(name=name, verdict=Verdict.UNPUBLISHED) for name in rebuilt if name not in published]
    return results


def gh(arguments: list[str]) -> str:
    result = subprocess.run(["gh", *arguments], capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit(f"reproduce: gh {' '.join(arguments)} failed: {result.stderr.strip()}")
    return result.stdout


def latest_tag(repository: str) -> str:
    """The most recent release's tag, or the empty string when there is none."""
    listed = json.loads(gh(["release", "list", "--repo", repository, "--limit", "1", "--json", "tagName"]))
    if not isinstance(listed, list) or not listed:
        return ""
    first = listed[0]
    tag = first.get("tagName") if isinstance(first, dict) else None
    return tag if isinstance(tag, str) else ""


def write_output(name: str, value: str) -> None:
    """Hand a value to the next workflow step, or print it when run outside one."""
    destination = os.environ.get("GITHUB_OUTPUT")
    if destination is None:
        # No workflow is reading, so this is for a person at a terminal.
        say(f"{name}={value}")
        return
    with Path(destination).open("a", encoding="utf-8") as handle:
        handle.write(f"{name}={value}\n")


def command_resolve(arguments: argparse.Namespace) -> int:
    """Pick the release to rebuild: the one asked for, else the latest, else none."""
    tag = arguments.requested.strip()
    if not tag:
        tag = latest_tag(arguments.repository)
    if not tag:
        # A workflow command, which the runner parses out of stdout.
        sys.stdout.write(f"::notice ::{arguments.repository} has no release to rebuild yet\n")
    else:
        say(f"reproduce: rebuilding {tag}")
    write_output("tag", tag)
    return 0


def command_compare(arguments: argparse.Namespace) -> int:
    """Compare a rebuild in `--dist` against the checksums its release carries."""
    dist: Path = arguments.dist
    published_path = dist.parent / f"published.{CHECKSUMS}"
    gh(
        [
            "release",
            "download",
            arguments.release,
            "--repo",
            arguments.repository,
            "--pattern",
            CHECKSUMS,
            "--output",
            str(published_path),
            "--clobber",
        ]
    )

    published = parse_checksums(published_path.read_text(encoding="utf-8"))
    rebuilt = parse_checksums((dist / CHECKSUMS).read_text(encoding="utf-8"))
    results = compare(published, rebuilt)

    width = max(len(result.name) for result in results)
    for result in results:
        say(f"  {result.name:<{width}}  {result.verdict.value}")

    unmatched = [result for result in results if result.verdict is not Verdict.MATCHES]
    if unmatched:
        say(f"\n✖ {arguments.release} did not reproduce:")
        for result in unmatched:
            say(f"    {result.name}: {result.verdict.value}")
        return 1
    say(f"\n{arguments.release} reproduced, every asset byte for byte")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True, help="owner/name to read releases from")
    subcommands = parser.add_subparsers(dest="command", required=True)

    resolve = subcommands.add_parser("resolve", help="decide which release to rebuild")
    resolve.add_argument("--requested", default="", help="the release asked for, if any")
    resolve.set_defaults(run=command_resolve)

    comparison = subcommands.add_parser("compare", help="compare a rebuild against its release")
    comparison.add_argument("--release", required=True, help="the release's tag")
    comparison.add_argument("--dist", type=Path, default=Path("dist"), help="where the rebuild wrote its archives")
    comparison.set_defaults(run=command_compare)

    arguments = parser.parse_args(argv)
    run = arguments.run
    result = run(arguments)
    return result if isinstance(result, int) else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ChecksumsError as error:
        say(f"reproduce: {error}")
        sys.exit(1)
