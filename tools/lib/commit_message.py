"""Reading a git commit message, once, for every check that needs one.

A message reaches a hook in one of two shapes, and they are not parsed the
same way. A message *file* still carries whatever `git commit` put in it:
comment lines, and under `git commit -v` a scissors line with the diff after
it. A *stored* message has been through git's cleanup already, so a line
starting with the comment char is text the author meant to keep.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

DEFAULT_COMMENT_CHAR = "#"
SCISSORS = ">8"


def comment_char() -> str:
    """The effective `core.commentChar`.

    Honour it so that a user who has changed it does not have template comment
    lines read as part of the message. Anything other than a single character,
    which includes the unset case and `auto`, falls back to `#`.
    """
    result = subprocess.run(
        ["git", "config", "--get", "core.commentChar"],
        capture_output=True,
        text=True,
    )
    configured = result.stdout.strip() if result.returncode == 0 else ""
    return configured if len(configured) == 1 else DEFAULT_COMMENT_CHAR


@dataclass(frozen=True)
class CommitMessage:
    """The lines of a message that the author wrote."""

    lines: tuple[str, ...]

    @property
    def subject(self) -> str:
        """The first non-blank line, or the empty string if there is none."""
        for line in self.lines:
            if line.strip():
                return line
        return ""

    @property
    def first_paragraph(self) -> tuple[str, ...]:
        """Every line up to the first blank one, which is what git joins into the subject."""
        paragraph: list[str] = []
        for line in self.lines:
            if not line.strip():
                if paragraph:
                    break
                continue
            paragraph.append(line)
        return tuple(paragraph)

    @property
    def body(self) -> tuple[str, ...]:
        """The non-blank lines after the first paragraph."""
        seen_paragraph = False
        for index, line in enumerate(self.lines):
            if line.strip():
                seen_paragraph = True
            elif seen_paragraph:
                return tuple(rest for rest in self.lines[index + 1 :] if rest.strip())
        return ()

    @property
    def text(self) -> str:
        return "\n".join(self.lines)


def from_file(path: Path) -> CommitMessage:
    """Read a message file, dropping what `git commit` added to it."""
    marker = comment_char()
    lines: list[str] = []
    for line in path.read_text(encoding="utf-8").split("\n"):
        if line.startswith(marker):
            if SCISSORS in line:
                break
            continue
        lines.append(line)
    return CommitMessage(lines=tuple(lines))


def from_stored(message: str) -> CommitMessage:
    """Wrap a message git has already cleaned up, such as `git log --format=%B` output."""
    return CommitMessage(lines=tuple(message.split("\n")))
