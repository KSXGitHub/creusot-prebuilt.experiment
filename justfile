set shell := ["bash", "-euo", "pipefail", "-c"]

python := env("PYTHON", "python3")
pkgver := trim(shell("cat pkgver"))
pkgrel := trim(shell("cat pkgrel"))

# List the recipes
default:
    @just --list

# Print the release identifier, which is also the tag and the release name
version:
    @echo "{{ pkgver }}-{{ pkgrel }}"

# Point git at the hooks in .githooks
install-git-hooks:
    git config core.hooksPath .githooks

# Stop git using the hooks in .githooks
uninstall-git-hooks:
    git config --unset core.hooksPath 2>/dev/null || true

# Check that a tag, the commit it points at, and pkgver/pkgrel all agree
verify-release ref commit="HEAD":
    {{ python }} tools/release_contract.py tag '{{ ref }}' '{{ commit }}'

# Put the pinned Creusot source where the build scripts read it
source:
    ./scripts/fetch-source.sh

# Build the Creusot binaries and the Coma prelude into build/creusot
build-creusot target="":
    ./scripts/build-creusot.sh {{ target }}

# Build Why3 and why3find into build/why3
build-why3:
    ./scripts/build-why3.sh

# Slice the build tree into one archive per tool under dist/
package target="":
    ./scripts/package.sh {{ target }}

# Everything: fetch the source, build both halves, and write the archives
build target="": source (build-creusot target) build-why3 (package target)

# Slice the build tree a second time and check the archives come out identical
check-packaging target="":
    ./scripts/check-packaging.sh {{ target }}

# Install dist/ into a scratch directory and run every tool it put there
smoke-test:
    ./scripts/smoke-test.sh

# Check the types and the lints of the Python
check-python:
    {{ python }} -m mypy
    {{ python }} -m ruff check
    {{ python }} -m ruff format --check

# Apply what ruff can fix, then reformat
fix-python:
    {{ python }} -m ruff check --fix
    {{ python }} -m ruff format

# Check the shell scripts and the git hooks
check-shell:
    shellcheck -x scripts/*.sh .githooks/*

# Every check that does not need a build
check: check-python check-shell

# Remove the build tree and the archives, leaving the source checkout alone
clean:
    rm -rf build dist
