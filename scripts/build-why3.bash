#!/usr/bin/env bash
# shellcheck source-path=SCRIPTDIR
# Build Why3 and why3find into build/why3.
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/lib/tool.bash"

tool build_why3 "$@"
