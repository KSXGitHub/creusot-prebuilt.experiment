"""What GitHub would autolink in a commit message.

The faults that retired the regexes these scanners replaced are here: every
reference in `#1 #2 #3` has to be reported, and a handle inside a code span
opened by two backticks has to be reported as nothing at all.
"""

from __future__ import annotations

import unittest

from lib.github_text import bare_issue_references, bare_mentions, take_code_span, take_handle


class TakeCodeSpan(unittest.TestCase):
    def test_takes_a_span_with_its_backticks(self) -> None:
        self.assertEqual(take_code_span("`code` rest"), ("`code`", " rest"))

    def test_a_span_opened_by_two_backticks_may_hold_one(self) -> None:
        self.assertEqual(take_code_span("``a `b` c`` rest"), ("``a `b` c``", " rest"))

    def test_a_run_is_closed_by_a_run_of_the_same_length(self) -> None:
        self.assertEqual(take_code_span("``@foo`` rest"), ("``@foo``", " rest"))

    def test_declines_a_run_that_never_closes(self) -> None:
        self.assertIsNone(take_code_span("`@foo"))

    def test_declines_text_that_does_not_start_with_a_backtick(self) -> None:
        self.assertIsNone(take_code_span("code`"))


class TakeHandle(unittest.TestCase):
    def test_takes_letters_digits_and_hyphens(self) -> None:
        self.assertEqual(take_handle("foo-bar9 rest"), ("foo-bar9", " rest"))

    def test_takes_a_slash_separated_second_part(self) -> None:
        self.assertEqual(take_handle("org/team rest"), ("org/team", " rest"))

    def test_a_trailing_slash_is_left_in_the_remainder(self) -> None:
        self.assertEqual(take_handle("org/ rest"), ("org", "/ rest"))

    def test_declines_a_handle_that_starts_with_a_hyphen(self) -> None:
        self.assertIsNone(take_handle("-foo"))

    def test_declines_an_empty_string(self) -> None:
        self.assertIsNone(take_handle(""))


class BareIssueReferences(unittest.TestCase):
    def test_reports_every_reference_in_a_run_of_them(self) -> None:
        self.assertEqual(bare_issue_references("#1 #2 #3"), ["#1", "#2", "#3"])

    def test_reports_one_in_parentheses_and_after_a_slash(self) -> None:
        self.assertEqual(bare_issue_references("fix (#123)"), ["#123"])
        self.assertEqual(bare_issue_references("see path/#123"), ["#123"])

    def test_a_qualified_reference_is_not_bare(self) -> None:
        self.assertEqual(bare_issue_references("KSXGitHub/perfectionist#123"), [])
        self.assertEqual(bare_issue_references("owner/repo#123 and C#123"), [])

    def test_a_word_character_after_the_digits_is_not_a_reference(self) -> None:
        self.assertEqual(bare_issue_references("#123abc"), [])
        self.assertEqual(bare_issue_references("file.rs#L123"), [])
        self.assertEqual(bare_issue_references("#issuecomment-1"), [])

    def test_a_code_span_does_not_hide_one(self) -> None:
        self.assertEqual(bare_issue_references("`#123`"), ["#123"])


class BareMentions(unittest.TestCase):
    def test_reports_a_handle(self) -> None:
        self.assertEqual(bare_mentions("thanks @foo"), ["@foo"])

    def test_a_span_of_one_backtick_hides_a_handle(self) -> None:
        self.assertEqual(bare_mentions("thanks `@foo`"), [])

    def test_a_span_of_two_backticks_hides_a_handle(self) -> None:
        self.assertEqual(bare_mentions("thanks ``@foo``"), [])

    def test_an_unclosed_backtick_hides_nothing(self) -> None:
        self.assertEqual(bare_mentions("thanks `@foo"), ["@foo"])

    def test_an_address_is_not_a_mention(self) -> None:
        self.assertEqual(bare_mentions("user@example.com"), [])
        self.assertEqual(bare_mentions("pkg@1.2.3"), [])

    def test_reports_a_team_and_a_scope(self) -> None:
        self.assertEqual(bare_mentions("ping @org/team"), ["@org/team"])
        self.assertEqual(bare_mentions("needs @scope/pkg"), ["@scope/pkg"])
