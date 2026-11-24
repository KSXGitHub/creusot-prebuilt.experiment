"""Where the build puts things, and which release it is building.

Two of these directories are inputs to the build rather than scratch space,
because a compiler writes the paths it was given into what it produces:

- A Rust binary records the directory it was compiled in. `cargo-creusot` falls
  back to its own `CARGO_MANIFEST_DIR` when `CREUSOT_PATH` is unset, so
  `build_root` ends up inside it as a literal string.
- `why3` compiles its data directory in and honours neither `WHY3DATA` nor
  being moved, so it has to be built at the path it will be unpacked at, which
  is the `_opam` inside `why3_switch`.

Building elsewhere therefore produces different checksums, which is why both
have a fixed default rather than a temporary directory.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from . import release
from .gitcmd import git_output

# Not a temporary directory despite living under /var/tmp: the path is written
# into the binaries, so it is fixed on purpose and shared between runs.
BUILD_ROOT_DEFAULT = Path("/var/tmp/creusot-prebuilt")  # noqa: S108
WHY3_SWITCH_DEFAULT = Path("/opt/creusot-why3")
CREUSOT_REPO_DEFAULT = "https://github.com/creusot-rs/creusot"


@dataclass(frozen=True)
class Layout:
    repo: Path
    """The checkout this build is driven from."""

    release: release.Release
    """What `pkgver` and `pkgrel` say."""

    build_root: Path
    """Holds the Creusot checkout and the cargo target directory."""

    why3_switch: Path
    """The directory opam creates the Why3 switch in."""

    creusot_repo: str
    """Where the Creusot source is cloned from."""

    @property
    def version_root(self) -> Path:
        return self.build_root / f"v{self.release.pkgver}"

    @property
    def source(self) -> Path:
        """The Creusot checkout, at the tag this release is built from."""
        return self.version_root / "src"

    @property
    def cargo_target(self) -> Path:
        return self.version_root / "target"

    @property
    def stage(self) -> Path:
        """Where each half of the build assembles its tree before packaging."""
        return self.repo / "build"

    @property
    def creusot_stage(self) -> Path:
        return self.stage / "creusot"

    @property
    def why3_stage(self) -> Path:
        return self.stage / "why3"

    @property
    def dist(self) -> Path:
        """What gets uploaded."""
        return self.repo / "dist"

    @property
    def why3_prefix(self) -> Path:
        """The prefix opam installs the switch into, and the one `why3` bakes in."""
        return self.why3_switch / "_opam"

    @property
    def smoke_root(self) -> Path:
        """Holds one compiled dependency tree per driver the smoke test has seen."""
        return self.build_root / "smoke-test"

    def smoke_target(self, driver: str) -> Path:
        """Where the smoke test compiles the demo crate's dependencies.

        It sits under `build_root`, which the build cache carries, so the
        dependency tree is compiled once rather than on every run. The
        directory is named after the content of the installed driver, because
        `cargo-creusot` points cargo at `creusot-rustc` through `RUSTC` and
        cargo keys its own fingerprints on the version that binary reports
        rather than on the binary. Two build revisions of one Creusot version
        report the same version, so without this a new driver could reuse
        artefacts the old one produced.
        """
        return self.smoke_root / driver / "target"

    def source_date_epoch(self) -> int:
        """The upstream tag's commit date, which every mtime in every asset gets.

        It depends on the Creusot tag alone, so it does not move between build
        revisions of one version.
        """
        return int(git_output(["log", "-1", "--format=%ct"], cwd=self.source).strip())


def _directory(variable: str, fallback: Path) -> Path:
    configured = os.environ.get(variable)
    return Path(configured) if configured else fallback


def repository_root() -> Path:
    """The checkout this module lives in, found by climbing out of `tools/lib`.

    The climb is checked rather than trusted: moving this module without
    changing the count would otherwise read `pkgver` from the wrong directory,
    or from none, and the failure would arrive somewhere else.
    """
    root = Path(__file__).resolve().parents[2]
    if not (root / release.PKGVER_FILE).is_file():
        raise release.ReleaseError(
            f"{root} holds no {release.PKGVER_FILE}; this module has moved and the climb out of it has not"
        )
    return root


def read(repo: Path | None = None) -> Layout:
    root = repository_root() if repo is None else repo
    return Layout(
        repo=root,
        release=release.read_release(root),
        build_root=_directory("BUILD_ROOT", BUILD_ROOT_DEFAULT),
        why3_switch=_directory("WHY3_SWITCH", WHY3_SWITCH_DEFAULT),
        creusot_repo=os.environ.get("CREUSOT_REPO") or CREUSOT_REPO_DEFAULT,
    )
