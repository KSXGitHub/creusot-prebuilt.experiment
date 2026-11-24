"""The Rust toolchain a Creusot tag pins, read from its `rust-toolchain` file.

The file is TOML, so it is parsed as TOML. Both the build script and the
packaging step need what it says, and this is the only place that knows where in
the file to look.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

FILE_NAME = "rust-toolchain"


class ToolchainError(Exception):
    """A `rust-toolchain` file that does not say what the build needs."""


@dataclass(frozen=True)
class Toolchain:
    channel: str
    """The rustup channel, such as `nightly-2026-08-03`. `creusot-rustc` loads
    `librustc_driver` out of this toolchain at run time, so an installation has
    to carry it under this exact name."""

    components: tuple[str, ...]
    """The rustup components the build needs, `rustc-dev` among them."""


def read(source: Path) -> Toolchain:
    try:
        with (source / FILE_NAME).open("rb") as handle:
            document = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise ToolchainError(f"cannot read {source / FILE_NAME}: {error}") from error

    table = document.get("toolchain")
    if not isinstance(table, dict):
        raise ToolchainError(f"{FILE_NAME} has no [toolchain] table")
    channel = table.get("channel")
    if not isinstance(channel, str) or not channel:
        raise ToolchainError(f"{FILE_NAME} names no toolchain.channel")
    listed = table.get("components", [])
    if not isinstance(listed, list) or not all(isinstance(entry, str) for entry in listed):
        raise ToolchainError(f"{FILE_NAME} has a toolchain.components that is not a list of strings")
    return Toolchain(channel=channel, components=tuple(listed))
