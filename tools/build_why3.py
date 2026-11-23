#!/usr/bin/env python3
"""Build Why3 and why3find into the staging tree.

Creusot proves nothing without them and neither has a binary release: upstream
installs them by building an opam switch from `creusot-deps.opam`, which
compiles OCaml, Why3 and why3find from source. The versions come from the tag's
own `creusot-deps.opam`, so what is built always matches the Creusot release it
ships beside.

why3 compiles its data directory in and honours neither `WHY3DATA` nor being
moved, so the switch is created at a fixed directory and the asset has to be
unpacked at the `_opam` inside it.
"""

from __future__ import annotations

import filecmp
import os
import shlex
import shutil
import sys
from pathlib import Path

from lib import layout, opam
from lib.console import say
from lib.run import CommandError, require, run

PROGRAMS = ("why3", "why3find")

COMPILE_ONLY_SUFFIXES = (".cmx", ".cmi", ".cmt", ".cmti", ".ml", ".mli", ".a", ".o", ".cma")
"""Dropped from `lib/why3`: interfaces, sources and archives that are only
needed to *compile* against Why3, which nothing in an installation does. For
Why3 1.8.2 this takes the directory from 131 MB to 21 MB. Excluding by what a
file is rather than keeping `*.cmxs` matters, because `lib/why3` also holds the
`why3server` executable that why3 spawns to run the solvers. Without it every
solver call hangs for ever, with no error."""

COMPILE_ONLY_NAMES = ("META", "dune-package")
"""Dropped from `lib/why3` as well: ocamlfind and dune metadata for compiling
against Why3. The version they carry comes from dune reading the source tree
rather than from Why3, and need not agree with it: for the commit pinned here
they say 1.8.1+git while the binary reports 1.8.2+git."""

LICENCE_CANDIDATES = ("doc/why3find", ".opam-switch/sources/why3find")
"""Where opam may have left why3find's licence. Why3's own ships inside
`share/why3`."""


def is_compile_only(path: Path) -> bool:
    """Whether an installation never reads this file."""
    return path.name.endswith(COMPILE_ONLY_SUFFIXES) or path.name in COMPILE_ONLY_NAMES


def copy_files_an_installation_reads(source: Path, destination: Path) -> None:
    """Copy the files that survive the filter, and no directory that holds none.

    Walking the files rather than the tree is what keeps an emptied directory
    out of the result: `lib/why3` has ten whose every member is compile-only,
    and a tree copy that filtered names would leave all ten behind empty.

    A symlink is skipped, which is what this filter did before as well. There
    are none in `lib/why3` today, so one appearing upstream would go unnoticed.
    """
    for path in sorted(source.rglob("*")):
        if path.is_symlink() or not path.is_file() or is_compile_only(path):
            continue
        target = destination / path.relative_to(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        shutil.copymode(path, target)


def switch_is_current(plan: layout.Layout, marker: Path) -> bool:
    """Whether the switch already holds what this release's dependencies ask for.

    The marker is written only once an install has succeeded, so a switch left
    half-built by a failed run is rebuilt rather than reused.
    """
    built = plan.why3_prefix / "bin" / "why3"
    declared = plan.source / opam.FILE_NAME
    return built.is_file() and marker.is_file() and filecmp.cmp(declared, marker, shallow=False)


def create_switch(plan: layout.Layout, marker: Path) -> None:
    switch = plan.why3_switch
    declared = plan.source / opam.FILE_NAME

    # Empty the directory without removing it: on a machine where only root may
    # write to its parent, somebody else created it and handed it over.
    switch.mkdir(parents=True, exist_ok=True)
    if not os.access(switch, os.W_OK):
        raise CommandError(f"{switch} is not writable; create it and hand it to this user")
    for entry in switch.iterdir():
        shutil.rmtree(entry) if entry.is_dir() and not entry.is_symlink() else entry.unlink()

    # opam pins a package that lives in a directory, so the dependencies get one
    # of their own rather than being read out of the Creusot checkout.
    dependencies = switch / "deps"
    dependencies.mkdir()
    shutil.copyfile(declared, dependencies / opam.FILE_NAME)

    run(["opam", "switch", "create", "-y", "--empty", switch])
    # `creusot-deps.opam` also asks for why3-ide, Why3's GTK front end, unless
    # `in-creusot-ci` is set. Its lablgtk3 dependencies need system GTK
    # packages that a headless machine has no reason to carry. Setting the
    # variable on this switch leaves the rest of opam alone.
    run(["opam", "var", "in-creusot-ci=true", "--switch", switch])
    run(["opam", "install", "-y", "--switch", switch, dependencies])
    shutil.copyfile(declared, marker)


def assemble(plan: layout.Layout) -> None:
    prefix = plan.why3_prefix
    out = plan.why3_stage
    shutil.rmtree(out, ignore_errors=True)
    (out / "bin").mkdir(parents=True)

    for program in PROGRAMS:
        installed = out / "bin" / program
        shutil.copyfile(prefix / "bin" / program, installed)
        installed.chmod(0o755)
        run(["strip", installed])

    shutil.copytree(prefix / "share" / "why3", out / "share" / "why3", symlinks=True)
    copy_files_an_installation_reads(prefix / "lib" / "why3", out / "lib" / "why3")

    for candidate in LICENCE_CANDIDATES:
        found = sorted((prefix / candidate).glob("LICENSE*")) if (prefix / candidate).is_dir() else []
        if found:
            shutil.copyfile(found[0], out / "LICENSE.why3find")
            break
    else:
        raise CommandError("why3find's licence is missing from the switch")

    run([out / "bin" / "why3", "--version"])
    say(f"build-why3: assembled {out}, compiled to read its data from {prefix}")


def main() -> int:
    plan = layout.read()
    require("opam", "install it from https://opam.ocaml.org")
    if not (plan.source / opam.FILE_NAME).is_file():
        raise CommandError(f"no {opam.FILE_NAME} in {plan.source}; fetch the source first")

    try:
        run(["opam", "switch", "list"])
    except CommandError:
        # A container without user namespaces cannot run opam's bubblewrap
        # sandbox. Set OPAM_INIT_FLAGS=--disable-sandboxing there, and leave it
        # unset everywhere else: the sandbox is what keeps a package's build
        # from reaching outside its own tree.
        run(["opam", "init", "--bare", "-y", *shlex.split(os.environ.get("OPAM_INIT_FLAGS", ""))])

    marker = plan.why3_switch / opam.FILE_NAME
    if switch_is_current(plan, marker):
        say(f"build-why3: reusing the switch at {plan.why3_switch}; its {opam.FILE_NAME} already matches")
    else:
        create_switch(plan, marker)

    assemble(plan)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except CommandError as error:
        say(f"build-why3: {error}")
        sys.exit(1)
