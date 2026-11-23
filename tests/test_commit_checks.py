"""The commit-message checks, each of which reports a message or passes it."""

from __future__ import annotations

import os
import unittest
from unittest import mock

from lib import commit_checks
from lib.commit_message import from_stored

OPT_OUT = commit_checks.LONG_SUBJECT_OPT_OUT


class BareReferences(unittest.TestCase):
    def test_reports_each_bare_reference_once(self) -> None:
        report = commit_checks.bare_issue_references(from_stored("fix: see #1 #2 #1\n"))
        self.assertIsNotNone(report)
        assert report is not None
        self.assertIn("#1", report)
        self.assertIn("#2", report)

    def test_passes_a_qualified_reference(self) -> None:
        self.assertIsNone(commit_checks.bare_issue_references(from_stored("fix: see owner/repo#1\n")))

    def test_reads_the_body_as_well_as_the_subject(self) -> None:
        self.assertIsNotNone(commit_checks.bare_issue_references(from_stored("fix: a thing\n\ncloses #12\n")))


class BareMentions(unittest.TestCase):
    def test_reports_a_bare_handle(self) -> None:
        self.assertIsNotNone(commit_checks.bare_mentions(from_stored("fix: reported by @foo\n")))

    def test_passes_a_handle_in_backticks(self) -> None:
        self.assertIsNone(commit_checks.bare_mentions(from_stored("fix: reported by `@foo`\n")))


class MultilineSubject(unittest.TestCase):
    def test_reports_a_first_paragraph_of_two_lines(self) -> None:
        report = commit_checks.multiline_subject(from_stored("fix: a thing\nand another\n"))
        self.assertIsNotNone(report)
        assert report is not None
        self.assertIn("fix: a thing and another", report)

    def test_passes_a_subject_with_a_body_after_a_blank_line(self) -> None:
        self.assertIsNone(commit_checks.multiline_subject(from_stored("fix: a thing\n\nand another\n")))


class SubjectLength(unittest.TestCase):
    def test_passes_a_subject_at_the_limit(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            subject = "f" * commit_checks.SUBJECT_LIMIT
            self.assertIsNone(commit_checks.subject_length(from_stored(f"{subject}\n")))

    def test_reports_a_subject_one_character_past_it(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            subject = "f" * (commit_checks.SUBJECT_LIMIT + 1)
            report = commit_checks.subject_length(from_stored(f"{subject}\n"))
            self.assertIsNotNone(report)
            assert report is not None
            self.assertIn(str(commit_checks.SUBJECT_LIMIT + 1), report)

    def test_counts_characters_rather_than_bytes(self) -> None:
        # Each of these is two bytes in UTF-8, so a byte count would reject a
        # subject that fits and a character count accepts it.
        with mock.patch.dict(os.environ, {}, clear=True):
            subject = "é" * commit_checks.SUBJECT_LIMIT
            self.assertIsNone(commit_checks.subject_length(from_stored(f"{subject}\n")))

    def test_the_opt_out_skips_the_check(self) -> None:
        with mock.patch.dict(os.environ, {OPT_OUT: "true"}):
            subject = "f" * (commit_checks.SUBJECT_LIMIT + 1)
            self.assertIsNone(commit_checks.subject_length(from_stored(f"{subject}\n")))

    def test_false_and_empty_enforce_the_cap(self) -> None:
        subject = "f" * (commit_checks.SUBJECT_LIMIT + 1)
        for value in ("false", ""):
            with self.subTest(value), mock.patch.dict(os.environ, {OPT_OUT: value}):
                self.assertIsNotNone(commit_checks.subject_length(from_stored(f"{subject}\n")))

    def test_a_misspelt_opt_out_is_rejected_rather_than_ignored(self) -> None:
        with mock.patch.dict(os.environ, {OPT_OUT: "yes"}):
            report = commit_checks.subject_length(from_stored("fix: a thing\n"))
            self.assertIsNotNone(report)
            assert report is not None
            self.assertIn(OPT_OUT, report)
