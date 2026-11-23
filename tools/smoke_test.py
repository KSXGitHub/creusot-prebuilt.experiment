#!/usr/bin/env python3
"""Install what is in dist/ into a scratch directory and run every tool.

What this proves is that the archives install where the tools look for each
other, and that a crate gets as far as Coma. It stops short of a proof, because
the SMT solvers are not shipped here: `creusot-install provers` downloads them
from their own projects.
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

from lib import checksums, layout, manifest
from lib.console import say
from lib.run import CommandError, output, run

DEMO = "demo"
COMA = Path("verif") / "demo_rlib" / "add_one.coma"


def installed_driver(data: Path) -> list[Path]:
    """The binaries whose content decides what a build of the demo produces.

    `creusot-rustc` compiles it and `cargo-creusot` chooses the flags, so a
    change to either is a reason not to reuse what the last run compiled.
    """
    candidates = [data / "bin" / "cargo-creusot", *data.glob("toolchains/*/bin/creusot-rustc")]
    found = [path for path in candidates if path.is_file()]
    if not found:
        raise CommandError(f"no driver was installed into {data}")
    return found


def keep_only(root: Path, wanted: str) -> None:
    """Drop every dependency tree but the one this run will use.

    Each is about 90 MB, and the build cache carries them, so the ones built
    for drivers that have been replaced would otherwise accumulate in it.
    """
    if not root.is_dir():
        return
    for entry in root.iterdir():
        if entry.name != wanted:
            shutil.rmtree(entry, ignore_errors=True)


def check(plan: layout.Layout, work: Path) -> None:
    data = work / "data"
    # dist/ holds the installer a release uploads, which differs from the
    # checkout's copy in the release it installs by default. Running that one
    # means the file a consumer downloads is the file this check exercises.
    installer = plan.dist / manifest.INSTALLER
    run([sys.executable, installer, "--from-dir", plan.dist, "--data-home", data, "--all"])

    driver = checksums.digest_of(installed_driver(data))[:16]
    keep_only(plan.smoke_root, driver)
    environment = {
        "CREUSOT_DATA_HOME": str(data),
        "PATH": f"{data / 'bin'}{os.pathsep}{os.environ['PATH']}",
        # The demo crate's dependencies are `creusot-std` and its proc-macro
        # tree, which take about half a minute to compile. Keeping them under
        # `build_root` lets the build cache carry them between runs. The crate
        # under verification is a different unit in every run, so the driver
        # still runs on it and still emits the Coma this test looks for.
        "CARGO_TARGET_DIR": str(plan.smoke_target(driver)),
    }
    for command in (["cargo-creusot", "creusot", "version"], ["why3", "--version"], ["why3find", "--version"]):
        run(command, extra_env=environment)

    # `why3 --print-datadir` is the prefix the asset was built for, and the one
    # it was just unpacked at. A mismatch means the two have drifted apart and
    # why3 would read a theory directory that is not there.
    datadir = Path(output(["why3", "--print-datadir"], extra_env=environment).strip())
    if not datadir.is_dir():
        raise CommandError(f"why3 reads {datadir}, which does not exist")

    run(["cargo-creusot", "creusot", "new", DEMO], cwd=work, extra_env=environment)
    # `--dry-run-why3find` prints the why3find command rather than running it,
    # so the run ends at the Coma the driver produced and asks no solver for
    # anything.
    run(["cargo-creusot", "creusot", "--dry-run-why3find"], cwd=work / DEMO, extra_env=environment)

    produced = work / DEMO / COMA
    if not produced.is_file():
        raise CommandError(f"{COMA} was not generated")
    say(f"smoke-test: every tool installed, and {COMA.name} came out of the driver")


def main() -> int:
    plan = layout.read()
    if not plan.dist.is_dir():
        raise CommandError(f"no {plan.dist}; package the build first")
    work = Path(tempfile.mkdtemp())
    try:
        check(plan, work)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except CommandError as error:
        say(f"smoke-test: {error}")
        sys.exit(1)
