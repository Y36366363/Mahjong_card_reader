from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from game import MahjongGame
from simulate_desktop_game import SimulatedDesktopPlayer


class SimulatedDesktopPlayerTests(unittest.TestCase):
    def test_discard_reuses_current_hint_report(self) -> None:
        game = MahjongGame(interactive=True, assist_mode="hint")
        game.players[0].hand = "1m 2m 3m 4m 5m 6m 1p 2p 3p 1s 2s 3s E E".split()
        game.last_hint_hand = tuple(game.players[0].hand)
        game.last_hint_report = {"chosen": "E"}
        player = SimulatedDesktopPlayer(game)
        with patch.object(game, "advanced_discard_report") as analyze:
            self.assertEqual(player("Discard tile: "), "E")
        analyze.assert_not_called()

    def test_complete_prompt_policy_covers_discards_wins_calls_and_continue(self) -> None:
        game = Mock()
        game.last_chi_options = [["1m", "2m", "3m"]]
        game.last_hint_report = None
        game.advanced_discard_report.return_value = {"chosen": "9p"}
        player = SimulatedDesktopPlayer(game, accept_calls=True)
        self.assertEqual(player("Discard tile (or index): "), "9p")
        self.assertEqual(player("Ron on 4m? [Y/n] "), "y")
        self.assertEqual(player("Declare riichi? [y/N] "), "y")
        self.assertEqual(player("Pon E? [y/N] "), "y")
        self.assertEqual(player("Choose chi: "), "1")
        self.assertEqual(player("Press Enter to continue"), "")


if __name__ == "__main__":
    unittest.main()
