#!/usr/bin/env bash
# shellcheck source-path=SCRIPTDIR
# Install dist/ into a scratch directory and put the tools through their paces.
#
# What this proves is that the archives install where the tools look for each
# other and that a crate gets as far as Coma. It stops short of a proof, because
# the SMT solvers are not shipped here: `creusot-install provers` downloads them
# from their own projects.
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"

[ -d "$REPO_ROOT/dist" ] || { echo "smoke-test: run scripts/package.sh first" >&2; exit 1; }

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
data=$work/data

python3 "$REPO_ROOT/install.py" --from-dir "$REPO_ROOT/dist" --data-home "$data" --all

export CREUSOT_DATA_HOME=$data
export PATH=$data/bin:$PATH

cargo-creusot creusot version
why3 --version
why3find --version

# `why3 --print-datadir` is the prefix the asset was built for, and the one it
# was just unpacked at. A mismatch means the two have drifted apart and why3
# would read a theory directory that is not there.
datadir=$(why3 --print-datadir)
[ -d "$datadir" ] || { echo "smoke-test: why3 reads $datadir, which does not exist" >&2; exit 1; }

cd "$work"
cargo-creusot creusot new demo
cd demo
# `--dry-run-why3find` prints the why3find command rather than running it, so the
# run ends at the Coma the driver produced and asks no solver for anything.
cargo-creusot creusot --dry-run-why3find
coma=verif/demo_rlib/add_one.coma
[ -f "$coma" ] || { echo "smoke-test: $coma was not generated" >&2; exit 1; }

echo "smoke-test: every tool installed, and $(basename "$coma") came out of the driver"
