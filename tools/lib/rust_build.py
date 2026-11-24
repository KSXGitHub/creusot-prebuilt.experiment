"""What the Rust half of the build has to work out before cargo runs.

Three things here were shell. The host triple was `rustc -vV | sed`, written
twice in the Creusot build script and a third time in Python, so one fact had
three spellings. The package list is a decision about the target. The
`--remap-path-prefix` flags decide what the published binaries contain, which
makes them the most consequential strings in the build.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from .take import take_literal

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
