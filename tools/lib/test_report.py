"""Running the unit tests and reporting them the way `cargo test` reports its own.

`unittest`'s default output is a row of dots, which says how many tests ran and
nothing about what they were. Its verbose mode names each test twice, bare and
again inside the dotted path, in lines long enough to wrap.

So the report is cargo's instead: a block per test module naming the file it
came from, a `test <name> ... ok` line per case, what each failure said, and a
result line. A name is qualified the way Python qualifies one, `Class.method`
beneath the module in the block's heading.

The report is narration, so it goes to stderr like every other explanation here.
"""

from __future__ import annotations

import sys
import time
import unittest
from collections.abc import Iterator
from pathlib import Path
from typing import Any, TextIO

PASSED = "ok"
FAILED = "FAILED"
IGNORED = "ignored"


class Report(unittest.TestResult):
    """One module's results, printed as each test finishes.

    Every test gets exactly one line, whatever happened inside it, which is why
    the outcome is settled between `startTest` and `stopTest` rather than in the
    hooks that record it. A test whose subtest failed calls neither `addSuccess`
    nor `addFailure`, so a line printed from those hooks would be missing for
    exactly the test whose line is wanted.
    """

    def __init__(self, stream: TextIO, module: str) -> None:
        super().__init__()
        self.stream = stream
        self.module = module
        self.outcomes = {PASSED: 0, FAILED: 0, IGNORED: 0}
        self._outcome = PASSED

    def _name(self, test: unittest.TestCase) -> str:
        """`Class.method`, the module being the heading the block was opened with."""
        return test.id().removeprefix(f"{self.module}.")

    def startTest(self, test: unittest.TestCase) -> None:
        super().startTest(test)
        self._outcome = PASSED

    def stopTest(self, test: unittest.TestCase) -> None:
        super().stopTest(test)
        self.outcomes[self._outcome] += 1
        self.stream.write(f"test {self._name(test)} ... {self._outcome}\n")
        self.stream.flush()

    def addError(self, test: unittest.TestCase, err: Any) -> None:
        super().addError(test, err)
        self._outcome = FAILED

    def addFailure(self, test: unittest.TestCase, err: Any) -> None:
        super().addFailure(test, err)
        self._outcome = FAILED

    def addUnexpectedSuccess(self, test: unittest.TestCase) -> None:
        super().addUnexpectedSuccess(test)
        self._outcome = FAILED

    def addSkip(self, test: unittest.TestCase, reason: str) -> None:
        super().addSkip(test, reason)
        self._outcome = IGNORED

    def addSubTest(self, test: unittest.TestCase, subtest: unittest.TestCase, err: Any) -> None:
        super().addSubTest(test, subtest, err)
        if err is not None:
            self._outcome = FAILED

    def problems(self) -> list[tuple[str, str]]:
        """Each failure and what it said, sorted by name so a log diff is stable.

        A test may appear more than once, because a failing subtest is recorded
        against the case that failed rather than against the test holding it.
        """
        listed = [(self._name(test), detail) for test, detail in self.errors + self.failures]
        listed += [
            (self._name(test), "the test passed, and is marked as expected to fail")
            for test in self.unexpectedSuccesses
        ]
        return sorted(listed)


def flatten(suite: unittest.TestSuite | unittest.TestCase) -> Iterator[unittest.TestCase]:
    """Every test in a suite, however deeply the loader nested it."""
    if isinstance(suite, unittest.TestCase):
        yield suite
        return
    for item in suite:
        yield from flatten(item)


def by_module(suite: unittest.TestSuite) -> dict[str, unittest.TestSuite]:
    """The tests grouped into the file each was written in, in discovery order.

    A module whose import failed arrives as a test of `unittest.loader`, which
    is a block of its own reporting the import as the failure it is.
    """
    groups: dict[str, unittest.TestSuite] = {}
    for test in flatten(suite):
        groups.setdefault(type(test).__module__, unittest.TestSuite()).addTest(test)
    return groups


def source(directory: Path, module: str) -> str:
    """The file a module was loaded from, or the module itself where it has none.

    A module whose import failed is handed back by the loader as a test of
    `unittest.loader`, which is not a file in the directory being discovered, so
    composing a path out of its name would name a file nobody can open.
    """
    return f"{directory.name}/{module}.py" if (directory / f"{module}.py").is_file() else module


def report(module: str, suite: unittest.TestSuite, path: str, stream: TextIO) -> bool:
    """Run one module's tests, report them, and say whether they all held."""
    count = suite.countTestCases()
    stream.write(f"\n     Running {path}\n\n")
    stream.write(f"running {count} {'test' if count == 1 else 'tests'}\n")

    result = Report(stream, module)
    started = time.perf_counter()
    result.startTestRun()
    suite.run(result)
    result.stopTestRun()
    elapsed = time.perf_counter() - started

    problems = result.problems()
    if problems:
        stream.write("\nfailures:\n\n")
        for name, detail in problems:
            stream.write(f"---- {name} ----\n{detail.rstrip()}\n\n")
        stream.write("failures:\n")
        for name, _ in problems:
            stream.write(f"    {name}\n")

    stream.write(
        f"\ntest result: {PASSED if result.wasSuccessful() else FAILED}. "
        f"{result.outcomes[PASSED]} passed; "
        f"{result.outcomes[FAILED]} failed; "
        f"{result.outcomes[IGNORED]} ignored; "
        f"finished in {elapsed:.2f}s\n"
    )
    stream.flush()
    return result.wasSuccessful()


def run(directory: Path, pattern: str | None = None) -> int:
    """Discover the tests under `directory` and run them. The exit status."""
    loader = unittest.TestLoader()
    if pattern:
        loader.testNamePatterns = [f"*{pattern}*"]
    groups = by_module(loader.discover(start_dir=str(directory), top_level_dir=str(directory)))
    stream = sys.stderr

    # A suite that has vanished would otherwise report nothing and succeed,
    # which reads exactly like a suite that passed.
    if not groups:
        wanted = f" matching {pattern!r}" if pattern else ""
        stream.write(f"no tests found in {directory}{wanted}\n")
        return 1

    held = [report(module, suite, source(directory, module), stream) for module, suite in groups.items()]
    stream.write("\n")
    return 0 if all(held) else 1
