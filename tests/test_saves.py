"""Regressions for the canonical-save boundary, independent of the game."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

from scripts import lab


class SaveIsolationTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = lab.ROOT / ".work/tests"
        directory.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=directory)
        self.addCleanup(self.temporary.cleanup)
        root = Path(self.temporary.name)
        self.config = lab.Config(
            root / "game",
            root / "proton",
            root / "seed",
            root / "canonical",
            root / "steam",
            root / "state",
            "0" * 64,
        )
        self.config.state.mkdir()
        self.original = self.config.canonical_prefix / lab.SAVE / "SaveGames"
        self.original.mkdir(parents=True)
        (self.original / "campaign.sav").write_bytes(b"100 percent campaign")
        (self.config.prefix / lab.SAVE).parent.mkdir(parents=True)

    def test_experiment_save_write_is_disposable(self) -> None:
        with patch.object(lab, "check_stopped"):
            lab.reset_saves(self.config)
            copied = self.config.prefix / lab.SAVE / "SaveGames/campaign.sav"
            copied.write_bytes(b"experiment")
            lab.verify(self.config)
            lab.reset_saves(self.config)
        self.assertEqual(copied.read_bytes(), b"100 percent campaign")
        self.assertEqual((self.original / "campaign.sav").read_bytes(), copied.read_bytes())

    def test_save_junction_into_canonical_prefix_is_rejected(self) -> None:
        destination = self.config.prefix / lab.SAVE
        destination.symlink_to(self.original.parent, target_is_directory=True)
        with patch.object(lab, "check_stopped"), self.assertRaisesRegex(RuntimeError, "outside"):
            lab.reset_saves(self.config)
        self.assertEqual((self.original / "campaign.sav").read_bytes(), b"100 percent campaign")

    def test_canonical_change_blocks_refreshing_the_baseline(self) -> None:
        with patch.object(lab, "check_stopped"):
            lab.reset_saves(self.config)
            before = (self.config.state / "canonical-before.json").read_bytes()
            (self.original / "campaign.sav").write_bytes(b"outside writer")
            with self.assertRaisesRegex(RuntimeError, "hashes changed"):
                lab.reset_saves(self.config)
        self.assertEqual((self.config.state / "canonical-before.json").read_bytes(), before)

    def test_failed_collected_game_unit_does_not_leave_display_running(self) -> None:
        commands: list[list[str]] = []

        def control(command: list[str], **options: object) -> CompletedProcess[str]:
            commands.append(command)
            state = "not-found" if "gr2-groundtruth-game" in command else "loaded"
            return CompletedProcess(command, 0, stdout=state + "\n")

        with (
            patch.object(lab, "run", side_effect=control),
            patch("scripts.lab.subprocess.run"),
            patch.object(lab, "verify") as verify,
        ):
            lab.stop(self.config)
        self.assertIn(["systemctl", "--user", "stop", "gr2-groundtruth"], commands)
        verify.assert_called_once_with(self.config)


if __name__ == "__main__":
    unittest.main()
