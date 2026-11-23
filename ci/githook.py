"""What the git hooks run.

`.githooks/commit-msg` and `.githooks/pre-push` are one line each, because
everything they used to do with `grep`, `sed` and `awk` is a function here. The
checks run in order and the first failure stops the commit, which is what the
chain of shell scripts did.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path

import commit_message
import release_contract
from commit_checks import CHECKS


def command_commit_msg(arguments: argparse.Namespace) -> int:
    message = commit_message.from_file(Path(arguments.message_file))

    # Git rejects an empty message on its own, and a message of nothing but
    # comments reads as empty here too.
    if not message.subject:
        return 0

    for check in CHECKS:
        report = check(message)
        if report is not None:
            print(report, file=sys.stderr)
            return 1

    return release_contract.command_commit_msg(arguments)


def command_pre_push(arguments: argparse.Namespace) -> int:
    return release_contract.command_pre_push(arguments)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd(), help="the checkout to read")
    subcommands = parser.add_subparsers(dest="hook", required=True)

    commit_msg = subcommands.add_parser("commit-msg", help="check the message about to be written")
    commit_msg.add_argument("message_file")
    commit_msg.set_defaults(run=command_commit_msg)

    pre_push = subcommands.add_parser("pre-push", help="check the refs being pushed, read on stdin")
    pre_push.set_defaults(run=command_pre_push)

    arguments = parser.parse_args(argv)
    run: Callable[[argparse.Namespace], int] = arguments.run
    return run(arguments)


if __name__ == "__main__":
    sys.exit(main())
