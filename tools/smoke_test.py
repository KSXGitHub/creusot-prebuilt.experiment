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

import layout
from run import CommandError, output, run

DEMO = "demo"
COMA = Path("verif") / "demo_rlib" / "add_one.coma"


def check(plan: layout.Layout, work: Path) -> None:
    data = work / "data"
    run([sys.executable, plan.repo / "install.py", "--from-dir", plan.dist, "--data-home", data, "--all"])

    environment = {
        "CREUSOT_DATA_HOME": str(data),
        "PATH": f"{data / 'bin'}{os.pathsep}{os.environ['PATH']}",
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
    print(f"smoke-test: every tool installed, and {COMA.name} came out of the driver")


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
        print(f"smoke-test: {error}", file=sys.stderr)
        sys.exit(1)
