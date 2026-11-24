"""Finding what GitHub would autolink in a commit message.

The scanners here replace two regexes that a test showed to be wrong.
`(^|[^0-9A-Za-z_])#[0-9]+([^0-9A-Za-z_]|$)` consumes the character after a
reference, so in `#1 #2 #3` the space after `#1` is eaten and `#2` never matches
its leading boundary: it reported the first and the third. `` `[^`]*` `` pairs
backticks greedily and has no notion of a span opened by two of them, so
```` ``@foo```` ```` stripped to a bare `@foo` and was reported as a mention it
is not.

A boundary here is GitHub's: `#` or `@` opens an autolink only when the
character before it is not an ASCII word character. That is what keeps
`owner/repo#123` and `user@example.com` from reading as bare.
"""

from __future__ import annotations

from .take import Taken, take_literal, take_run, take_while

WORD = frozenset("0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_")
DIGITS = frozenset("0123456789")
HANDLE_START = frozenset("0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")
HANDLE_REST = HANDLE_START | frozenset("-")


def take_code_span(text: str) -> Taken:
    """Take a code span, opening backtick run and closing run included.

    CommonMark closes a run of N backticks with the next run of exactly N, so a
    span opened by two is closed by two and may hold single ones. A run that
    never closes opens nothing and is ordinary text.
    """
    opening = take_run(text, "`")
    if opening is None:
        return None
    ticks, rest = opening
    inside = ""
    while rest:
        run = take_run(rest, "`")
        if run is None:
            inside, rest = inside + rest[0], rest[1:]
            continue
        closing, after = run
        if len(closing) == len(ticks):
            return ticks + inside + closing, after
        inside, rest = inside + closing, after
    return None


def take_handle(text: str) -> Taken:
    """Take a mention's handle, without the `@`.

    A handle is a letter or digit then any of letter, digit and hyphen, and may
    carry one `/`-separated second part, which covers `@org/team` and
    `@scope/pkg`.
    """
    if not text or text[0] not in HANDLE_START:
        return None
    first = take_while(text, HANDLE_REST)
    if first is None:
        return None
    name, rest = first
    slash = take_literal(rest, "/")
    if slash is not None:
        _, after_slash = slash
        second = take_handle(after_slash)
        if second is not None:
            team, remainder = second
            return f"{name}/{team}", remainder
    return name, rest


def bare_issue_references(text: str) -> list[str]:
    """Every `#NNN` that GitHub would resolve against the repository it is read in.

    A word character after the digits means this is not a reference at all,
    which is what keeps `#123abc` and the fragments `#L123` and
    `#issuecomment-1` out. Code spans are not skipped: GitHub autolinks a
    commit message as plain text.
    """
    found: list[str] = []
    previous = ""
    rest = text
    while rest:
        if rest[0] == "#" and previous not in WORD:
            digits = take_while(rest[1:], DIGITS)
            if digits is not None:
                number, after = digits
                if not after or after[0] not in WORD:
                    found.append(f"#{number}")
                    previous, rest = number[-1], after
                    continue
        previous, rest = rest[0], rest[1:]
    return found


def bare_mentions(text: str) -> list[str]:
    """Every `@handle` outside a code span that GitHub would turn into a mention.

    A span is stepped over whole, so a handle written inside one is never
    examined. That is the escape this repository asks for in a commit message.
    """
    found: list[str] = []
    previous = ""
    rest = text
    while rest:
        span = take_code_span(rest)
        if span is not None:
            consumed, rest = span
            previous = consumed[-1]
            continue
        if rest[0] == "@" and previous not in WORD:
            handle = take_handle(rest[1:])
            if handle is not None:
                name, after = handle
                found.append(f"@{name}")
                previous, rest = name[-1], after
                continue
        previous, rest = rest[0], rest[1:]
    return found
