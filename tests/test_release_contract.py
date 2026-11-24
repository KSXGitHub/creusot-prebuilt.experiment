"""Whether a tag, the commit message it points at, and `pkgver`/`pkgrel` agree."""

from __future__ import annotations

import io
import unittest
from contextlib import redirect_stderr
from pathlib import Path

from lib import layout, release_contract
from lib.commit_message import from_stored

ZERO_SHA = "0" * 40
TAG_WRITE = [f"{ZERO_SHA} ccc333 refs/tags/0.15.0-0"]
"""One line of what git feeds `reference-transaction` as a release tag is written."""


class MessageProblems(unittest.TestCase):
    def test_a_message_of_the_tag_alone_holds(self) -> None:
        self.assertEqual(release_contract.message_problems(from_stored("0.15.0-0\n"), "0.15.0-0"), [])

    def test_reports_a_subject_that_is_not_the_tag(self) -> None:
        problems = release_contract.message_problems(from_stored("0.15.0-1\n"), "0.15.0-0")
        self.assertEqual(len(problems), 1)
        self.assertIn("0.15.0-1", problems[0])
        self.assertIn("0.15.0-0", problems[0])

    def test_reports_a_body(self) -> None:
        problems = release_contract.message_problems(from_stored("0.15.0-0\n\nrebuilt for a fix\n"), "0.15.0-0")
        self.assertEqual(len(problems), 1)
        self.assertIn("rebuilt for a fix", problems[0])

    def test_trailing_blank_lines_are_not_a_body(self) -> None:
        self.assertEqual(release_contract.message_problems(from_stored("0.15.0-0\n\n\n"), "0.15.0-0"), [])


class FilesProblems(unittest.TestCase):
    def test_a_pair_that_forms_the_tag_holds(self) -> None:
        self.assertEqual(release_contract.files_problems("0.15.0\n", "0\n", "0.15.0-0"), [])

    def test_reports_a_pair_that_forms_another_tag(self) -> None:
        problems = release_contract.files_problems("0.15.0\n", "1\n", "0.15.0-0")
        self.assertEqual(len(problems), 1)
        self.assertIn("0.15.0-1", problems[0])

    def test_reports_a_pair_that_does_not_validate(self) -> None:
        self.assertEqual(len(release_contract.files_problems("v0.15.0\n", "0\n", "0.15.0-0")), 1)


class ParsesAsTag(unittest.TestCase):
    def test_recognises_a_release_tag(self) -> None:
        self.assertTrue(release_contract.parses_as_tag("0.15.0-0"))

    def test_rejects_anything_else(self) -> None:
        for candidate in ("master", "v0.15.0", "0.15.0", "nightly-2026-08-03"):
            with self.subTest(candidate):
                self.assertFalse(release_contract.parses_as_tag(candidate))


class Report(unittest.TestCase):
    def test_holding_reports_nothing_and_succeeds(self) -> None:
        narration = io.StringIO()
        with redirect_stderr(narration):
            self.assertEqual(release_contract.report("0.15.0-0", []), 0)
        self.assertIn("0.15.0-0", narration.getvalue())

    def test_a_problem_fails_and_is_named(self) -> None:
        narration = io.StringIO()
        with redirect_stderr(narration):
            self.assertEqual(release_contract.report("0.15.0-0", ["the subject is wrong"]), 1)
        self.assertIn("the subject is wrong", narration.getvalue())


class Updates(unittest.TestCase):
    """The two line formats, which put the new sha in different places.

    Reading one with the other's positions would check a ref name as though it
    were an object, or an old value as though it were the new one, and the
    report would be about something nobody asked about.
    """

    def test_a_push_line_names_the_local_ref_then_its_sha(self) -> None:
        line = "refs/tags/0.15.0-1 aaa111 refs/tags/0.15.0-1 bbb222"
        self.assertEqual(list(release_contract.pushed_updates([line])), [("refs/tags/0.15.0-1", "aaa111")])

    def test_a_transaction_line_names_the_values_then_the_ref(self) -> None:
        line = f"{ZERO_SHA} ccc333 refs/tags/0.15.0-1"
        self.assertEqual(list(release_contract.transaction_updates([line])), [("refs/tags/0.15.0-1", "ccc333")])

    def test_a_line_too_short_to_read_is_passed_over(self) -> None:
        self.assertEqual(list(release_contract.pushed_updates(["", "refs/tags/0.15.0-1"])), [])
        self.assertEqual(list(release_contract.transaction_updates(["", f"{ZERO_SHA} ccc333"])), [])


class HookFilter(unittest.TestCase):
    """The one fact `.githooks/reference-transaction` spells for itself.

    The hook looks for a tag among the refs before starting anything, because
    the processes behind it cost about 200ms that every commit would otherwise
    pay to learn it touched no tag. The test is for the presence of a tag rather
    than the shape of one, so the hook decides nothing and extracts nothing, but
    it does spell the prefix `check_refs` reads, and the two drifting apart would
    leave the hook passing over the tags it exists to catch.
    """

    def test_the_hook_looks_for_the_prefix_check_refs_reads(self) -> None:
        hook = (layout.repository_root() / ".githooks" / "reference-transaction").read_text(encoding="utf-8")
        # The comments naming the prefix are dropped, because the first draft of
        # this test read the whole file and passed with the filter broken.
        code = [line for line in hook.splitlines() if not line.lstrip().startswith("#")]
        self.assertIn(release_contract.TAG_PREFIX, "\n".join(code))


class CheckPushedRefs(unittest.TestCase):
    """The filtering, which decides what is looked at before git is asked anything."""

    def test_a_push_with_no_release_tag_is_nothing_to_check(self) -> None:
        lines = [
            "refs/heads/master abc123 refs/heads/master def456",
            "refs/tags/nightly abc123 refs/tags/nightly def456",
            f"refs/tags/0.15.0-0 {ZERO_SHA} refs/tags/0.15.0-0 def456",
            "",
            "refs/tags/0.15.0-0",
        ]
        self.assertEqual(release_contract.check_pushed_refs(Path("."), lines), 0)


class CheckCreatedRefs(unittest.TestCase):
    """What a ref transaction has to be before git is asked about it.

    This hook runs for every ref update in the repository, so what it declines
    to look at matters as much as what it refuses.
    """

    def test_only_the_prepared_state_can_still_stop_anything(self) -> None:
        for state in ("committed", "aborted", ""):
            with self.subTest(state):
                self.assertEqual(release_contract.check_created_refs(Path("."), state, TAG_WRITE), 0)

    def test_a_transaction_touching_no_tag_is_nothing_to_check(self) -> None:
        lines = [
            f"{ZERO_SHA} aaa111 refs/heads/side",
            "aaa111 bbb222 HEAD",
            f"{ZERO_SHA} ccc333 refs/tags/nightly-2026-08-03",
            f"ccc333 {ZERO_SHA} refs/tags/0.15.0-0",
            "",
        ]
        self.assertEqual(release_contract.check_created_refs(Path("."), "prepared", lines), 0)
