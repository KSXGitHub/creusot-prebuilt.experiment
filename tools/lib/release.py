"""The release identifier: the `pkgver` and `pkgrel` files, and the tag they form.

A release is identified by the upstream Creusot version (`pkgver`) together with
a build revision (`pkgrel`), so that a packaging fix can be shipped for a Creusot
version that has already been released. The tag `0.15.0-2` is the second build of
Creusot 0.15.0.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

PKGVER_FILE = "pkgver"
PKGREL_FILE = "pkgrel"

# Creusot tags releases as `vX.Y.Z`, so `pkgver` is the same triple without the
# `v`. Restricting the shape keeps the hyphen in a tag unambiguous: everything
# before the last one is the pkgver.
PKGVER_PATTERN = re.compile(r"\A[0-9]+\.[0-9]+\.[0-9]+\Z")
PKGREL_PATTERN = re.compile(r"\A(0|[1-9][0-9]*)\Z")


class ReleaseError(Exception):
    """A `pkgver` / `pkgrel` pair, or a tag, that does not hold the required shape."""


@dataclass(frozen=True)
class Release:
    """The pair that identifies one release."""

    pkgver: str
    pkgrel: str

    @property
    def tag(self) -> str:
        """The git tag, the release name, and the version part of every asset name."""
        return f"{self.pkgver}-{self.pkgrel}"

    @property
    def upstream_tag(self) -> str:
        """The tag of the Creusot source this release is built from."""
        return f"v{self.pkgver}"


def validate(pkgver: str, pkgrel: str) -> Release:
    """Check the two fields and pair them up."""
    if not PKGVER_PATTERN.fullmatch(pkgver):
        raise ReleaseError(f"pkgver must be X.Y.Z; got {pkgver!r}")
    if not PKGREL_PATTERN.fullmatch(pkgrel):
        raise ReleaseError(f"pkgrel must be a non-negative integer without leading zeroes; got {pkgrel!r}")
    return Release(pkgver=pkgver, pkgrel=pkgrel)


def read_file(root: Path, name: str) -> str:
    try:
        text = (root / name).read_text(encoding="utf-8")
    except OSError as error:
        raise ReleaseError(f"cannot read {name}: {error}") from error
    stripped = text.strip()
    if text != stripped + "\n" or "\n" in stripped:
        raise ReleaseError(f"{name} must hold one line and end with a newline")
    return stripped


def read_release(root: Path) -> Release:
    """Read `pkgver` and `pkgrel` from a checkout."""
    return validate(read_file(root, PKGVER_FILE), read_file(root, PKGREL_FILE))


def parse_tag(tag: str) -> Release:
    """Split a tag into the pair that produced it."""
    pkgver, separator, pkgrel = tag.rpartition("-")
    if not separator:
        raise ReleaseError(f"a release tag is <pkgver>-<pkgrel>; got {tag!r}")
    return validate(pkgver, pkgrel)


def strip_ref_prefix(ref: str) -> str:
    """Reduce `refs/tags/0.15.0-1` to `0.15.0-1`, and leave a bare tag alone."""
    prefix = "refs/tags/"
    return ref[len(prefix) :] if ref.startswith(prefix) else ref
