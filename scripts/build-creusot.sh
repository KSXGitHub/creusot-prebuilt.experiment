#!/usr/bin/env bash
# shellcheck source-path=SCRIPTDIR
# Build the Creusot binaries and the Coma prelude into $STAGE/creusot.
#
#   Usage: build-creusot.sh [target-triple]
#
# Everything upstream pins is pinned here too: the source tree is the release
# tag, the Rust toolchain is the channel in that tree's `rust-toolchain`, and the
# dependencies come from that tree's `Cargo.lock` (`--locked`). The build runs in
# a fixed directory with source paths remapped and SOURCE_DATE_EPOCH set to the
# tag's commit date.
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"

TARGET=${1:-$(rustc -vV | sed -n 's/^host: //p')}
[ -f "$SRC/rust-toolchain" ] || { echo "build-creusot: run scripts/fetch-source.sh first" >&2; exit 1; }

cd "$SRC"
CHANNEL=$(rust_channel)
COMPONENTS=$(sed -n 's/^components *= *\[\(.*\)\]/\1/p' rust-toolchain | tr -d '" ' | tr ',' ' ')
# Both expansions are meant to split: `rust-toolchain` lists the components
# as one string and each needs its own `-c`.
# shellcheck disable=SC2046,SC2086
rustup toolchain install "$CHANNEL" --profile minimal --no-self-update $(printf -- '-c %s ' $COMPONENTS)
rustup target add --toolchain "$CHANNEL" "$TARGET"

HOST=$(rustc -vV | sed -n 's/^host: //p')

# `creusot-rustc` is a rustc driver: it is compiled against `rustc-dev` and loads
# `librustc_driver-<hash>.so` out of the toolchain at run time. rustup ships
# `rustc-dev` for the host triple only, so `creusot-rustc` can be built for the
# host's own triple and for no other. `creusot-dev-config` is a helper for
# working on Creusot itself and is not shipped.
PACKAGES=(-p cargo-creusot -p creusot-install)
if [ "$TARGET" = "$HOST" ]; then
  PACKAGES+=(-p creusot-rustc)
else
  echo "build-creusot: $TARGET is not the host, so creusot-rustc is skipped" >&2
fi

SOURCE_DATE_EPOCH=$(source_date_epoch)
export SOURCE_DATE_EPOCH
export CARGO_INCREMENTAL=0
export CARGO_TARGET_DIR="$CARGO_TARGET"
# `creusot-rustc` is compiled against `rustc-dev`, whose sources sit under the
# rustup toolchain, so their paths reach the binary: 96 of them for Creusot
# 0.15.0. Without the third remapping, a build under /root and a build under
# /home/runner produce different bytes.
export RUSTFLAGS="--remap-path-prefix=$SRC=/build/creusot"
RUSTFLAGS="$RUSTFLAGS --remap-path-prefix=${CARGO_HOME:-$HOME/.cargo}=/build/cargo"
RUSTFLAGS="$RUSTFLAGS --remap-path-prefix=${RUSTUP_HOME:-$HOME/.rustup}=/build/rustup"

cargo "+$CHANNEL" build --release --locked --target "$TARGET" "${PACKAGES[@]}"
# `prelude-generator` only runs during this build, to generate the Coma prelude,
# and is not shipped: nothing in Creusot invokes it at run time, and the
# templates it reads live in the source tree. So build it for the host, where it
# is sure to run.
cargo "+$CHANNEL" build --release --locked --target "$HOST" -p prelude-generator

bin=$CARGO_TARGET/$TARGET/release
out=$STAGE/creusot
rm -rf "$out"
mkdir -p "$out/bin" "$out/share"
for program in cargo-creusot creusot-install creusot-rustc; do
  [ -f "$bin/$program" ] || continue
  install -m 755 "$bin/$program" "$out/bin/$program"
  strip "$out/bin/$program"
done

# The Coma prelude: the sources `prelude-generator` expands from the templates in
# prelude-generator/. Shipping it saves the consumer a second build and puts it
# where why3find looks.
CARGO_MANIFEST_DIR="$SRC/prelude-generator" "$CARGO_TARGET/$HOST/release/prelude-generator"
mkdir -p "$out/share/why3find"
cp -r "$SRC/target/creusot/packages" "$out/share/why3find/"

# why3find.json is what `cargo creusot new` seeds a project with;
# creusot_why3.conf is the solver configuration `cargo-creusot` hands to why3 as
# WHY3CONFIG. Both are read from the Creusot data directory.
#
# `creusot-std` and its siblings are not copied: a released `creusot-std` comes
# from crates.io, and those sources are only consulted through CREUSOT_PATH when
# running against a development build of Creusot.
cp why3find.json creusot-install/creusot_why3.conf LICENSE "$out/"

echo "build-creusot: assembled $out for $TARGET against $CHANNEL"
