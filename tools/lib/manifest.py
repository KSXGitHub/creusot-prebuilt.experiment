"""Which built file goes into which release asset, and where that asset unpacks.

One asset holds one tool, so that a consumer who only needs `cargo creusot
--only coma` never downloads the prover framework. Each asset unpacks at a
*prefix*, and every path inside it is already correct relative to that prefix, so
installing is an extraction and nothing more.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Prefix(Enum):
    """The directory an asset unpacks at."""

    CREUSOT_DATA_HOME = "creusot-data-home"
    """`$CREUSOT_DATA_HOME`, else `$XDG_DATA_HOME/creusot`, else
    `~/.local/share/creusot`. This is where `cargo-creusot` looks for everything
    it did not come with, and it puts its own `bin` on `PATH` for the tools it
    spawns."""

    WHY3_PREFIX = "why3-prefix"
    """The absolute path recorded as `why3_prefix` in `release.json`. `why3`
    compiles its data directory in and honours neither `WHY3DATA` nor being
    moved, so this asset works at that one path and nowhere else."""


class Arch(Enum):
    """Whether an asset's content depends on the machine it runs on."""

    TARGET = "target"
    """Named after the target triple it was compiled for."""

    NOARCH = "noarch"
    """The same bytes on every target."""


@dataclass(frozen=True)
class Member:
    """One file or directory copied out of the build tree into an asset.

    `source` is relative to the build directory, whose `creusot/` and `why3/`
    subtrees the two build scripts assemble. `dest` is relative to the asset's
    prefix and may use `{channel}` for the Rust toolchain Creusot is pinned to.
    """

    source: str
    dest: str


@dataclass(frozen=True)
class Asset:
    """One uploaded archive."""

    name: str
    prefix: Prefix
    arch: Arch
    summary: str
    members: tuple[Member, ...]

    def file_name(self, tag: str, target: str) -> str:
        suffix = target if self.arch is Arch.TARGET else Arch.NOARCH.value
        return f"{self.name}-{tag}-{suffix}.tar.gz"


CREUSOT_LICENSE = "creusot/LICENSE"
WHY3FIND_LICENSE = "why3/LICENSE.why3find"

ASSETS: tuple[Asset, ...] = (
    Asset(
        name="cargo-creusot",
        prefix=Prefix.CREUSOT_DATA_HOME,
        arch=Arch.TARGET,
        summary="The `cargo creusot` subcommand, which drives every other tool here.",
        members=(
            Member("creusot/bin/cargo-creusot", "bin/cargo-creusot"),
            # Read from the data directory by `cargo-creusot` itself:
            # `creusot_why3.conf` is the solver configuration it passes to why3,
            # and `why3find.json` is what `cargo creusot new` seeds a project
            # with.
            Member("creusot/creusot_why3.conf", "creusot_why3.conf"),
            Member("creusot/why3find.json", "why3find.json"),
            Member(CREUSOT_LICENSE, "share/licenses/creusot/LICENSE"),
        ),
    ),
    Asset(
        name="creusot-rustc",
        prefix=Prefix.CREUSOT_DATA_HOME,
        arch=Arch.TARGET,
        summary="The rustc driver that turns a crate into Coma.",
        members=(
            Member("creusot/bin/creusot-rustc", "toolchains/{channel}/bin/creusot-rustc"),
            Member(CREUSOT_LICENSE, "share/licenses/creusot/LICENSE"),
        ),
    ),
    Asset(
        name="creusot-install",
        prefix=Prefix.CREUSOT_DATA_HOME,
        arch=Arch.TARGET,
        summary="Downloads the SMT solvers into the data directory.",
        members=(
            Member("creusot/bin/creusot-install", "bin/creusot-install"),
            Member(CREUSOT_LICENSE, "share/licenses/creusot/LICENSE"),
        ),
    ),
    Asset(
        name="creusot-prelude",
        prefix=Prefix.CREUSOT_DATA_HOME,
        arch=Arch.NOARCH,
        summary="The Coma prelude a proof is discharged against.",
        members=(
            Member("creusot/share/why3find/packages", "share/why3find/packages"),
            Member(CREUSOT_LICENSE, "share/licenses/creusot/LICENSE"),
        ),
    ),
    Asset(
        name="why3find",
        prefix=Prefix.CREUSOT_DATA_HOME,
        arch=Arch.TARGET,
        summary="The proof-session driver `cargo creusot prove` runs.",
        members=(
            Member("why3/bin/why3find", "bin/why3find"),
            Member(WHY3FIND_LICENSE, "share/licenses/why3find/LICENSE"),
        ),
    ),
    Asset(
        name="why3",
        prefix=Prefix.WHY3_PREFIX,
        arch=Arch.TARGET,
        summary="Why3 itself, with the `why3server` that runs the solvers.",
        members=(
            Member("why3/bin/why3", "bin/why3"),
            Member("why3/lib/why3", "lib/why3"),
            Member("why3/share/why3", "share/why3"),
        ),
    ),
)

RELEASE_METADATA = "release.json"
"""Names every asset of a release, its prefix and its checksum. Read by
`install.py`, which therefore hardcodes none of this."""

CHECKSUMS = "SHA256SUMS"
"""Every uploaded file's checksum, in the format `sha256sum --check` reads."""

INSTALLER = "install.py"
"""Uploaded beside the archives so that a release is enough on its own."""


def asset_by_name(name: str) -> Asset | None:
    for asset in ASSETS:
        if asset.name == name:
            return asset
    return None
