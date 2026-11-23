#!/usr/bin/env bash
# shellcheck source-path=SCRIPTDIR
# Slice $STAGE into one archive per tool under dist/.
#
#   Usage: package.sh [target-triple]
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"

target=${1:-}
exec python3 "$REPO_ROOT/tools/package.py" \
  --repo "$REPO_ROOT" \
  --source "$SRC" \
  ${target:+--target "$target"}
