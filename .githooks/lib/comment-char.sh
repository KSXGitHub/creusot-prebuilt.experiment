# Shared git-hook helper. Sourced, not executed: it defines a function and sets
# no `set -euo pipefail` of its own (the sourcing script owns that).

# Echo the effective comment char. Honour `core.commentChar` (default `#`) so a
# user with a non-default comment char does not have template comment lines leak
# through, which would let a malformed release commit slip past the subject
# checks and make the bare-reference scan read lines it should skip. Fall back to
# `#` on unset, `auto`, or any value longer than one character.
git_comment_char() {
  local cc
  cc=$(git config --get core.commentChar 2>/dev/null || true)
  case "$cc" in
    '') cc='#' ;;
    ?) ;;
    *) cc='#' ;;
  esac
  printf '%s' "$cc"
}
