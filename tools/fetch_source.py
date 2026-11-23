"""Put the Creusot source for this release where the build reads it.

The checkout is the upstream release tag, shallow, and is left alone when it is
already at that tag so that a rebuild does not refetch it.
"""

from __future__ import annotations

import shutil
import sys

import layout
from gitcmd import GitError, git_output
from run import CommandError, run


def main() -> int:
    plan = layout.read()
    tag = plan.release.upstream_tag
    source = plan.source

    at_tag = ""
    if (source / ".git").exists():
        try:
            at_tag = git_output(["describe", "--tags", "--exact-match"], cwd=source).strip()
        except GitError:
            at_tag = ""

    if at_tag == tag:
        print(f"fetch-source: {source} is already at {tag}")
    else:
        shutil.rmtree(source, ignore_errors=True)
        source.parent.mkdir(parents=True, exist_ok=True)
        run(["git", "clone", "--depth", "1", "--branch", tag, plan.creusot_repo, source])

    commit = git_output(["rev-parse", "HEAD"], cwd=source).strip()
    print(f"fetch-source: {tag} is commit {commit}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (CommandError, GitError) as error:
        print(f"fetch-source: {error}", file=sys.stderr)
        sys.exit(1)
