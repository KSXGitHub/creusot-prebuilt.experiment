#!/usr/bin/env bash
# shellcheck source-path=SCRIPTDIR
# Build Why3 and why3find into $STAGE/why3.
#
# Creusot proves nothing without them, and neither has a binary release:
# upstream installs them by building an opam switch from `creusot-deps.opam`,
# which compiles OCaml, Why3 and why3find from source. The versions come from
# the tag's own `creusot-deps.opam`, so what is built always matches the Creusot
# release it ships beside.
#
# why3 compiles its data directory in and honours neither WHY3DATA nor being
# moved: `why3 --print-datadir` always reports the prefix it was built at. So the
# switch is created at a fixed $WHY3_SWITCH, and the asset has to be unpacked at
# the `_opam` inside it. `ci/package.py` asks the built binary which path that
# is rather than assuming one.
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"

command -v opam >/dev/null || { echo "build-why3: opam not found" >&2; exit 1; }
[ -f "$SRC/creusot-deps.opam" ] || { echo "build-why3: run scripts/fetch-source.sh first" >&2; exit 1; }

SOURCE_DATE_EPOCH=$(source_date_epoch)
export SOURCE_DATE_EPOCH

# A container without user namespaces cannot run opam's bubblewrap sandbox. Set
# OPAM_INIT_FLAGS=--disable-sandboxing there. Leave it unset everywhere else: the
# sandbox is what keeps a package's build from reaching outside its own tree.
read -r -a opam_init_flags <<< "${OPAM_INIT_FLAGS:-}"
opam switch list >/dev/null 2>&1 || opam init --bare -y "${opam_init_flags[@]}"

# `in-creusot-ci` excludes why3-ide, Why3's GTK front end: a headless machine has
# no use for it and its lablgtk3 dependencies need system GTK packages. Set on
# this switch rather than globally, so the rest of opam is left alone.
# `$WHY3_SWITCH/creusot-deps.opam` is written only once the install has
# succeeded, so a switch left half-built by a failed run is rebuilt rather than
# reused. The copy opam itself needs lives in a scratch directory.
marker=$WHY3_SWITCH/creusot-deps.opam
if [ -x "$WHY3_SWITCH/_opam/bin/why3" ] && cmp -s "$SRC/creusot-deps.opam" "$marker"; then
  echo "build-why3: reusing the switch at $WHY3_SWITCH; its creusot-deps.opam already matches"
else
  # Empty the prefix without removing it: on a machine where only root may
  # write to its parent, somebody else created it and gave it to this user.
  mkdir -p "$WHY3_SWITCH" 2>/dev/null || true
  [ -w "$WHY3_SWITCH" ] || { echo "build-why3: $WHY3_SWITCH is not writable; create it and hand it to this user" >&2; exit 1; }
  find "$WHY3_SWITCH" -mindepth 1 -maxdepth 1 -exec rm -rf {} +
  mkdir -p "$WHY3_SWITCH/deps"
  cp "$SRC/creusot-deps.opam" "$WHY3_SWITCH/deps/creusot-deps.opam"
  opam switch create -y --empty "$WHY3_SWITCH"
  opam var in-creusot-ci=true --switch "$WHY3_SWITCH" >/dev/null
  opam install -y --switch "$WHY3_SWITCH" "$WHY3_SWITCH/deps"
  cp "$SRC/creusot-deps.opam" "$marker"
fi

# Keep everything under lib/why3 except what is only needed to *compile* against
# Why3: the `.cmx` / `.cmi` / `.cmt` / `.cmti` interfaces, `.ml` / `.mli` sources
# and `.a` / `.o` / `.cma` archives. That is 131 MB down to 20 MB. Excluding by
# extension rather than selecting `*.cmxs` matters: lib/why3 also holds the
# `why3server` executable, which why3 spawns to run the solvers. Without it every
# solver call hangs for ever, with no error.
#
# `META` and `dune-package` are dropped too. They are ocamlfind and dune metadata
# for compiling against Why3, and nothing here does. They also happen to be the
# only part of this tree that is not reproducible: dune writes a git-describe
# version into META when the package's source tree has git metadata, which
# depends on whether opam had the pin cached as a clone. Excluding them makes two
# from-scratch builds byte-identical.
opam_root=$WHY3_SWITCH/_opam
out=$STAGE/why3
rm -rf "$out"
mkdir -p "$out/bin" "$out/share" "$out/lib"
install -m 755 "$opam_root/bin/why3" "$opam_root/bin/why3find" "$out/bin/"
strip "$out/bin/why3" "$out/bin/why3find"
cp -r "$opam_root/share/why3" "$out/share/"
(cd "$opam_root" && find lib/why3 -type f \
    ! -name '*.cmx' ! -name '*.cmi' ! -name '*.cmt' ! -name '*.cmti' \
    ! -name '*.ml' ! -name '*.mli' ! -name '*.a' ! -name '*.o' ! -name '*.cma' \
    ! -name 'META' ! -name 'dune-package' \
    -print0 | tar --null -cf - -T -) | tar -xf - -C "$out"
# Why3 ships its licence in share/why3/LICENSE; add why3find's, wherever opam put it.
for candidate in "$opam_root"/doc/why3find/LICENSE* "$opam_root"/.opam-switch/sources/why3find/LICENSE*; do
  [ -f "$candidate" ] && cp "$candidate" "$out/LICENSE.why3find" && break
done
[ -f "$out/LICENSE.why3find" ] || { echo "build-why3: why3find's licence is missing from the switch" >&2; exit 1; }

"$out/bin/why3" --version
echo "build-why3: assembled $out, baked for $WHY3_SWITCH"
