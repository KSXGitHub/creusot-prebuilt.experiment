"""Running the unit tests so that the log says which ones ran.

`unittest`'s default output is a row of dots, which reports how many tests ran
and nothing about what they were. Its verbose mode names each test twice, bare
and again inside the dotted path, in lines long enough to wrap. This prints the
module once as a heading and one line per test under it, which is what a CI log
has to carry for a reader who cannot run the suite.

The report is narration, so it goes to stderr like every other explanation here.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import Any

OUTCOME_WIDTH = 9


class NamedResult(unittest.TextTestResult):
    """A result that names each test under the module it came from."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        # Every line of the report is written here, so the base class's own
        # dots and verbose rows are turned off rather than printed alongside.
        # What it still prints is the traceback of each failure, which is its
        # own format and worth keeping.
        self.showAll = False
        self.dots = False
        self._heading: str | None = None

    def _report(self, test: unittest.TestCase, outcome: str, note: str = "") -> None:
        self._line(type(test).__module__, test, outcome, note)

    def _line(self, module: str, test: unittest.TestCase, outcome: str, note: str = "") -> None:
        """Report `test` under `module`, which names the heading to print it beneath.

        The module is passed rather than read off `test`, because a subtest is an
        instance of a class `unittest` itself defines and so answers with
        `unittest.case` for the module the test was written in.
        """
        if module != self._heading:
            self._heading = module
            self.stream.write(f"{module}\n")
        name = test.id().removeprefix(f"{module}.")
        self.stream.write(f"  {outcome:<{OUTCOME_WIDTH}}{name}{note}\n")
        self.stream.flush()

    def addSuccess(self, test: unittest.TestCase) -> None:
        super().addSuccess(test)
        self._report(test, "ok")

    def addFailure(self, test: unittest.TestCase, err: Any) -> None:
        super().addFailure(test, err)
        self._report(test, "FAILED")

    def addError(self, test: unittest.TestCase, err: Any) -> None:
        super().addError(test, err)
        self._report(test, "ERROR")

    def addSkip(self, test: unittest.TestCase, reason: str) -> None:
        super().addSkip(test, reason)
        self._report(test, "skipped", f"  ({reason})")

    def addExpectedFailure(self, test: unittest.TestCase, err: Any) -> None:
        super().addExpectedFailure(test, err)
        self._report(test, "expected")

    def addUnexpectedSuccess(self, test: unittest.TestCase) -> None:
        super().addUnexpectedSuccess(test)
        self._report(test, "UNEXPECTED")

    def addSubTest(self, test: unittest.TestCase, subtest: unittest.TestCase, err: Any) -> None:
        super().addSubTest(test, subtest, err)
        # A test whose subtests all passed is reported once, by `addSuccess`.
        # Only a failing case is worth a line of its own, and it carries the
        # value that failed, which the bare method name does not.
        if err is not None:
            self._line(type(test).__module__, subtest, "FAILED")


def run(directory: Path, pattern: str | None = None) -> int:
    """Discover the tests under `directory` and run them. The exit status."""
    loader = unittest.TestLoader()
    if pattern:
        loader.testNamePatterns = [f"*{pattern}*"]
    suite = loader.discover(start_dir=str(directory), top_level_dir=str(directory))
    runner = unittest.TextTestRunner(stream=sys.stderr, resultclass=NamedResult)
    return 0 if runner.run(suite).wasSuccessful() else 1
