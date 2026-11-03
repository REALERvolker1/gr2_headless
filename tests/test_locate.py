"""Discovery regressions for the machine-specific Steam paths."""

from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from scripts import locate
from scripts.lab import Config


class LocateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name)

    def make_game(self, library: Path) -> Path:
        binary = library / "steamapps/common" / locate.GAME / locate.BINARY
        binary.parent.mkdir(parents=True)
        binary.write_bytes(b"shipping executable")
        (library / "steamapps/compatdata" / locate.APP_ID).mkdir(parents=True)
        return library / "steamapps/common" / locate.GAME

    def test_discovers_game_in_secondary_library(self) -> None:
        steam = self.home / ".local/share/Steam"
        (steam / "steamapps").mkdir(parents=True)
        library = self.home / "games"
        game = self.make_game(library)
        (steam / "steamapps/libraryfolders.vdf").write_text(
            f'"libraryfolders"\n{{\n\t"0"\n\t{{\n\t\t"path"\t\t"{library}"\n\t}}\n}}\n'
        )
        proton = steam / "compatibilitytools.d/Proton-GE/proton"
        proton.parent.mkdir(parents=True)
        proton.write_bytes(b"")

        config = locate.discover(self.home, state=self.home / "state")

        self.assertEqual(config.game, game)
        self.assertEqual(config.canonical_prefix, library / "steamapps/compatdata/2144740")
        self.assertEqual(config.seed_prefix, config.canonical_prefix)
        self.assertEqual(config.steam, steam.resolve())
        self.assertEqual(config.proton, proton)
        self.assertEqual(config.game_sha256, hashlib.sha256(b"shipping executable").hexdigest())

    def test_finds_flatpak_steam_root(self) -> None:
        flatpak = self.home / ".var/app/com.valvesoftware.Steam/data/Steam"
        flatpak.mkdir(parents=True)

        self.assertIn(flatpak.resolve(), locate.steam_roots(self.home))

    def test_unqualified_build_clears_the_hash(self) -> None:
        config = Config(
            self.home / "game",
            self.home / "proton",
            self.home / "seed",
            self.home / "canonical",
            self.home / "steam",
            self.home / "state",
            "a" * 64,
        )

        self.assertEqual(locate.qualify(config, "a" * 64).game_sha256, "a" * 64)
        self.assertEqual(locate.qualify(config, "b" * 64).game_sha256, "")


if __name__ == "__main__":
    unittest.main()
