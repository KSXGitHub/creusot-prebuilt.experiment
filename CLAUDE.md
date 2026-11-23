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
  conditionals those invocations need.
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

## The asset table has one definition

`ci/manifest.py` says which built file goes into which asset and where that
asset unpacks. `ci/package.py` writes `release.json` from it, `ci/release_notes.py`
renders the release body from that, and `install.py` reads it back. Adding a
tool means editing the manifest and nothing else.

So do not write the asset list into `README.md`, into a workflow, or into
`install.py`. A second copy is a second thing to forget.

## Reproducibility depends on two fixed paths

`scripts/common.sh` defaults `BUILD_ROOT` to `/var/tmp/creusot-prebuilt` and
`WHY3_SWITCH` to `/opt/creusot-why3`. Neither is a convenience:

- A Rust binary records the directory it was compiled in. `cargo-creusot` falls
  back to its own `CARGO_MANIFEST_DIR` when `CREUSOT_PATH` is unset, so the
  build directory ends up in the binary as a literal string.
- `why3` compiles its data directory in and honours neither `WHY3DATA` nor
  being moved. `why3 --print-datadir` reports the prefix it was built at, which
  is the `_opam` inside `WHY3_SWITCH`, and is why its asset has to be unpacked
  there. `ci/package.py` asks the built binary for that path and records it in
  `release.json`, so nothing else has to spell it.

Changing either default changes the published checksums. A change to either one
is a change to the release, not to the build script.

## Cutting a release

1. Edit `pkgver` to the upstream Creusot version, or `pkgrel` when the same
   version is rebuilt with a packaging change. `pkgrel` restarts at `1` whenever
   `pkgver` moves.
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
`just check-packaging` and `just smoke-test` are the two checks that run on its
output, and the `Test` workflow runs all of this on every branch.

A build script that is being executed must not be edited. Bash reads a script
incrementally and seeks back to a byte offset between commands, so rewriting the
file under a running build makes it resume in the middle of a line.

## Writing

These conventions come from
[KSXGitHub/perfectionist](https://github.com/KSXGitHub/perfectionist), which
arrived at them while reviewing prose that machines had written. They apply to
every doc comment, script comment, commit message, and markdown file here, and
an agent is the reason they are written down: left alone, it produces prose that
is long, obvious and unverifiable.

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
