"""The commit-message checks, each returning the report it would print.

These were four shell scripts. The scans they did with `grep -E` and `awk` are
now in `github_text` and `commit_message`, and the subject length is counted
with `len`, which replaces subtracting UTF-8 continuation bytes from a byte
count under `LC_ALL=C`.
"""

from __future__ import annotations

import os

import github_text
from commit_message import CommitMessage

SUBJECT_LIMIT = 72
LONG_SUBJECT_OPT_OUT = "CREUSOT_PREBUILT_ALLOW_LONG_SUBJECT"
REPOSITORY = "KSXGitHub/creusot-prebuilt.experiment"


def _listed(items: list[str]) -> str:
    return "\n".join(f"    {item}" for item in items)


def bare_issue_references(message: CommitMessage) -> str | None:
    """Reject a `#NNN` that GitHub would resolve against this repository."""
    found = github_text.bare_issue_references(message.text)
    if not found:
        return None
    return f"""✖ Commit message rejected: it contains a bare "#NNN" reference.

{_listed(sorted(set(found)))}

A bare "#123" is ambiguous and a common way to mis-reference an issue:

  • Used to enumerate list items ("#1", "#2", "#3"), it instead reads as
    issue or pull request 1, 2, 3. Number the items another way, such as
    "item 1", "1.", or "(1)".

  • Used for a real issue or pull request, GitHub resolves a bare "#123"
    against THIS repository, so a number meant for another repository
    silently links to the wrong issue here.

Use an unambiguous form instead:

  • Same repo:    {REPOSITORY}#123
  • Another repo: owner/repo#123
  • Absolute URL: https://github.com/owner/repo/issues/123

Qualified ("owner/repo#123") and URL forms are always accepted, so it is
safe to qualify even same-repository references."""


def bare_mentions(message: CommitMessage) -> str | None:
    """Reject an `@handle` that GitHub would turn into a mention."""
    found = github_text.bare_mentions(message.text)
    if not found:
        return None
    return f"""✖ Commit message rejected: it contains a bare "@handle" mention.

{_listed(sorted(set(found)))}

Outside backticks, GitHub autolinks "@foo" as a user or team mention:

  • If you meant it as code (a CLI flag, a path like @scope/pkg, a version
    like pkg@1.2.3), GitHub still reads it as a mention.

  • If you meant a real account, every commit, comment, and rebase that
    carries the message pings that person again.

Wrap the handle in backticks so it renders as code and never pings:

  • `@foo`  instead of  @foo

A genuinely intended mention belongs in the pull request or issue body,
not in a commit message."""


def multiline_subject(message: CommitMessage) -> str | None:
    """Reject a first paragraph of more than one line.

    Git takes every line up to the first blank one and joins them with spaces,
    so each of them lands in the title rather than in the body.
    """
    paragraph = message.first_paragraph
    if len(paragraph) <= 1:
        return None
    joined = " ".join(line.rstrip() for line in paragraph)
    return f"""✖ Commit message rejected: the subject spans more than one line.

{_listed(list(paragraph))}

Git does not read the subject as the first line: it takes every line up to
the first blank one and joins them with spaces. So every line above lands
in the title rather than the body, and the subject reads:

    {joined}

Put a blank line after the subject so the rest becomes the body, or fold
the extra words into the subject itself. A first paragraph of more than
one line has no legitimate form, so this check has no opt-out."""


def subject_length(message: CommitMessage) -> str | None:
    """Reject a subject past the conventional 72-character cap.

    The count is of characters rather than bytes, because that is what GitHub
    truncates by and what an accented or non-Latin subject should be judged on.
    """
    opt_out = os.environ.get(LONG_SUBJECT_OPT_OUT, "")
    if opt_out not in {"true", "false", ""}:
        return f"✖ {LONG_SUBJECT_OPT_OUT} must be 'true', 'false', empty, or unset; got: {opt_out}"
    if opt_out == "true":
        return None

    subject = message.subject
    length = len(subject)
    if length <= SUBJECT_LIMIT:
        return None
    return f"""✖ Commit message rejected: the subject line is too long.

    {subject}

The subject is {length} characters; the limit is {SUBJECT_LIMIT}.

GitHub truncates a subject past {SUBJECT_LIMIT} characters in its web UI: it cuts the
line, appends a "…", and folds the overflow into the body behind another
"…", so the commit reads as a mangled title/body split.

Shorten the subject to {SUBJECT_LIMIT} characters or fewer (the conventional ideal is
50). Move any detail that does not fit into the commit body: a blank line
after the subject, then the rest.

If a longer subject is genuinely warranted, re-run the commit with
{LONG_SUBJECT_OPT_OUT}=true to skip this check. The other
commit-message checks still apply."""


CHECKS = (bare_issue_references, bare_mentions, multiline_subject, subject_length)
"""Run in this order, so that the subject is known to be one line before its
length is measured."""
