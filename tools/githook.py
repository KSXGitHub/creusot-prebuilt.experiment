#!/usr/bin/env python3
"""What the git hooks run.

Every hook in `.githooks/` is a wrapper that names a subcommand here, because
everything they used to do with `grep`, `sed` and `awk` is a function in
`tools/lib/`. The checks run in order and the first failure stops the commit,
which is what the chain of shell scripts did.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from lib import commit_message, layout, release_contract
from lib.commit_checks import CHECKS
from lib.console import say


def commit_msg(repo: Path, message_file: Path) -> int:
    message = commit_message.from_file(message_file)

    # Git rejects an empty message on its own, and a message of nothing but
    # comments reads as empty here too.
    if not message.subject:
        return 0

    for check in CHECKS:
        report = check(message)
        if report is not None:
            say(report)
            return 1

    return release_contract.check_staged_message(repo, message)


def pre_push(repo: Path) -> int:
    return release_contract.check_pushed_refs(repo, sys.stdin.read().splitlines())


def reference_transaction(repo: Path, state: str) -> int:
    # The refs are read whatever the state, because git writes them to this
    # process either way and a hook that left them unread would be writing to a
    # closed pipe.
    return release_contract.check_created_refs(repo, state, sys.stdin.read().splitlines())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=None, help="the checkout to read")
    subcommands = parser.add_subparsers(dest="hook", required=True)

    commit = subcommands.add_parser("commit-msg", help="check the message about to be written")
    commit.add_argument("message_file", type=Path)
    commit.set_defaults(hook="commit-msg")

    subcommands.add_parser("pre-push", help="check the refs being pushed, read on stdin")

    transaction = subcommands.add_parser(
        "reference-transaction", help="check the refs about to be written, read on stdin"
    )
    transaction.add_argument("state", help="prepared, committed or aborted, as git names it")
    transaction.set_defaults(hook="reference-transaction")

    arguments = parser.parse_args(argv)
    repo = arguments.repo if arguments.repo is not None else layout.repository_root()
    if arguments.hook == "commit-msg":
        return commit_msg(repo, arguments.message_file)
    if arguments.hook == "reference-transaction":
        return reference_transaction(repo, arguments.state)
    return pre_push(repo)


if __name__ == "__main__":
    sys.exit(main())
