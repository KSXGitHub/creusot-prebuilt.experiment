"""The asset table every other part of the release reads."""

from __future__ import annotations

import unittest

from lib import manifest
from lib.manifest import Arch, Asset, Member, Prefix

TAG = "0.15.0-0"
TARGET = "x86_64-unknown-linux-gnu"


class FileName(unittest.TestCase):
    def test_a_target_asset_is_named_after_the_triple(self) -> None:
        asset = Asset(
            name="tool",
            prefix=Prefix.CREUSOT_DATA_HOME,
            arch=Arch.TARGET,
            summary="",
            members=(Member("creusot/bin/tool", "bin/tool"),),
        )
        self.assertEqual(asset.file_name(TAG, TARGET), f"tool-{TAG}-{TARGET}.tar.gz")

    def test_an_architecture_free_asset_is_named_noarch(self) -> None:
        asset = Asset(
            name="data",
            prefix=Prefix.CREUSOT_DATA_HOME,
            arch=Arch.NOARCH,
            summary="",
            members=(Member("creusot/share", "share"),),
        )
        self.assertEqual(asset.file_name(TAG, TARGET), f"data-{TAG}-noarch.tar.gz")


class AssetByName(unittest.TestCase):
    def test_finds_an_asset_the_table_holds(self) -> None:
        found = manifest.asset_by_name("why3")
        self.assertIsNotNone(found)
        assert found is not None
        self.assertIs(found.prefix, Prefix.WHY3_PREFIX)

    def test_answers_with_nothing_for_a_name_it_does_not_hold(self) -> None:
        self.assertIsNone(manifest.asset_by_name("alt-ergo"))


class TableInvariants(unittest.TestCase):
    """What an edit to the table has to keep true, since one asset is one tool."""

    def test_every_asset_has_its_own_name(self) -> None:
        names = [asset.name for asset in manifest.ASSETS]
        self.assertEqual(sorted(names), sorted(set(names)))

    def test_every_asset_holds_at_least_one_member(self) -> None:
        for asset in manifest.ASSETS:
            with self.subTest(asset.name):
                self.assertTrue(asset.members)

    def test_no_member_is_placed_outside_its_prefix(self) -> None:
        for asset in manifest.ASSETS:
            for member in asset.members:
                with self.subTest(f"{asset.name}:{member.dest}"):
                    self.assertFalse(member.dest.startswith("/"))
                    self.assertNotIn("..", member.dest.split("/"))

    def test_every_asset_says_what_it_holds(self) -> None:
        for asset in manifest.ASSETS:
            with self.subTest(asset.name):
                self.assertTrue(asset.summary.endswith("."))
