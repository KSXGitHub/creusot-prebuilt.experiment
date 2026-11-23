#!/usr/bin/env bash
# shellcheck source-path=SCRIPTDIR
# Slice the build tree again and check the archives come out identical.
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/lib/common.bash"

tool check_packaging "$@"
