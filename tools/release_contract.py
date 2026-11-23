#!/usr/bin/env python3
"""The contract a release commit holds to, checked locally and again in CI.

A release is cut by tagging a commit `X.Y.Z-W`. For that tag to mean anything,
three things have to agree: the tag, the commit message, and the `pkgver` and
`pkgrel` files at that commit. This module is the one place that decides whether
they do. The `commit-msg` and `pre-push` hooks call it so a mismatch is caught
before it reaches the remote, and the deployment workflow calls it again so a tag
pushed from elsewhere cannot skip the check.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path

import commit_message
import release
from commit_message import CommitMessage
from gitcmd import GitError, git_output
from release import ReleaseError

RELEASE_FILES = (release.PKGVER_FILE, release.PKGREL_FILE)


def message_problems(message: CommitMessage, tag: str) -> list[str]:
    """Why this commit message does not announce `tag`, or nothing if it does."""
    problems: list[str] = []
    if message.subject != tag:
        problems.append(f"the subject is {message.subject!r}, but the tag is {tag!r}")
    if message.body:
        problems.append(f"the message has a body, which a release commit may not: {message.body[0]!r}")
    return problems


def files_problems(pkgver: str, pkgrel: str, tag: str) -> list[str]:
    """Why these `pkgver` and `pkgrel` contents do not form `tag`."""
    try:
        identity = release.validate(pkgver.strip(), pkgrel.strip())
    except ReleaseError as error:
        return [str(error)]
    if identity.tag != tag:
        return [f"pkgver and pkgrel form {identity.tag!r}, but the tag is {tag!r}"]
    return []


def report(tag: str, problems: list[str]) -> int:
    if not problems:
        print(f"release-contract: {tag} holds")
        return 0
    print(f"✖ The release contract does not hold for {tag}:", file=sys.stderr)
    for problem in problems:
        print(f"    • {problem}", file=sys.stderr)
    print(
        "\nA commit tagged X.Y.Z-W must carry X.Y.Z-W as its whole message, and\n"
        "the pkgver and pkgrel files at that commit must spell the same pair.",
        file=sys.stderr,
    )
    return 1


def check_commit(tag: str, commit: str, repo: Path) -> list[str]:
    """Check a commit that already exists, by its message and its two files."""
    stored = commit_message.from_stored(git_output(["log", "-1", "--format=%B", commit], cwd=repo))
    problems = message_problems(stored, tag)
    contents: list[str] = []
    for name in RELEASE_FILES:
        try:
            contents.append(git_output(["show", f"{commit}:{name}"], cwd=repo))
        except GitError:
            problems.append(f"{name} does not exist at {commit}")
            return problems
    return problems + files_problems(contents[0], contents[1], tag)


def command_tag(arguments: argparse.Namespace) -> int:
    tag = release.strip_ref_prefix(arguments.ref)
    try:
        release.parse_tag(tag)
    except ReleaseError as error:
        return report(tag, [str(error)])
    return report(tag, check_commit(tag, arguments.commit, arguments.repo))


def command_commit_msg(arguments: argparse.Namespace) -> int:
    """The `commit-msg` hook: judge the message about to be written.

    A commit is a release commit when it changes `pkgver` or `pkgrel`, or when
    its subject already reads as a release tag. Either way the staged files
    decide which tag it claims to be.
    """
    repo: Path = arguments.repo
    message = commit_message.from_file(Path(arguments.message_file))
    subject = message.subject

    changed = git_output(["diff", "--cached", "--name-only", "--diff-filter=M"], cwd=repo).split()
    touches_release_files = any(name in RELEASE_FILES for name in changed)
    subject_reads_as_tag = _parses_as_tag(subject)
    if not touches_release_files and not subject_reads_as_tag:
        return 0

    contents: list[str] = []
    for name in RELEASE_FILES:
        try:
            contents.append(git_output(["show", f":{name}"], cwd=repo))
        except GitError:
            return report(subject, [f"{name} is not in the index"])
    try:
        staged = release.validate(contents[0].strip(), contents[1].strip())
    except ReleaseError as error:
        return report(subject, [str(error)])

    return report(staged.tag, message_problems(message, staged.tag))


def command_pre_push(arguments: argparse.Namespace) -> int:
    """The `pre-push` hook: judge every release-shaped tag in this push.

    git feeds one `<local-ref> <local-sha> <remote-ref> <remote-sha>` line per
    ref. A deletion carries an all-zero local sha and has nothing to verify.
    """
    status = 0
    for line in sys.stdin.read().splitlines():
        fields = line.split()
        if len(fields) < 2:
            continue
        local_ref, local_sha = fields[0], fields[1]
        if not local_ref.startswith("refs/tags/"):
            continue
        tag = release.strip_ref_prefix(local_ref)
        if not _parses_as_tag(tag) or set(local_sha) == {"0"}:
            continue
        status |= report(tag, check_commit(tag, local_sha, arguments.repo))
    return status


def _parses_as_tag(candidate: str) -> bool:
    try:
        release.parse_tag(candidate)
    except ReleaseError:
        return False
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd(), help="the checkout to read")
    subcommands = parser.add_subparsers(dest="command", required=True)

    tag_parser = subcommands.add_parser("tag", help="check a tag against an existing commit")
    tag_parser.add_argument("ref", help="the tag, or the refs/tags/... ref")
    tag_parser.add_argument("commit", nargs="?", default="HEAD", help="the commit the tag points at")
    tag_parser.set_defaults(run=command_tag)

    commit_msg_parser = subcommands.add_parser("commit-msg", help="the commit-msg hook")
    commit_msg_parser.add_argument("message_file")
    commit_msg_parser.set_defaults(run=command_commit_msg)

    pre_push_parser = subcommands.add_parser("pre-push", help="the pre-push hook, reading refs on stdin")
    pre_push_parser.set_defaults(run=command_pre_push)

    arguments = parser.parse_args(argv)
    run: Callable[[argparse.Namespace], int] = arguments.run
    return run(arguments)


if __name__ == "__main__":
    sys.exit(main())
