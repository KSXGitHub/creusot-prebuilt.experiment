#!/usr/bin/env bash
# shellcheck source-path=SCRIPTDIR
# Put the Creusot source for this release where the build reads it.
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/lib/common.bash"

tool fetch_source "$@"
