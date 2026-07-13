from __future__ import annotations

import random
import unittest
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch

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

    def test_interactive_mode_and_separate_call_prompts(self) -> None:
        game = MahjongGame(interactive=True)
        with redirect_stdout(StringIO()):
            with patch("builtins.input", side_effect=["2"]):
                self.assertEqual(game._choose_assist_mode(), "hint")
        options = [("pon", ["E"] * 3), ("kan", ["E"] * 4)]
        with patch("builtins.input", side_effect=["n", "是"]):
            self.assertEqual(game._choose_user_call("E", options), options[0])
        chi = [("chi", ["1m", "2m", "3m"]), ("chi", ["2m", "3m", "4m"])]
        with redirect_stdout(StringIO()):
            with patch("builtins.input", side_effect=["2"]):
                self.assertEqual(game._choose_user_call("3m", chi), chi[1])

    def test_hint_view_contains_status_rivers_and_tracker(self) -> None:
        game = MahjongGame(interactive=True, assist_mode="hint", ai_levels=["advanced"] * 4)
        game.wall = ["1m"] * 20
        game.dora_indicators = ["4p"]
        game.players[0].hand = "1m 2m 3m 4m 5m 6m 2p 3p 4p 5s 6s 7s E E".split()
        game.players[1].riichi = True
        game.players[1].river = ["9m"]
        output = StringIO()
        with redirect_stdout(output):
            game._show_state("E")
        text = output.getvalue()
        self.assertIn("Player status", text)
        self.assertIn("Rivers", text)
        self.assertIn("Recommended discard", text)
        self.assertIn("Tile tracker", text)

    def test_chinese_game_view_is_localized(self) -> None:
        game = MahjongGame(
            interactive=True, assist_mode="hint", language="zh", ai_levels=["advanced"] * 4
        )
        game.wall = ["1m"] * 20
        game.dora_indicators = ["4p"]
        game.players[0].hand = "1m 2m 3m 4m 5m 6m 2p 3p 4p 5s 6s 7s E E".split()
        output = StringIO()
        with redirect_stdout(output):
            game._show_state("E")
        text = output.getvalue()
        self.assertIn("你的手牌", text)
        self.assertIn("玩家状态", text)
        self.assertIn("牌河", text)
        self.assertIn("推荐弃牌", text)
        self.assertIn("记牌器", text)
        self.assertNotIn("Your hand", text)

    def test_chinese_interaction_prompts(self) -> None:
        game = MahjongGame(interactive=True, language="zh")
        prompts: list[str] = []

        def answer_mode(prompt: str) -> str:
            prompts.append(prompt)
            return "提示"

        with redirect_stdout(StringIO()), patch("builtins.input", side_effect=answer_mode):
            self.assertEqual(game._choose_assist_mode(), "hint")
        with patch("builtins.input", side_effect=lambda prompt: prompts.append(prompt) or "是"):
            self.assertTrue(game._yes_no("是否碰 E？", False))
        self.assertTrue(any("请选择模式" in prompt for prompt in prompts))
        self.assertTrue(any("默认否" in prompt for prompt in prompts))

    def test_automatic_match_collects_final_statistics(self) -> None:
        game = MahjongGame(seed=91, interactive=False, assist_mode="normal")
        with redirect_stdout(StringIO()):
            game.play()
        self.assertTrue(all(player.stats.hands >= 4 for player in game.players))
        self.assertEqual(sum(player.points for player in game.players), 100_000)


if __name__ == "__main__":
    unittest.main()
