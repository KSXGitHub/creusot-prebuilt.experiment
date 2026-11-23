#!/usr/bin/env bash
# shellcheck source-path=SCRIPTDIR
# Slice the build tree into one archive per tool under dist/.
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/lib/tool.bash"

tool package "$@"
