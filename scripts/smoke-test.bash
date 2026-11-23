#!/usr/bin/env bash
# shellcheck source-path=SCRIPTDIR
# Install dist/ into a scratch directory and run every tool.
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/lib/tool.bash"

tool smoke_test "$@"
