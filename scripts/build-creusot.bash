#!/usr/bin/env bash
# shellcheck source-path=SCRIPTDIR
# Build the Creusot binaries and the Coma prelude into build/creusot.
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/lib/tool.bash"

tool build_creusot "$@"
