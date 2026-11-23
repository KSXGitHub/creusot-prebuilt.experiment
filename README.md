# creusot-prebuilt.experiment

Prebuilt binaries of [Creusot](https://github.com/creusot-rs/creusot), the
deductive verifier for Rust, and of the Why3 framework it discharges proofs
with. They are published as the assets of a [GitHub
release](https://github.com/KSXGitHub/creusot-prebuilt.experiment/releases).

Creusot publishes no binaries of its own, so installing it means compiling a
pinned Rust nightly together with `rustc-dev`, and building an opam switch that
compiles OCaml, Why3 and why3find from source. That takes tens of minutes, which
a continuous-integration job pays on every run. This repository pays it once per
release.

## How a release is named

A release is named `<creusot version>-<build revision>`, such as `0.15.0-1`. The
first part is the Creusot release the binaries were built from. The second
counts the builds of that same Creusot version, and goes up when the packaging
changes while the upstream version does not.

## What a release holds

One archive per tool, and no bundle of several. A task that only translates a
crate to Coma can take the tools it needs and leave the prover framework
undownloaded. The release notes list every asset with its size and what it
holds.

Each archive unpacks at one directory and needs no further moving:

| the asset's `prefix` in `release.json` | unpack it at                                                                       |
| -------------------------------------- | ---------------------------------------------------------------------------------- |
| `creusot-data-home`                    | `$CREUSOT_DATA_HOME`, else `$XDG_DATA_HOME/creusot`, else `~/.local/share/creusot` |
| `why3-prefix`                          | the absolute path the same `release.json` records as `why3_prefix`                 |

`why3-prefix` is a fixed path rather than a choice, because `why3` compiles its
data directory in and honours neither `WHY3DATA` nor being moved.
`why3 --print-datadir` reports the prefix it was built at, so a copy anywhere
else looks for its theories where they are not.

## Installing

`install.py` reads the release's own description of itself, so it needs no
argument beyond the tools wanted, and nothing but a Python 3 standard library.

```bash
curl -fsSLO https://github.com/KSXGitHub/creusot-prebuilt.experiment/releases/latest/download/install.py
```

```bash
python3 install.py --list
```

```bash
python3 install.py cargo-creusot creusot-rustc creusot-prelude why3 why3find
```

Add `$CREUSOT_DATA_HOME/bin` to `PATH` afterwards, and `cargo creusot` works.
`--all` takes everything, `--release <tag>` pins a release other than the
latest, and `--data-home <dir>` puts the Creusot half somewhere of your
choosing.

To install by hand instead, download an archive and unpack it at the directory
[What a release holds](#what-a-release-holds) gives for its prefix. The `why3`
asset additionally has to be reachable as `$CREUSOT_DATA_HOME/bin/why3`, because
that is where `cargo-creusot` looks for it.

### What you need

| prerequisite                                | why                                                                           |
| ------------------------------------------- | ----------------------------------------------------------------------------- |
| x86_64 Linux with glibc                     | the only target built so far                                                  |
| `rustup`                                    | `cargo creusot` compiles the crate under verification with the pinned nightly |
| write access to the `why3_prefix` directory | `why3` reads its theories from the path it was built at                       |
| `$CREUSOT_DATA_HOME/bin` on `PATH`          | an installer cannot edit your `PATH`                                          |

### What is not here

The SMT solvers. Alt-Ergo, Z3, CVC4 and CVC5 have binary releases of their own,
and `creusot-install provers` downloads the versions Creusot expects:

```bash
creusot-install provers
```

Why3's GTK front end, `why3-ide`, is not built either. It needs system GTK
packages that a headless machine has no reason to carry.

## Verifying what you downloaded

Every release carries `SHA256SUMS` over all of its assets:

```bash
sha256sum --check --ignore-missing SHA256SUMS
```

Every asset also carries a GitHub build attestation, which ties it to the
workflow run and the commit that produced it:

```bash
gh attestation verify <asset> --repo KSXGitHub/creusot-prebuilt.experiment
```

## Reproducing a release

This section is for somebody who wants to rebuild a release rather than download
it, and assumes a clone of this repository at the release's tag.

Everything the build consumes is pinned. The Creusot source is the upstream tag
named in `release.json`, the Rust toolchain is the channel that tag's
`rust-toolchain` file names, the Rust dependencies come from its `Cargo.lock`,
and Why3 and why3find are the git commits its `creusot-deps.opam` pins. Every
timestamp in every archive is the upstream commit date rather than the time of
the build, and each archive is written with its entries sorted and its ownership
dropped.

Two directories are part of the build rather than a matter of taste, because a
Rust binary records the directory it was compiled in and `why3` records the
prefix it was installed at. Building elsewhere produces different checksums.
`scripts/common.sh` holds both defaults.

```bash
just build
```

Then compare `dist/SHA256SUMS` against the release's own. The
[reproducibility workflow](.github/workflows/reproducibility.yaml) does exactly
this, with the build cache switched off. It is started by hand rather than on a
schedule.

On one machine, every asset reproduces. Two builds of `0.15.0-1`, each starting
from an empty opam switch and an empty cargo target directory, produced
byte-identical archives, Why3 included.

Across two machines running the same Ubuntu release, the picture is partial.
`cargo-creusot`, `creusot-install` and `creusot-prelude` agreed. `why3` and
`why3find` did not, and they carry no path from the machine that built them, so
what differs has not been identified. `creusot-rustc` did not either, because
96 paths from the rustup toolchain it is compiled against had reached the
binary; a `--remap-path-prefix` for the rustup home now removes them.

## Building it yourself

This section is for somebody working on this repository.

`just --list` names every task. `just check` runs the checks that need no build.
`just build` fetches the source, builds both halves and writes the archives. It
needs `rustup`, `opam`, and the system packages the OCaml dependencies are
compiled against, which
[the build action](.github/actions/build/action.yaml) installs on Ubuntu.

[CLAUDE.md](CLAUDE.md) holds the conventions this repository is written to. It
is addressed to the AI agents that work on it rather than to you, but it is the
place those conventions are recorded.

## Licences

The build scripts and everything else original to this repository are under the
[MIT licence](LICENSE.md). The binaries are not: Creusot, Why3 and why3find are
each distributed under their own terms, and every archive carries the licence of
what it holds under `share/licenses/`.
