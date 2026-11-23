#!/usr/bin/env python3
"""Build the Creusot binaries and the Coma prelude into the staging tree.

Everything upstream pins is pinned here too: the source is the release tag, the
toolchain is the channel that tag's `rust-toolchain` names, and the dependencies
come from its `Cargo.lock` through `--locked`. The build runs in a fixed
directory with paths remapped and `SOURCE_DATE_EPOCH` set to the tag's commit
date, so repeating it produces the same bytes.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

from lib import layout, rust_build, rust_toolchain
from lib.console import say
from lib.gitcmd import GitError
from lib.run import CommandError, require, run

PROGRAMS = ("cargo-creusot", "creusot-install", "creusot-rustc")
"""Installed from the release build when the build produced them. `creusot-rustc`
is absent when the target is not the host, which `rust_build` decides."""

PRELUDE_GENERATOR = "prelude-generator"
"""Runs during this build to expand the Coma prelude from the templates in the
source tree, and is not shipped: nothing in Creusot invokes it at run time."""

CONFIGURATION = ("why3find.json", "creusot-install/creusot_why3.conf", "LICENSE")
"""Copied to the staging root. `why3find.json` is what `cargo creusot new` seeds
a project with, and `creusot_why3.conf` is the solver configuration
`cargo-creusot` hands to why3 as `WHY3CONFIG`. `creusot-std` and its siblings are
not copied: a released `creusot-std` comes from crates.io, and those sources are
only read through `CREUSOT_PATH` against a development build of Creusot."""


def build(plan: layout.Layout, target: str) -> None:
    source = plan.source
    if not (source / rust_toolchain.FILE_NAME).is_file():
        raise CommandError(f"no {rust_toolchain.FILE_NAME} in {source}; fetch the source first")

    require("rustup", "install it from https://rustup.rs")
    toolchain = rust_toolchain.read(source)
    host = rust_build.host_triple()

    components = [flag for component in toolchain.components for flag in ("-c", component)]
    run(["rustup", "toolchain", "install", toolchain.channel, "--profile", "minimal", "--no-self-update", *components])
    run(["rustup", "target", "add", "--toolchain", toolchain.channel, target])

    packages = rust_build.packages_for(target, host)
    if target != host:
        skipped = ", ".join(sorted(set(rust_build.SHIPPED_FOR_THE_HOST_ONLY) - set(packages)))
        say(f"build-creusot: {target} is not the host, so {skipped} is skipped")

    environment = {
        "SOURCE_DATE_EPOCH": str(plan.source_date_epoch()),
        "CARGO_INCREMENTAL": "0",
        "CARGO_TARGET_DIR": str(plan.cargo_target),
        "RUSTFLAGS": rust_build.remap_flags(source),
    }
    cargo = ["cargo", f"+{toolchain.channel}", "build", "--release", "--locked"]
    selected = [flag for package in packages for flag in ("-p", package)]
    run([*cargo, "--target", target, *selected], cwd=source, extra_env=environment)
    # Built for the host, where it is sure to run.
    run([*cargo, "--target", host, "-p", PRELUDE_GENERATOR], cwd=source, extra_env=environment)

    assemble(plan, target, host)


def assemble(plan: layout.Layout, target: str, host: str) -> None:
    built = plan.cargo_target / target / "release"
    out = plan.creusot_stage
    shutil.rmtree(out, ignore_errors=True)
    (out / "bin").mkdir(parents=True)
    (out / "share").mkdir()

    for program in PROGRAMS:
        produced = built / program
        if not produced.is_file():
            continue
        installed = out / "bin" / program
        shutil.copyfile(produced, installed)
        installed.chmod(0o755)
        run(["strip", installed])

    # `prelude-generator` writes beside the manifest it is told about, so it has
    # to be pointed at its own directory in the source tree.
    generator = plan.cargo_target / host / "release" / PRELUDE_GENERATOR
    run([generator], cwd=plan.source, extra_env={"CARGO_MANIFEST_DIR": str(plan.source / PRELUDE_GENERATOR)})
    prelude = plan.source / "target" / "creusot" / "packages"
    if not prelude.is_dir():
        raise CommandError(f"{PRELUDE_GENERATOR} wrote no prelude at {prelude}")
    (out / "share" / "why3find").mkdir(parents=True)
    shutil.copytree(prelude, out / "share" / "why3find" / "packages", symlinks=True)

    for name in CONFIGURATION:
        shutil.copyfile(plan.source / name, out / Path(name).name)

    say(f"build-creusot: assembled {out} for {target} against {plan.release.upstream_tag}")


def main(argv: list[str] | None = None) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    if len(arguments) > 1:
        say("usage: build_creusot.py [target-triple]")
        return 2
    plan = layout.read()
    build(plan, arguments[0] if arguments and arguments[0] else rust_build.host_triple())
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (CommandError, GitError, rust_toolchain.ToolchainError) as error:
        say(f"build-creusot: {error}")
        sys.exit(1)
