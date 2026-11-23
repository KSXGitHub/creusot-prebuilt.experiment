#!/usr/bin/env python3
"""What the Rust half of the build has to work out before cargo runs.

Three things here were shell. The host triple was `rustc -vV | sed`, written
twice in the Creusot build script and a third time in Python, so one fact had
three spellings. The package list is a decision about the target. The
`--remap-path-prefix` flags decide what the published binaries contain, which
makes them the most consequential strings in the build.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

import rust_toolchain
from take import take_literal

HOST_FIELD = "host: "

SHIPPED_EVERYWHERE = ("cargo-creusot", "creusot-install")
"""Built for whichever target is asked for."""

SHIPPED_FOR_THE_HOST_ONLY = ("creusot-rustc",)
"""`creusot-rustc` is a rustc driver: it is compiled against `rustc-dev` and
loads `librustc_driver` out of the toolchain at run time. rustup ships
`rustc-dev` for the host triple alone, so this can be built for the host and for
no other target."""

REMAPPED_TO = {
    "source": "/build/creusot",
    "cargo home": "/build/cargo",
    "rustup home": "/build/rustup",
}
"""Where each real directory is made to look like it was, so that two machines
with different home directories produce the same bytes. The rustup home is here
because `rustc-dev`'s sources sit under the toolchain and their paths reach
`creusot-rustc`: 96 of them for Creusot 0.15.0."""


def host_triple() -> str:
    """The triple `rustc` reports for itself, read off its `key: value` output."""
    output = subprocess.run(["rustc", "-vV"], capture_output=True, text=True, check=True).stdout
    for line in output.splitlines():
        field = take_literal(line, HOST_FIELD)
        if field is not None:
            return field[1].strip()
    raise SystemExit("rust-build: rustc reports no host triple")


def packages_for(target: str, host: str) -> tuple[str, ...]:
    """The packages to build for `target`, which is every shipped one on the host."""
    if target == host:
        return SHIPPED_EVERYWHERE + SHIPPED_FOR_THE_HOST_ONLY
    return SHIPPED_EVERYWHERE


def _home(variable: str, fallback: str) -> Path:
    configured = os.environ.get(variable)
    return Path(configured) if configured else Path.home() / fallback


def remap_flags(source: Path) -> str:
    """The `--remap-path-prefix` flags the Rust build runs with."""
    real = {
        "source": source,
        "cargo home": _home("CARGO_HOME", ".cargo"),
        "rustup home": _home("RUSTUP_HOME", ".rustup"),
    }
    return " ".join(f"--remap-path-prefix={real[name]}={fixed}" for name, fixed in REMAPPED_TO.items())


def command_host(_: argparse.Namespace) -> int:
    print(host_triple())
    return 0


def command_packages(arguments: argparse.Namespace) -> int:
    target = arguments.target or host_triple()
    packages = packages_for(target, host_triple())
    if not set(SHIPPED_FOR_THE_HOST_ONLY) <= set(packages):
        skipped = ", ".join(SHIPPED_FOR_THE_HOST_ONLY)
        print(f"rust-build: {target} is not the host, so {skipped} is skipped", file=sys.stderr)
    print(" ".join(f"-p {package}" for package in packages))
    return 0


def command_component_flags(arguments: argparse.Namespace) -> int:
    toolchain = rust_toolchain.read(arguments.source)
    print(" ".join(f"-c {component}" for component in toolchain.components))
    return 0


def command_rustflags(arguments: argparse.Namespace) -> int:
    print(remap_flags(arguments.source))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)

    host = subcommands.add_parser("host", help="the triple rustc reports for itself")
    host.set_defaults(run=command_host)

    packages = subcommands.add_parser("packages", help="the cargo -p flags for a target")
    packages.add_argument("--target", default="", help="the target triple; this host's when empty")
    packages.set_defaults(run=command_packages)

    components = subcommands.add_parser("component-flags", help="the rustup -c flags the tag asks for")
    components.add_argument("--source", type=Path, required=True, help="the Creusot checkout")
    components.set_defaults(run=command_component_flags)

    rustflags = subcommands.add_parser("rustflags", help="the --remap-path-prefix flags")
    rustflags.add_argument("--source", type=Path, required=True, help="the Creusot checkout")
    rustflags.set_defaults(run=command_rustflags)

    arguments = parser.parse_args(argv)
    run = arguments.run
    result = run(arguments)
    return result if isinstance(result, int) else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except rust_toolchain.ToolchainError as error:
        print(f"rust-build: {error}", file=sys.stderr)
        sys.exit(1)
