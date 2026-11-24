"""The release body, and the one thing about it no other check would notice.

GitHub renders a release body the way it renders a comment, so a newline inside
a paragraph reaches the page as a `<br>`. Wrapping the prose in the source is
what puts one there, and nothing about the markdown looks wrong until it is
rendered, which is after the release exists.
"""

from __future__ import annotations

import unittest
from typing import Any

from lib import inventory

FENCE = "```"
OWN_LINE = ("|", "-", "#", ">")
"""What markdown already gives a line of its own: a table row, a bullet, a
heading, a blockquote. GitHub joins neither of these to the line before it."""

METADATA: dict[str, Any] = {
    "pkgver": "0.15.0",
    "pkgrel": "1",
    "tag": "0.15.0-1",
    "target": "x86_64-unknown-linux-gnu",
    "creusot_tag": "v0.15.0",
    "creusot_commit": "fd4d85b2c237ef93147e99f6a0c04acfc89a6a17",
    "rust_channel": "nightly-2026-08-03",
    "opam_pins": {"why3": "git-05bf4ddf", "why3find": "git-89dd8721"},
    "source_date_epoch": 1794307262,
    "why3_prefix": "/opt/creusot-why3/_opam",
    "repository": "owner/name",
    "assets": [
        {
            "name": "cargo-creusot",
            "file": "cargo-creusot-0.15.0-1-x86_64-unknown-linux-gnu.tar.gz",
            "prefix": "creusot-data-home",
            "arch": "target",
            "summary": "The subcommand.",
            "size": 873_000,
            "sha256": "0" * 64,
        },
        {
            "name": "why3",
            "file": "why3-0.15.0-1-x86_64-unknown-linux-gnu.tar.gz",
            "prefix": "why3-prefix",
            "arch": "target",
            "summary": "Why3 itself.",
            "size": 10_900_000,
            "sha256": "1" * 64,
        },
    ],
}


def hard_line_breaks(body: str) -> list[str]:
    """Every line GitHub would join to the line above it with a `<br>`."""
    found: list[str] = []
    inside_fence = False
    after_prose = False
    for line in body.splitlines():
        if line.startswith(FENCE):
            inside_fence = not inside_fence
            after_prose = False
            continue
        is_prose = not inside_fence and bool(line.strip()) and not line.startswith(OWN_LINE)
        if is_prose and after_prose:
            found.append(line)
        after_prose = is_prose
    return found


class Paragraph(unittest.TestCase):
    def test_joins_its_fragments_with_one_space(self) -> None:
        self.assertEqual(inventory.paragraph("one", "two", "three"), "one two three")

    def test_one_fragment_is_the_paragraph(self) -> None:
        self.assertEqual(inventory.paragraph("alone"), "alone")


class HumanSize(unittest.TestCase):
    def test_counts_a_small_file_in_kilobytes(self) -> None:
        self.assertEqual(inventory.human_size(873_000), "873 kB")

    def test_counts_a_large_file_in_megabytes(self) -> None:
        self.assertEqual(inventory.human_size(10_900_000), "10.9 MB")

    def test_a_megabyte_is_where_the_unit_changes(self) -> None:
        self.assertEqual(inventory.human_size(1_000_000), "1.0 MB")


class Render(unittest.TestCase):
    def test_no_paragraph_carries_a_hard_line_break(self) -> None:
        broken = hard_line_breaks(inventory.render(METADATA))
        self.assertEqual(broken, [], f"these lines would render behind a <br>: {broken}")

    def test_the_table_holds_one_row_per_asset(self) -> None:
        rows = [line for line in inventory.render(METADATA).splitlines() if line.startswith("| `")]
        self.assertEqual(len(rows), len(METADATA["assets"]))

    def test_a_row_names_the_directory_its_asset_unpacks_at(self) -> None:
        body = inventory.render(METADATA)
        self.assertIn("| the Creusot data directory |", body)
        self.assertIn(f"| `{METADATA['why3_prefix']}` |", body)

    def test_the_body_ends_with_one_newline(self) -> None:
        body = inventory.render(METADATA)
        self.assertTrue(body.endswith("```\n"))
        self.assertFalse(body.endswith("\n\n"))
