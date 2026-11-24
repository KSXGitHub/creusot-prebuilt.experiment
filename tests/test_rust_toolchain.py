"""Reading the toolchain a Creusot tag pins out of its `rust-toolchain` file."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lib import rust_toolchain
from lib.rust_toolchain import ToolchainError

PINNED = """[toolchain]
channel = "nightly-2026-08-03"
components = ["rustfmt", "rustc-dev", "llvm-tools"]
"""


def written(text: str) -> Path:
    directory = Path(tempfile.mkdtemp())
    (directory / rust_toolchain.FILE_NAME).write_text(text, encoding="utf-8")
    return directory


class Read(unittest.TestCase):
    def test_reads_the_channel_and_the_components(self) -> None:
        toolchain = rust_toolchain.read(written(PINNED))
        self.assertEqual(toolchain.channel, "nightly-2026-08-03")
        self.assertEqual(toolchain.components, ("rustfmt", "rustc-dev", "llvm-tools"))

    def test_components_may_be_absent(self) -> None:
        toolchain = rust_toolchain.read(written('[toolchain]\nchannel = "stable"\n'))
        self.assertEqual(toolchain.components, ())

    def test_reports_a_file_with_no_toolchain_table(self) -> None:
        with self.assertRaises(ToolchainError):
            rust_toolchain.read(written('channel = "stable"\n'))

    def test_reports_a_table_that_names_no_channel(self) -> None:
        for table in ("[toolchain]\n", '[toolchain]\nchannel = ""\n', "[toolchain]\nchannel = 1\n"):
            with self.subTest(table), self.assertRaises(ToolchainError):
                rust_toolchain.read(written(table))

    def test_reports_components_that_are_not_a_list_of_strings(self) -> None:
        for table in (
            '[toolchain]\nchannel = "stable"\ncomponents = "rustfmt"\n',
            '[toolchain]\nchannel = "stable"\ncomponents = [1]\n',
        ):
            with self.subTest(table), self.assertRaises(ToolchainError):
                rust_toolchain.read(written(table))

    def test_reports_a_file_that_is_not_toml(self) -> None:
        with self.assertRaises(ToolchainError):
            rust_toolchain.read(written("[toolchain\n"))

    def test_reports_a_file_that_is_not_there(self) -> None:
        with tempfile.TemporaryDirectory() as scratch, self.assertRaises(ToolchainError):
            rust_toolchain.read(Path(scratch))
