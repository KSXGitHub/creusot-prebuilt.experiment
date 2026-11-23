"""Reading a commit message in each of the two shapes a hook is handed one.

A message file still carries what `git commit` put in it, and a stored message
has been through git's cleanup already. Reading a message file as though it were a
stored message rejected every release commit written in an editor, because the
template's comment lines read as a body.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lib import commit_message


class Parts(unittest.TestCase):
    def test_the_subject_is_the_first_non_blank_line(self) -> None:
        self.assertEqual(commit_message.from_stored("\n\nfix: a thing\n").subject, "fix: a thing")

    def test_a_message_of_only_blank_lines_has_no_subject(self) -> None:
        self.assertEqual(commit_message.from_stored("\n\n").subject, "")

    def test_the_first_paragraph_runs_to_the_first_blank_line(self) -> None:
        message = commit_message.from_stored("one\ntwo\n\nbody\n")
        self.assertEqual(message.first_paragraph, ("one", "two"))

    def test_the_body_is_what_follows_the_first_paragraph(self) -> None:
        message = commit_message.from_stored("subject\n\nbody one\n\nbody two\n")
        self.assertEqual(message.body, ("body one", "body two"))

    def test_trailing_blank_lines_are_not_a_body(self) -> None:
        self.assertEqual(commit_message.from_stored("0.15.0-0\n\n\n").body, ())


class FromFile(unittest.TestCase):
    def setUp(self) -> None:
        self.marker = commit_message.comment_char()

    def written(self, text: str) -> commit_message.CommitMessage:
        with tempfile.TemporaryDirectory() as scratch:
            path = Path(scratch) / "COMMIT_EDITMSG"
            path.write_text(text, encoding="utf-8")
            return commit_message.from_file(path)

    def test_drops_the_template_comment_lines(self) -> None:
        message = self.written(
            f"0.15.0-0\n\n"
            f"{self.marker} Please enter the commit message for your changes.\n"
            f"{self.marker} On branch master\n"
        )
        self.assertEqual(message.subject, "0.15.0-0")
        self.assertEqual(message.body, ())

    def test_stops_at_the_scissors_and_leaves_the_diff_out(self) -> None:
        message = self.written(
            f"0.15.0-0\n\n{self.marker} ------------------------ {commit_message.SCISSORS} ------------------------\n"
            "diff --git a/pkgrel b/pkgrel\n-0\n+1\n"
        )
        self.assertEqual(message.subject, "0.15.0-0")
        self.assertEqual(message.body, ())

    def test_keeps_a_body_the_author_wrote(self) -> None:
        message = self.written(f"fix: a thing\n\nwhy it was broken\n{self.marker} a comment\n")
        self.assertEqual(message.body, ("why it was broken",))

    def test_a_stored_message_keeps_a_line_that_starts_with_the_comment_char(self) -> None:
        stored = commit_message.from_stored(f"fix: a thing\n\n{self.marker}1 was wrong\n")
        self.assertEqual(stored.body, (f"{self.marker}1 was wrong",))
