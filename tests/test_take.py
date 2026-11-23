"""The parser primitives every hand-written scanner here is built from."""

from __future__ import annotations

import unittest

from lib.take import (
    drop_while,
    take_balanced,
    take_literal,
    take_quoted,
    take_run,
    take_until,
    take_while,
)

DIGITS = frozenset("0123456789")


class TakeWhile(unittest.TestCase):
    def test_takes_the_longest_run_and_leaves_the_rest(self) -> None:
        self.assertEqual(take_while("123abc", DIGITS), ("123", "abc"))

    def test_takes_the_whole_string(self) -> None:
        self.assertEqual(take_while("123", DIGITS), ("123", ""))

    def test_declines_rather_than_taking_nothing(self) -> None:
        self.assertIsNone(take_while("abc", DIGITS))
        self.assertIsNone(take_while("", DIGITS))


class TakeLiteral(unittest.TestCase):
    def test_takes_the_prefix(self) -> None:
        self.assertEqual(take_literal("host: x86_64", "host: "), ("host: ", "x86_64"))

    def test_declines_a_string_that_starts_otherwise(self) -> None:
        self.assertIsNone(take_literal("target: x86_64", "host: "))

    def test_an_exhausted_string_leaves_an_empty_remainder(self) -> None:
        self.assertEqual(take_literal("abc", "abc"), ("abc", ""))


class TakeRun(unittest.TestCase):
    def test_takes_repetitions_of_the_one_character(self) -> None:
        self.assertEqual(take_run("```code", "`"), ("```", "code"))

    def test_declines_when_the_character_is_not_first(self) -> None:
        self.assertIsNone(take_run("code```", "`"))


class DropWhile(unittest.TestCase):
    def test_drops_the_leading_run(self) -> None:
        self.assertEqual(drop_while("   value", frozenset(" ")), "value")

    def test_succeeds_with_nothing_to_drop(self) -> None:
        self.assertEqual(drop_while("value", frozenset(" ")), "value")
        self.assertEqual(drop_while("", frozenset(" ")), "")


class TakeUntil(unittest.TestCase):
    def test_leaves_the_marker_in_the_remainder(self) -> None:
        self.assertEqual(take_until("name: value", ":"), ("name", ": value"))

    def test_a_marker_at_the_start_takes_nothing_and_still_succeeds(self) -> None:
        self.assertEqual(take_until(":value", ":"), ("", ":value"))

    def test_declines_when_the_marker_is_absent(self) -> None:
        self.assertIsNone(take_until("name value", ":"))


class TakeQuoted(unittest.TestCase):
    def test_returns_the_contents_without_the_quotes(self) -> None:
        self.assertEqual(take_quoted('"why3.git-05bf4ddf" rest'), ("why3.git-05bf4ddf", " rest"))

    def test_an_empty_quoted_run_is_taken(self) -> None:
        self.assertEqual(take_quoted('""rest'), ("", "rest"))

    def test_declines_an_unterminated_run(self) -> None:
        self.assertIsNone(take_quoted('"why3'))

    def test_declines_a_string_that_does_not_open_with_the_quote(self) -> None:
        self.assertIsNone(take_quoted('why3"'))


class TakeBalanced(unittest.TestCase):
    def test_returns_the_contents_without_the_outer_brackets(self) -> None:
        self.assertEqual(take_balanced("[ a b ] rest", "[", "]"), (" a b ", " rest"))

    def test_ends_at_the_bracket_that_closes_the_first_one(self) -> None:
        self.assertEqual(take_balanced("[ [ a ] [ b ] ] rest", "[", "]"), (" [ a ] [ b ] ", " rest"))

    def test_declines_when_nothing_closes_the_first_bracket(self) -> None:
        self.assertIsNone(take_balanced("[ [ a ]", "[", "]"))

    def test_declines_a_string_that_does_not_open_with_the_bracket(self) -> None:
        self.assertIsNone(take_balanced(" [ a ]", "[", "]"))
