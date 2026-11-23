"""The pieces a hand-written parser here is built from.

A `take_*` function is offered a string and either consumes a prefix of it or
declines. On success it returns the prefix it took and the remainder; on failure
it returns `None` and the caller tries something else. A parse that owns its
whole input finishes by requiring the remainder to be empty.

This is the shape every non-trivial scanner in this repository uses, in place of
a regex. The reason is not taste: the regexes these replaced were each wrong in
a way only a test revealed, and the failures were in the parts a regex hides,
which are boundaries and repetition.
"""

from __future__ import annotations

from collections.abc import Container

Taken = tuple[str, str] | None
"""What a `take_*` returns: the prefix it consumed and the remainder, or nothing."""


def take_while(text: str, allowed: Container[str]) -> Taken:
    """Take the longest non-empty prefix whose every character is in `allowed`."""
    index = 0
    while index < len(text) and text[index] in allowed:
        index += 1
    return (text[:index], text[index:]) if index else None


def take_literal(text: str, prefix: str) -> Taken:
    """Take `prefix` if `text` starts with it."""
    return (prefix, text[len(prefix) :]) if text.startswith(prefix) else None


def take_run(text: str, character: str) -> Taken:
    """Take the longest non-empty prefix of repetitions of one character."""
    return take_while(text, {character})


def drop_while(text: str, allowed: Container[str]) -> str:
    """The remainder after any leading `allowed` characters. Always succeeds."""
    taken = take_while(text, allowed)
    return taken[1] if taken is not None else text


def take_until(text: str, marker: str) -> Taken:
    """Take everything before the first `marker`, which is left in the remainder."""
    position = text.find(marker)
    return (text[:position], text[position:]) if position >= 0 else None


def take_quoted(text: str, quote: str = '"') -> Taken:
    """Take a quoted run, returning its contents without the quotes.

    There is no escape sequence to honour: the files parsed with this hold no
    quoted string that contains a quote.
    """
    opening = take_literal(text, quote)
    if opening is None:
        return None
    _, rest = opening
    closing = rest.find(quote)
    return (rest[:closing], rest[closing + 1 :]) if closing >= 0 else None


def take_balanced(text: str, opening: str, closing: str) -> Taken:
    """Take a bracketed run, returning its contents without the outer brackets.

    Nesting counts, so the run ends at the bracket that closes the first one
    rather than at the first closing bracket.
    """
    start = take_literal(text, opening)
    if start is None:
        return None
    _, rest = start
    depth = 1
    for index, character in enumerate(rest):
        if character == opening:
            depth += 1
        elif character == closing:
            depth -= 1
            if depth == 0:
                return rest[:index], rest[index + 1 :]
    return None
