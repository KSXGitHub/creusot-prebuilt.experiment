"""Reading the Why3 pins out of Creusot's `creusot-deps.opam`.

opam's file format has no reader in the standard library, so this is a parse of
the one construct needed: the `pin-depends:` list.

The file names each pin twice. Under `depends:` it reads
`"why3" {= "git-05bf4ddf"}`, where the package and the version are separate
tokens; under `pin-depends:` it reads `[ "why3.git-05bf4ddf" "git+https://..." ]`,
where one token carries both. The second is the one read here, and reading it
from inside the list is what keeps the comment above it and the URLs beside it
out of the answer. A regex over the whole file was right for this file only by
accident.
"""

from __future__ import annotations

from pathlib import Path

from .take import drop_while, take_balanced, take_literal, take_quoted, take_until

FILE_NAME = "creusot-deps.opam"
PIN_DEPENDS = "pin-depends:"
WHITESPACE = frozenset(" \t\r\n")
WANTED = frozenset({"why3", "why3find"})


class OpamError(Exception):
    """A `creusot-deps.opam` that does not hold the pins the build needs."""


def take_pin_depends(text: str) -> str | None:
    """The contents of the `pin-depends:` list, or None when the file has none."""
    marker = take_until(text, PIN_DEPENDS)
    if marker is None:
        return None
    _, at_marker = marker
    consumed = take_literal(at_marker, PIN_DEPENDS)
    if consumed is None:
        return None
    _, rest = consumed
    bracketed = take_balanced(drop_while(rest, WHITESPACE), "[", "]")
    return None if bracketed is None else bracketed[0]


def pin_entries(body: str) -> list[str]:
    """Each `[ ... ]` entry of a `pin-depends:` list, without its brackets."""
    entries: list[str] = []
    rest = drop_while(body, WHITESPACE)
    while rest:
        bracketed = take_balanced(rest, "[", "]")
        if bracketed is None:
            break
        entry, rest = bracketed
        entries.append(entry)
        rest = drop_while(rest, WHITESPACE)
    return entries


def read_pins(source: Path) -> dict[str, str]:
    """The versions `creusot-deps.opam` pins Why3 and why3find to."""
    path = source / FILE_NAME
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        raise OpamError(f"cannot read {path}: {error}") from error

    body = take_pin_depends(text)
    if body is None:
        raise OpamError(f"{FILE_NAME} has no {PIN_DEPENDS} list")

    pins: dict[str, str] = {}
    for entry in pin_entries(body):
        quoted = take_quoted(drop_while(entry, WHITESPACE))
        if quoted is None:
            continue
        token, _ = quoted
        package, separator, version = token.partition(".")
        if separator and package in WANTED:
            pins[package] = version
    missing = sorted(WANTED - pins.keys())
    if missing:
        raise OpamError(f"{FILE_NAME} pins no version for {', '.join(missing)}")
    return pins
