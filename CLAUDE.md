# Instructions for AI agents

This file is what an AI agent reads before changing anything here, and
`AGENTS.md` points at it so that other harnesses pick it up. It is written as
rules addressed to an agent rather than as a contributing guide for people.

This repository builds [Creusot](https://github.com/creusot-rs/creusot) and the
Why3 framework it proves with, and publishes the result as GitHub release
assets. There is no application here: the deliverable is a release, and
everything in the tree exists to produce one or to check that it is correct.

## Where each kind of logic lives

- **`justfile`** is the entry point for every task. A recipe names a script and
  passes it arguments.
- **`scripts/*.sh`** invoke the toolchains. They are the places that run
  `cargo`, `opam`, `rustup`, and `git`, and they hold no decisions beyond the
  conditionals those invocations need. A script reaching for `grep`, `sed` or
  `awk` to take a string apart is a sign the work belongs in `ci/`.
- **`.githooks/*`** are one line each, and call `ci/githook.py`.
- **`ci/*.py`** hold the computation and the decision trees: which file belongs
  to which asset, what makes a release commit valid, how an archive is written
  so that two runs produce the same bytes. They are type-annotated throughout
  and checked by `mypy --strict`.
- **`install.py`** is the consumer's half of `ci/manifest.py`, and is uploaded
  with each release. It reads `release.json` rather than repeating what the
  manifest says.

A new piece of logic goes wherever it already fits. Shell that grows a
decision tree belongs in `ci/`; Python that only spawns one program belongs in a
script.

## Taking a string apart

Where a string has to be parsed, the parse is built from the `take_*` functions
in `ci/take.py`. Each is offered a string and either consumes a prefix and hands
back the remainder, or declines; a parse that owns its input finishes by
requiring the remainder to be empty. `ci/github_text.py` and `ci/opam.py` are
written that way.

A regex is right for an anchored, total check. `ci/release.py` uses two, for
`pkgver` and `pkgrel`, and they should stay. A regex is wrong for a scan,
because what a scan gets wrong is boundaries and repetition, which is exactly
what a regex hides. The two scanners here replaced regexes that reported two of
three bare references and read a correctly escaped mention as a bare one, and
neither fault was visible by reading.

Where the standard library already parses the format, use it rather than writing
a parser. `rust-toolchain` is TOML and goes through `tomllib`; `release.json`
goes through `json`. opam's file format has no reader in the standard library,
which is the reason `ci/opam.py` exists.

## The asset table has one definition

`ci/manifest.py` says which built file goes into which asset and where that
asset unpacks. `ci/package.py` writes `release.json` from it, `ci/release_notes.py`
renders the release body from that, and `install.py` reads it back. Adding a
tool means editing the manifest and nothing else.

So do not write the asset list into `README.md`, into a workflow, or into
`install.py`. A second copy is a second thing to forget.

## Reproducibility depends on where the build runs

A compiler writes the paths it was given into what it produces, so the
directories the build uses are inputs to it:

- `scripts/common.sh` defaults `BUILD_ROOT` to `/var/tmp/creusot-prebuilt`.
  `cargo-creusot` falls back to its own `CARGO_MANIFEST_DIR` when
  `CREUSOT_PATH` is unset, so the build directory ends up in the binary as a
  literal string.
- `scripts/common.sh` defaults `WHY3_SWITCH` to `/opt/creusot-why3`. `why3`
  compiles its data directory in and honours neither `WHY3DATA` nor being
  moved. `why3 --print-datadir` reports the prefix it was built at, which is
  the `_opam` inside `WHY3_SWITCH`, and is why its asset has to be unpacked
  there. `ci/package.py` asks the built binary for that path and records it in
  `release.json`, so nothing else has to spell it.
- `scripts/build-creusot.sh` remaps three directories out of the Rust build:
  the source, the cargo home and the rustup home. The last one matters because
  `creusot-rustc` is compiled against `rustc-dev`, whose sources sit under the
  toolchain, and without that remapping a build under `/root` and a build under
  `/home/runner` produce different bytes.

Changing any of these changes the published checksums, so a change to one is a
change to the release rather than to the build script.

## Cutting a release

1. Edit `pkgver` to the upstream Creusot version, or `pkgrel` when the same
   version is rebuilt with a packaging change. `pkgrel` counts from `0` and
   restarts there whenever `pkgver` moves.
2. Commit with the release identifier as the whole message, which `just version`
   prints. The `commit-msg` hook rejects anything else for such a commit.
3. Tag the commit with the same identifier and push both.

The `pre-push` hook and the first job of the deployment workflow both run
`ci/release_contract.py`, so a tag that disagrees with the files it points at
never reaches a build.

Install the hooks on a fresh checkout with `just install-git-hooks`.

## Validating a change

`just check` runs the checks that need no build: `mypy`, `ruff`, and
`shellcheck`. Run it before every commit.

`just build` runs the whole pipeline, which takes tens of minutes on a cold
machine, mostly in the opam switch that compiles OCaml and Why3 from source.
`just check-packaging` and `just smoke-test` are the checks that run on its
output. The `Test` workflow runs all of it on a pull request, on `master` and on
demand. Its `paths-ignore` skips a prose-only commit pushed to `master`, and a
pull request whose whole diff is prose, but not a prose commit pushed to a pull
request that also changes code: there the filter reads the whole diff. Such a
push builds off the cache in about two minutes.

A build script that is being executed must not be edited. Bash reads a script
incrementally and seeks back to a byte offset between commands, so rewriting the
file under a running build makes it resume in the middle of a line.

## Writing

These conventions apply to every doc comment, script comment, commit message
and markdown file here. They are written down because an agent left to itself
produces prose that is long, obvious and unverifiable.

### Do not write documentation that restates the code

Prose that duplicates a fact the code already states is unverified by
construction: nothing fails when the code changes and the prose does not. Before
writing such a sentence, ask what would make it go stale, and prefer the form
that cannot.

- **A count over a list that can grow is a second copy of it.** "The release
  holds six assets" goes stale the moment a tool is added. Write "The release
  holds one asset per tool".
- **Prefer a greppable predicate to a hand-maintained list.** "Every script that
  sources `common.sh`" stays true; a list of script names does not.
- **State a fact in exactly one place.** Paths, defaults and asset names have one
  home; everything else points at it.
- **If a passage exists only to restate the code beneath it, delete it.** Length
  is not thoroughness.

### Say what it does, not what it resembles

A metaphor borrowed from outside software states nothing the reader can check.
"The pinned prefix is load-bearing" claims that changing it breaks something
without saying what. Name the mechanism instead: "`why3` compiles the prefix in,
so a copy at another path reads a theory directory that is not there".

The shapes to avoid are a metaphor from another field ("papers over", "baked
in"), an unnamed standard ("earns its keep", "worth the complexity"),
anthropomorphism ("opam wants a directory"), and a vogue phrase ("low-hanging
fruit", "moves the needle"). Software's own vocabulary is not the fault: pass,
walk, hook, cache, prefix and driver are terms, not figures.

Do not use an em dash to join two clauses. It hides loose phrasing that a
rewrite would expose. Restructure the sentence so each clause stands on its own
rather than swapping the dash for another mark.

### Repeat the word; do not vary it

A synonym signals a distinction, so where there is none it sends the reader
looking for one. The same thing is called the same thing every time it comes up.
Spell a value the way the code spells it: the manifest says `prefix`, so the
prose says prefix rather than root, base or destination.

### Every passage must read on its own

A sentence that takes its meaning from a neighbouring one breaks when anything
is inserted between them, and nothing fails when it does. The reader arrives
from a `grep` hit or a diff hunk, not in writing order.

- **A positional reference** such as "the script above" points at the wrong thing
  once an item moves. Name it instead.
- **A dangling comparative** such as a bare "likewise" or "the same", whose
  antecedent is in another passage, costs less to restate than to chase.

A back-reference inside the same passage is not the fault, and neither is prose
introducing what immediately follows.

### Shipped docs address the consumer, not the contributor

`README.md` and the release notes are read by somebody who has downloaded a
release and never cloned this repository. They may name only what that reader
can reach: an asset, a tool, a command, an upstream project.

A heading may switch audience where the reader has to clone to go further, which
is what `README.md` does for building and for reproducing a release. Outside
such a section, a justfile recipe, a script in `scripts/` and a file in `ci/`
are all things the reader does not have.

Everything else is contributor-only and may say whatever is useful: this guide,
the comments in the scripts, and the docstrings in `ci/`.

### Re-read new prose before committing

Prose that breaks these conventions still passes `just check`. You are the only
check it has, and writing a passage is a separate pass from checking one. Before
committing, re-read every comment, docstring and markdown paragraph the diff
touches against the conventions that govern it.

## Commit messages

Every commit follows
[Conventional Commits](https://www.conventionalcommits.org/): a
`type(scope): subject` header with the type drawn from the usual set (`feat`,
`fix`, `docs`, `chore`, `ci`, `refactor`, `style`, `build`, `test`, `perf`), an
optional scope in parentheses, and a `!` after the type or scope for a breaking
change.

The single exception is a release commit, whose message is the release
identifier alone.

The subject is one line of at most 72 characters. GitHub truncates a longer one
in its web UI and folds the overflow into the body, so the commit reads as a
mangled title and body. Move anything that does not fit into the body, after a
blank line. `CREUSOT_PREBUILT_ALLOW_LONG_SUBJECT=true` skips the length check
for one commit when a longer subject is genuinely warranted.

### Issue and pull-request references

Never write a bare `#NNN`. A reference is bare when a `#` followed by digits is
not immediately preceded by an ASCII word character, which is the form GitHub
autolinks against this repository. Write
`KSXGitHub/creusot-prebuilt.experiment#123` for this repository, `owner/repo#123`
for another, or the absolute URL. To enumerate list items, number them without
`#`, since "`#1`" otherwise autolinks as issue 1.

### `@handle` mentions

Never write a bare `@handle`. Outside backticks GitHub autolinks it as a user or
team mention, which pings that account again on every commit, comment and
rebase that carries the message. Wrap it in backticks. A genuinely intended
mention belongs in the pull request or issue body.

The `commit-msg` hook rejects both shapes.

## Symlinks

This file is the authoritative copy. It is also exposed under another name so
that other agent harnesses pick it up:

- `AGENTS.md`, a symlink to `CLAUDE.md`.

Edit `CLAUDE.md` only; the symlink follows.
