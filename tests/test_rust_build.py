"""What the Rust half of the build works out before cargo runs."""

from __future__ import annotations

import os
import unittest
from pathlib import Path
from unittest import mock

from lib import rust_build

HOST = "x86_64-unknown-linux-gnu"
OTHER = "aarch64-unknown-linux-gnu"


class PackagesFor(unittest.TestCase):
    def test_the_host_gets_the_rustc_driver_too(self) -> None:
        self.assertIn("creusot-rustc", rust_build.packages_for(HOST, HOST))

    def test_another_target_does_not(self) -> None:
        packages = rust_build.packages_for(OTHER, HOST)
        self.assertNotIn("creusot-rustc", packages)
        self.assertIn("cargo-creusot", packages)


class RemapFlags(unittest.TestCase):
    def test_remaps_the_source_the_cargo_home_and_the_rustup_home(self) -> None:
        with mock.patch.dict(os.environ, {"CARGO_HOME": "/ch", "RUSTUP_HOME": "/rh"}):
            flags = rust_build.remap_flags(Path("/src"))
        self.assertEqual(
            flags.split(),
            [
                "--remap-path-prefix=/src=/build/creusot",
                "--remap-path-prefix=/ch=/build/cargo",
                "--remap-path-prefix=/rh=/build/rustup",
            ],
        )

    def test_falls_back_to_the_directories_under_the_home(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            flags = rust_build.remap_flags(Path("/src"))
        self.assertIn(f"--remap-path-prefix={Path.home() / '.cargo'}=/build/cargo", flags)
        self.assertIn(f"--remap-path-prefix={Path.home() / '.rustup'}=/build/rustup", flags)
