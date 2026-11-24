"""The contract a release commit holds to, checked locally and again in CI.

A release is cut by tagging a commit `X.Y.Z-W`. For that tag to mean anything,
three things have to agree: the tag, the commit message, and the `pkgver` and
`pkgrel` files at that commit. This module is the one place that decides whether
they do. The `commit-msg` and `pre-push` hooks call it so a mismatch is caught
before it reaches the remote, and the deployment workflow calls it again so a tag
pushed from elsewhere cannot skip the check.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from pathlib import Path

from . import commit_message, release
from .commit_message import CommitMessage
from .console import say
from .gitcmd import GitError, git_output
from .release import ReleaseError

RELEASE_FILES = (release.PKGVER_FILE, release.PKGREL_FILE)
TAG_PREFIX = "refs/tags/"
PREPARED = "prepared"


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
        say(f"release-contract: {tag} holds")
        return 0
    say(f"✖ The release contract does not hold for {tag}:")
    for problem in problems:
        say(f"    • {problem}")
    say(
        "\nA commit tagged X.Y.Z-W must carry X.Y.Z-W as its whole message, and\n"
        "the pkgver and pkgrel files at that commit must spell the same pair."
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


def check_tag(repo: Path, ref: str, commit: str) -> int:
    """Check a tag against the commit it points at. Used by CI and by `just`."""
    tag = release.strip_ref_prefix(ref)
    try:
        release.parse_tag(tag)
    except ReleaseError as error:
        return report(tag, [str(error)])
    return report(tag, check_commit(tag, commit, repo))


def check_staged_message(repo: Path, message: CommitMessage) -> int:
    """Judge the message a commit is about to be written with.

    A commit is a release commit when it changes `pkgver` or `pkgrel`, or when
    its subject already reads as a release tag. Either way the staged files
    decide which tag it claims to be.
    """
    changed = git_output(["diff", "--cached", "--name-only", "--diff-filter=M"], cwd=repo).split()
    touches_release_files = any(name in RELEASE_FILES for name in changed)
    if not touches_release_files and not parses_as_tag(message.subject):
        return 0

    contents: list[str] = []
    for name in RELEASE_FILES:
        try:
            contents.append(git_output(["show", f":{name}"], cwd=repo))
        except GitError:
            return report(message.subject, [f"{name} is not in the index"])
    try:
        staged = release.validate(contents[0].strip(), contents[1].strip())
    except ReleaseError as error:
        return report(message.subject, [str(error)])

    return report(staged.tag, message_problems(message, staged.tag))


def check_refs(repo: Path, updates: Iterable[tuple[str, str]]) -> int:
    """Judge every release-shaped tag among these `(ref, new sha)` pairs.

    A ref that is not a tag, a tag whose name is not a release identifier, and a
    deletion, whose new sha is all zeroes, each have nothing to verify.
    """
    status = 0
    for ref, new_sha in updates:
        if not ref.startswith(TAG_PREFIX):
            continue
        tag = release.strip_ref_prefix(ref)
        if not parses_as_tag(tag) or set(new_sha) == {"0"}:
            continue
        status |= report(tag, check_commit(tag, new_sha, repo))
    return status


def pushed_updates(lines: Iterable[str]) -> Iterator[tuple[str, str]]:
    """What `pre-push` is fed: `<local-ref> <local-sha> <remote-ref> <remote-sha>`."""
    for line in lines:
        fields = line.split()
        if len(fields) >= 2:
            yield fields[0], fields[1]


def transaction_updates(lines: Iterable[str]) -> Iterator[tuple[str, str]]:
    """What `reference-transaction` is fed: `<old-value> <new-value> <ref>`."""
    for line in lines:
        fields = line.split()
        if len(fields) >= 3:
            yield fields[2], fields[1]


def check_pushed_refs(repo: Path, lines: Iterable[str]) -> int:
    """Judge every release-shaped tag a push would send."""
    return check_refs(repo, pushed_updates(lines))


def check_created_refs(repo: Path, state: str, lines: Iterable[str]) -> int:
    """Judge every release-shaped tag a ref transaction is about to write.

    This is what catches `git tag 0.15.0-9` on a commit that says otherwise,
    which `pre-push` would only catch once the tag was already written. git runs
    it for every ref it updates, in three states, and only a non-zero exit from
    `prepared` stops the update: by `committed` and `aborted` the transaction has
    already been decided.

    A transaction covers the refs a fetch writes as well as the ones a `git tag`
    writes, and git gives the hook the same environment either way, so a tag
    arriving from a remote is held to the same contract. One that does not hold
    fails the whole fetch, which is why the report names the way to take it
    anyway.
    """
    if state != PREPARED:
        return 0
    status = check_refs(repo, transaction_updates(lines))
    if status != 0:
        say(
            "\nIf this tag is arriving from a fetch rather than one you are writing,\n"
            "`git -c core.hooksPath= fetch` takes it without this check."
        )
    return status


def parses_as_tag(candidate: str) -> bool:
    try:
        release.parse_tag(candidate)
    except ReleaseError:
        return False
    return True
