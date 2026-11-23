# shellcheck shell=bash
# Sourced by every script in scripts/. It decides nothing about the build: the
# layout, the parses and the decisions live in tools/, and these scripts exist
# so that each task has a name you can run by hand as well as through `just`.

REPO_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
export REPO_ROOT

# Hand the arguments to a module in tools/ and become it.
tool() {
  local module=$1
  shift
  exec python3 "$REPO_ROOT/tools/$module.py" "$@"
}
