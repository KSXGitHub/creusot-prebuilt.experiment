#!/usr/bin/env bash
# shellcheck source-path=SCRIPTDIR
# Slice the build tree a second time and check the archives come out identical.
#
#   Usage: check-packaging.sh [target-triple]
#
# This catches the ordinary ways an archive stops being reproducible: a
# directory walked in filesystem order, an mtime read off the disk, a gzip
# header carrying the name and the time of the file it compressed.
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"

target=${1:-}
second=$(mktemp -d)
trap 'rm -rf "$second"' EXIT

python3 "$REPO_ROOT/ci/package.py" \
  --repo "$REPO_ROOT" \
  --source "$SRC" \
  --dist "$second" \
  ${target:+--target "$target"} >/dev/null

diff "$REPO_ROOT/dist/SHA256SUMS" "$second/SHA256SUMS"
echo "check-packaging: a second slice of the same build tree hashes the same"
