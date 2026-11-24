"""The release identifier: what `pkgver` and `pkgrel` may hold, and the tag they form."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lib import release
from lib.release import ReleaseError


class Validate(unittest.TestCase):
    def test_accepts_a_triple_and_a_non_negative_revision(self) -> None:
        self.assertEqual(release.validate("0.15.0", "0"), release.Release(pkgver="0.15.0", pkgrel="0"))
        self.assertEqual(release.validate("1.2.3", "10").pkgrel, "10")

    def test_rejects_a_pkgver_that_is_not_a_triple(self) -> None:
        for pkgver in ("0.15", "0.15.0.1", "v0.15.0", "0.15.0-rc1", ""):
            with self.subTest(pkgver), self.assertRaises(ReleaseError):
                release.validate(pkgver, "0")

    def test_rejects_a_pkgrel_with_a_leading_zero_or_a_sign(self) -> None:
        for pkgrel in ("01", "-1", "+1", "1.0", ""):
            with self.subTest(pkgrel), self.assertRaises(ReleaseError):
                release.validate("0.15.0", pkgrel)


class Identifiers(unittest.TestCase):
    def test_the_tag_joins_the_pair(self) -> None:
        self.assertEqual(release.Release(pkgver="0.15.0", pkgrel="2").tag, "0.15.0-2")

    def test_the_upstream_tag_is_the_creusot_one(self) -> None:
        self.assertEqual(release.Release(pkgver="0.15.0", pkgrel="2").upstream_tag, "v0.15.0")


class ParseTag(unittest.TestCase):
    def test_splits_at_the_last_hyphen(self) -> None:
        self.assertEqual(release.parse_tag("0.15.0-2"), release.Release(pkgver="0.15.0", pkgrel="2"))

    def test_rejects_a_tag_with_no_revision(self) -> None:
        with self.assertRaises(ReleaseError):
            release.parse_tag("0.15.0")

    def test_rejects_a_tag_whose_halves_do_not_validate(self) -> None:
        for tag in ("v0.15.0-2", "0.15.0-02", "master-1"):
            with self.subTest(tag), self.assertRaises(ReleaseError):
                release.parse_tag(tag)


class StripRefPrefix(unittest.TestCase):
    def test_reduces_a_tag_ref_to_the_tag(self) -> None:
        self.assertEqual(release.strip_ref_prefix("refs/tags/0.15.0-1"), "0.15.0-1")

    def test_leaves_anything_else_alone(self) -> None:
        self.assertEqual(release.strip_ref_prefix("0.15.0-1"), "0.15.0-1")
        self.assertEqual(release.strip_ref_prefix("refs/heads/master"), "refs/heads/master")


class ReadRelease(unittest.TestCase):
    def test_reads_a_checkout(self) -> None:
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            (root / release.PKGVER_FILE).write_text("0.15.0\n", encoding="utf-8")
            (root / release.PKGREL_FILE).write_text("3\n", encoding="utf-8")
            self.assertEqual(release.read_release(root).tag, "0.15.0-3")

    def test_requires_one_line_ending_in_a_newline(self) -> None:
        for content in ("0.15.0", "0.15.0\n\n", " 0.15.0\n", "0.15.0\n0.15.1\n"):
            with self.subTest(content), tempfile.TemporaryDirectory() as scratch:
                root = Path(scratch)
                (root / release.PKGVER_FILE).write_text(content, encoding="utf-8")
                with self.assertRaises(ReleaseError):
                    release.read_file(root, release.PKGVER_FILE)

    def test_reports_a_file_that_is_not_there(self) -> None:
        with tempfile.TemporaryDirectory() as scratch, self.assertRaises(ReleaseError):
            release.read_file(Path(scratch), release.PKGVER_FILE)
