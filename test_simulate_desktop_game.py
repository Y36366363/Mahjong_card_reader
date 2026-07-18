from __future__ import annotations

import unittest
from unittest.mock import Mock

from simulate_desktop_game import SimulatedDesktopPlayer


class SimulatedDesktopPlayerTests(unittest.TestCase):
    def test_complete_prompt_policy_covers_discards_wins_calls_and_continue(self) -> None:
        game = Mock()
        game.last_chi_options = [["1m", "2m", "3m"]]
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
