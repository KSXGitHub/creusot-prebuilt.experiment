# shellcheck shell=bash
# Sourced, not executed. Defines one function and nothing else.

# Hand the arguments to a command in tools/ and become it. `python3` is named
# rather than relying on the module's executable bit, so the interpreter is
# explicit and a checkout that dropped the mode still works.
tool() {
  local module=$1
  shift
  local root
  root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
  exec python3 "$root/tools/$module.py" "$@"
}
