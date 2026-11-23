#!/usr/bin/env python3
"""Slice the build tree into one archive per tool, then checksum and describe them.

Every archive is written byte-for-byte deterministically: members are sorted,
ownership is dropped, permissions are reduced to executable or not, every mtime
is the upstream commit date, and gzip stores no name or timestamp of its own. So
an archive does not record when or in which directory it was written, and what
the compilers produced is all that is left to differ.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
from dataclasses import dataclass
from pathlib import Path

import layout
import manifest
import opam
import release
import rust_build
import rust_toolchain
from gitcmd import git_output
from manifest import Asset, Member


@dataclass(frozen=True)
class BuildFacts:
    """What the build tree and its source checkout say about this build."""

    target: str
    rust_channel: str
    creusot_commit: str
    source_date_epoch: int
    why3_prefix: str
    opam_pins: dict[str, str]


def read_why3_prefix(build: Path) -> str:
    """Ask the built `why3` which prefix it was compiled for.

    It reports its data directory, and honours neither `WHY3DATA` nor being
    moved, so this is the one path its asset can be unpacked at.
    """
    why3 = build / "why3" / "bin" / "why3"
    datadir = subprocess.run([str(why3), "--print-datadir"], capture_output=True, text=True, check=True).stdout.strip()
    suffix = "/share/why3"
    if not datadir.endswith(suffix):
        raise SystemExit(f"package: {why3} reports an unexpected data directory {datadir!r}")
    return datadir[: -len(suffix)]


def collect_facts(source: Path, build: Path, target: str) -> BuildFacts:
    return BuildFacts(
        target=target,
        rust_channel=rust_toolchain.read(source).channel,
        creusot_commit=git_output(["rev-parse", "HEAD"], cwd=source).strip(),
        source_date_epoch=int(git_output(["log", "-1", "--format=%ct"], cwd=source).strip()),
        why3_prefix=read_why3_prefix(build),
        opam_pins=opam.read_pins(source),
    )


def stage_member(build: Path, stage: Path, member: Member, channel: str) -> None:
    source = build / member.source
    destination = stage / member.dest.format(channel=channel)
    if not source.exists():
        raise SystemExit(f"package: the build tree has no {member.source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.is_dir():
        shutil.copytree(source, destination, symlinks=True)
    else:
        shutil.copy2(source, destination, follow_symlinks=False)


def archive_entries(stage: Path) -> list[tuple[str, Path]]:
    """Every path in the staging tree, directories included, sorted by name."""
    entries: list[tuple[str, Path]] = []
    for path in stage.rglob("*"):
        entries.append((path.relative_to(stage).as_posix(), path))
    entries.sort(key=lambda entry: entry[0])
    return entries


def write_archive(stage: Path, destination: Path, epoch: int) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as raw:
        # `filename=""` and `mtime=0` keep the gzip header free of anything that
        # varies between runs.
        with gzip.GzipFile(filename="", mode="wb", compresslevel=9, fileobj=raw, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w", format=tarfile.GNU_FORMAT) as archive:
                for name, path in archive_entries(stage):
                    info = archive.gettarinfo(str(path), arcname=name)
                    info.uid = 0
                    info.gid = 0
                    info.uname = ""
                    info.gname = ""
                    info.mtime = epoch
                    if info.isdir():
                        info.mode = 0o755
                    elif info.issym():
                        info.mode = 0o777
                    else:
                        info.mode = 0o755 if info.mode & 0o100 else 0o644
                    if info.isreg():
                        with path.open("rb") as content:
                            archive.addfile(info, content)
                    else:
                        archive.addfile(info)
    os.utime(destination, (epoch, epoch))


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def build_asset(
    asset: Asset, build: Path, work: Path, dist: Path, identity: release.Release, facts: BuildFacts
) -> dict[str, object]:
    stage = work / asset.name
    shutil.rmtree(stage, ignore_errors=True)
    stage.mkdir(parents=True)
    for member in asset.members:
        stage_member(build, stage, member, facts.rust_channel)
    file_name = asset.file_name(identity.tag, facts.target)
    archive = dist / file_name
    write_archive(stage, archive, facts.source_date_epoch)
    return {
        "name": asset.name,
        "file": file_name,
        "prefix": asset.prefix.value,
        "arch": asset.arch.value,
        "summary": asset.summary,
        "size": archive.stat().st_size,
        "sha256": sha256_of(archive),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    # Every path defaults to what `tools/layout.py` says, so the usual call
    # takes no arguments at all.
    parser.add_argument("--repo", type=Path, default=None, help="the checkout holding pkgver and pkgrel")
    parser.add_argument("--build", type=Path, default=None, help="the assembled build tree")
    parser.add_argument("--dist", type=Path, default=None, help="where the archives are written")
    parser.add_argument("--source", type=Path, default=None, help="the Creusot checkout the build came from")
    parser.add_argument("--target", default=None, help="the target triple (default: this host's)")
    arguments = parser.parse_args(argv)

    plan = layout.read(arguments.repo)
    build: Path = arguments.build if arguments.build is not None else plan.stage
    dist: Path = arguments.dist if arguments.dist is not None else plan.dist
    source: Path = arguments.source if arguments.source is not None else plan.source

    identity = plan.release
    facts = collect_facts(source, build, arguments.target or rust_build.host_triple())

    shutil.rmtree(dist, ignore_errors=True)
    dist.mkdir(parents=True)
    work = dist / ".stage"
    work.mkdir()

    described = [build_asset(asset, build, work, dist, identity, facts) for asset in manifest.ASSETS]
    shutil.rmtree(work)

    # The installer is uploaded beside the archives, so that a consumer who has
    # the release has everything needed to read it. Copying rather than
    # preserving the checkout's own timestamp keeps dist/ a function of the
    # release alone.
    installer = dist / manifest.INSTALLER
    shutil.copyfile(plan.repo / manifest.INSTALLER, installer)
    installer.chmod(0o755)
    os.utime(installer, (facts.source_date_epoch, facts.source_date_epoch))

    uploaded: list[dict[str, object]] = [
        *described,
        {"sha256": sha256_of(installer), "file": manifest.INSTALLER},
    ]
    checksums = "".join(f"{entry['sha256']}  {entry['file']}\n" for entry in uploaded)
    (dist / manifest.CHECKSUMS).write_text(checksums, encoding="utf-8")

    metadata: dict[str, object] = {
        "pkgver": identity.pkgver,
        "pkgrel": identity.pkgrel,
        "tag": identity.tag,
        "target": facts.target,
        "creusot_tag": identity.upstream_tag,
        "creusot_commit": facts.creusot_commit,
        "rust_channel": facts.rust_channel,
        "opam_pins": facts.opam_pins,
        "source_date_epoch": facts.source_date_epoch,
        "why3_prefix": facts.why3_prefix,
        "installer": manifest.INSTALLER,
        "assets": described,
    }
    (dist / manifest.RELEASE_METADATA).write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")

    for entry in described:
        print(f"{entry['sha256']}  {entry['file']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
