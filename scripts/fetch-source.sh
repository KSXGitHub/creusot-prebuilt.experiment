#!/usr/bin/env bash
# shellcheck source-path=SCRIPTDIR
# Put the Creusot source for this release at $SRC, at the tag `v$PKGVER`.
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"

tag=v$PKGVER
if [ -e "$SRC/.git" ] && [ "$(git -C "$SRC" describe --tags --exact-match 2>/dev/null || true)" = "$tag" ]; then
  echo "fetch-source: $SRC is already at $tag"
else
  rm -rf "$SRC"
  mkdir -p "$(dirname "$SRC")"
  git clone --depth 1 --branch "$tag" "$CREUSOT_REPO" "$SRC"
fi

echo "fetch-source: $tag is commit $(git -C "$SRC" rev-parse HEAD)"
