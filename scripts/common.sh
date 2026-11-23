# shellcheck shell=bash
# Sourced by every build script. Defines the paths the build uses and reads the
# release identifier. Sets no `set -euo pipefail` of its own: the sourcing script
# owns that.

REPO_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
export REPO_ROOT

PKGVER=$(cat "$REPO_ROOT/pkgver")
PKGREL=$(cat "$REPO_ROOT/pkgrel")
export PKGVER PKGREL

# Both defaults are part of the build inputs, not a convenience: a Rust binary
# records the directory it was compiled in, and `why3` records the prefix it was
# installed at. Build somewhere else and the assets differ from the published
# ones. See the reproducibility section of README.md.
BUILD_ROOT=${BUILD_ROOT:-/var/tmp/creusot-prebuilt}
# opam installs a switch into `<switch directory>/_opam`, and that is the path
# why3 bakes in, so it is also where the why3 asset has to be unpacked.
WHY3_SWITCH=${WHY3_SWITCH:-/opt/creusot-why3}
export BUILD_ROOT WHY3_SWITCH

SRC=$BUILD_ROOT/v$PKGVER/src
CARGO_TARGET=$BUILD_ROOT/v$PKGVER/target
STAGE=$REPO_ROOT/build
export SRC CARGO_TARGET STAGE

CREUSOT_REPO=${CREUSOT_REPO:-https://github.com/creusot-rs/creusot}
export CREUSOT_REPO

# The commit date of the upstream tag. Every mtime in every asset is set to it,
# and `cargo` stamps it into anything that calls `SOURCE_DATE_EPOCH`. It depends
# on the Creusot tag alone, so it does not move between pkgrels.
source_date_epoch() {
  git -C "$SRC" log -1 --format=%ct
}

# The Rust toolchain the Creusot tag pins. `creusot-rustc` is a rustc driver and
# loads `librustc_driver-<hash>.so` out of this toolchain at run time, so an
# installation has to carry it under this exact name.
rust_channel() {
  sed -n 's/^channel *= *"\(.*\)"/\1/p' "$SRC/rust-toolchain"
}
