"""Reading the Why3 pins out of a `creusot-deps.opam`.

The file names each pin twice, under `depends:` and again under `pin-depends:`,
and names `why3-ide` beside `why3`. Answering with the wrong one of those pins
the build to a version nothing asked for.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lib import opam
from lib.opam import OpamError

DEPS = """opam-version: "2.0"
synopsis: "Dependencies of Creusot"

depends: [
  "why3" {= "git-05bf4ddf"}
  "why3-ide" {= "git-05bf4ddf"}
  "why3find" {= "git-89dd8721"}
]

pin-depends: [
  [ "why3.git-05bf4ddf" "git+https://gitlab.inria.fr/why3/why3.git#05bf4ddf" ]
  [ "why3-ide.git-05bf4ddf" "git+https://gitlab.inria.fr/why3/why3.git#05bf4ddf" ]
  [ "why3find.git-89dd8721" "git+https://git.frama-c.com/pub/why3find.git#89dd8721" ]
]
"""


def written(text: str) -> Path:
    directory = Path(tempfile.mkdtemp())
    (directory / opam.FILE_NAME).write_text(text, encoding="utf-8")
    return directory


class TakePinDepends(unittest.TestCase):
    def test_returns_the_contents_of_the_list(self) -> None:
        body = opam.take_pin_depends(DEPS)
        self.assertIsNotNone(body)
        assert body is not None
        self.assertIn('"why3.git-05bf4ddf"', body)
        self.assertNotIn("opam-version", body)
        self.assertNotIn('{= "git-05bf4ddf"}', body)

    def test_declines_a_file_with_no_list(self) -> None:
        self.assertIsNone(opam.take_pin_depends('opam-version: "2.0"\n'))

    def test_declines_a_list_that_never_closes(self) -> None:
        self.assertIsNone(opam.take_pin_depends('pin-depends: [\n  [ "why3.git-1" "url" ]\n'))


class PinEntries(unittest.TestCase):
    def test_returns_one_entry_per_bracketed_pair(self) -> None:
        body = opam.take_pin_depends(DEPS)
        assert body is not None
        entries = opam.pin_entries(body)
        self.assertEqual(len(entries), 3)
        self.assertIn('"why3.git-05bf4ddf"', entries[0])

    def test_an_empty_list_has_no_entries(self) -> None:
        self.assertEqual(opam.pin_entries("  \n  "), [])


class ReadPins(unittest.TestCase):
    def test_reads_the_two_pins_the_build_needs(self) -> None:
        self.assertEqual(
            opam.read_pins(written(DEPS)),
            {"why3": "git-05bf4ddf", "why3find": "git-89dd8721"},
        )

    def test_does_not_answer_with_the_ide_package(self) -> None:
        self.assertNotIn("why3-ide", opam.read_pins(written(DEPS)))

    def test_reports_a_file_with_no_pin_depends_list(self) -> None:
        with self.assertRaises(OpamError):
            opam.read_pins(written('opam-version: "2.0"\n'))

    def test_reports_a_missing_pin(self) -> None:
        without_why3find = DEPS.replace(
            '  [ "why3find.git-89dd8721" "git+https://git.frama-c.com/pub/why3find.git#89dd8721" ]\n', ""
        )
        with self.assertRaises(OpamError) as caught:
            opam.read_pins(written(without_why3find))
        self.assertIn("why3find", str(caught.exception))

    def test_reports_a_file_that_is_not_there(self) -> None:
        with tempfile.TemporaryDirectory() as scratch, self.assertRaises(OpamError):
            opam.read_pins(Path(scratch))
