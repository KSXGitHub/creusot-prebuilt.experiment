"""Hashing a file, and reducing a set of files to one digest."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from pathlib import Path

BLOCK = 1 << 20


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(BLOCK), b""):
            digest.update(block)
    return digest.hexdigest()


def digest_of(paths: Iterable[Path]) -> str:
    """One digest over several files, for naming a directory after their content.

    The paths are sorted first, so the digest depends on what the files hold
    and not on the order they were offered in.
    """
    combined = hashlib.sha256()
    for path in sorted(paths):
        combined.update(sha256_of(path).encode("ascii"))
    return combined.hexdigest()
