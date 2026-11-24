"""The contract between `install.py` and the packaging step that stamps it.

`tools/lib/packaging.py` rewrites one assignment in `install.py` so that the
copy uploaded with a release installs that release rather than whatever is
newest. Renaming or reshaping that assignment breaks nothing in `install.py`
itself, and the packaging step that refuses it runs only inside a build, which
is late. These tests hold the two sides together from the checks that need no
build.
"""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType

from lib import layout, manifest, packaging

SAMPLE_TAG = "1.2.3-4"


def load(path: Path) -> ModuleType:
    """Import a copy of `install.py` and hand back the module it defines.

    Importing rather than reading the text means a stamped copy has to be a
    module that runs, not just a file with the right line in it.
    """
    specification = importlib.util.spec_from_file_location("installer_under_test", path)
    if specification is None or specification.loader is None:
        raise AssertionError(f"{path} cannot be imported as a module")
    module = importlib.util.module_from_spec(specification)
    # `install.py` writes its annotations as strings, and `dataclass` resolves a
    # field's annotation by looking its class's module up in `sys.modules`, so a
    # module executed before it is registered there raises instead.
    sys.modules[specification.name] = module
    specification.loader.exec_module(module)
    return module


class InstallerPin(unittest.TestCase):
    def setUp(self) -> None:
        self.installer = layout.repository_root() / manifest.INSTALLER

    def test_the_checkout_copy_installs_the_newest_release(self) -> None:
        self.assertIsNone(load(self.installer).PINNED_RELEASE)

    def test_stamping_pins_a_copy_to_the_release_it_is_uploaded_with(self) -> None:
        with tempfile.TemporaryDirectory() as scratch:
            stamped = Path(scratch) / manifest.INSTALLER
            packaging.stamp_installer(self.installer, stamped, SAMPLE_TAG)
            self.assertEqual(load(stamped).PINNED_RELEASE, SAMPLE_TAG)

    def test_stamping_refuses_a_source_that_does_not_hold_the_assignment_once(self) -> None:
        text = self.installer.read_text(encoding="utf-8")
        mutations = {
            "renamed": text.replace(packaging.INSTALLER_PIN, "PINNED: str | None = None"),
            "duplicated": f"{text}\n{packaging.INSTALLER_PIN}\n",
        }
        for name, mutated in mutations.items():
            with self.subTest(name), tempfile.TemporaryDirectory() as scratch:
                source = Path(scratch) / manifest.INSTALLER
                source.write_text(mutated, encoding="utf-8")
                with self.assertRaises(SystemExit):
                    packaging.stamp_installer(source, Path(scratch) / "stamped.py", SAMPLE_TAG)
