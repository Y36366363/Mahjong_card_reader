from __future__ import annotations

import random
import unittest

from game import MahjongGame
from shanten import shanten_standard, shanten_standard_draw_state
from tiles import index_to_tile, tiles_to_counts


class AdvancedAITests(unittest.TestCase):
    def test_ai_levels_are_explicit_and_validated(self) -> None:
        game = MahjongGame(ai_levels=["simple", "advanced", "simple", "advanced"])
        self.assertEqual([p.ai_level for p in game.players], ["simple", "advanced", "simple", "advanced"])
        with self.assertRaises(ValueError):
            MahjongGame(ai_levels=["advanced"])

    def test_fast_draw_state_matches_full_ukeire_check(self) -> None:
        rng = random.Random(73)
        wall = [index_to_tile(i) for i in range(34) for _ in range(4)]
        for _ in range(8):
            rng.shuffle(wall)
            counts = tiles_to_counts(wall[:13])
            current = shanten_standard(counts)
            slow: set[int] = set()
            fast: set[int] = set()
            for i in range(34):
                if counts[i] >= 4:
                    continue
                drawn = counts.copy(); drawn[i] += 1
                if shanten_standard(drawn) < current:
                    slow.add(i)
                if shanten_standard_draw_state(drawn) < current:
                    fast.add(i)
            self.assertEqual(slow, fast)

    def test_genbutsu_is_safer_against_riichi(self) -> None:
        game = MahjongGame(ai_levels=["advanced"] * 4)
        game.players[1].riichi = True
        game.players[1].river = ["5m"]
        visible = game._visible_counts(0)
        self.assertLess(
            game._defense_risk(0, "5m", [1], visible),
            game._defense_risk(0, "6p", [1], visible),
        )

    def test_simple_policy_remains_available(self) -> None:
        game = MahjongGame(ai_levels=["simple"] * 4, interactive=False)
        player = game.players[0]
        player.hand = "1m 2m 4m 5m 7m 8m 1p 2p 4p 5p 7s 8s E E".split()
        discard, shanten = game._choose_simple_discard(player)
        self.assertIn(discard, player.hand)
        self.assertEqual(shanten, game._shanten_after_discard(player, discard))


if __name__ == "__main__":
    unittest.main()
