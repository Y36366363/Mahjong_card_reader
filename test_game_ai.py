from __future__ import annotations

import random
import unittest
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch

from game import MahjongGame
from scoring import score_points_from_config
from shanten import shanten_standard, shanten_standard_draw_state
from tiles import index_to_tile, tiles_to_counts


class AdvancedAITests(unittest.TestCase):
    def test_ura_dora_is_real_scoring_input_and_requires_riichi(self) -> None:
        args = dict(
            hand_text="1m 2m 3m 1p 2p 3p 1s 2s 3s E E E P",
            win_tile_text="P", win_type="ron", is_dealer=False,
            seat_wind="S", round_wind="E", ura_dora_text="P",
        )
        riichi = score_points_from_config(**args, riichi=True)
        dama = score_points_from_config(**args, riichi=False)
        self.assertEqual(riichi.ura_dora_han, 2)
        self.assertEqual(dama.ura_dora_han, 0)
        self.assertGreater(riichi.han, dama.han)

    def test_dead_wall_fixes_parallel_dora_ura_pairs_for_kans(self) -> None:
        game = MahjongGame(seed=20260719)
        game._new_wall()
        self.assertEqual(len(game._rinshan_tiles), 4)
        self.assertEqual(len(game._all_dora_indicators), 5)
        self.assertEqual(len(game._all_ura_dora_indicators), 5)
        self.assertEqual(game.dora_indicators, game._all_dora_indicators[:1])
        self.assertEqual(game.ura_dora_indicators, game._all_ura_dora_indicators[:1])
        game._reveal_kan_dora()
        self.assertEqual(game.dora_indicators, game._all_dora_indicators[:2])
        self.assertEqual(game.ura_dora_indicators, game._all_ura_dora_indicators[:2])

    def test_win_confirmation_label_hides_points_until_final_score(self) -> None:
        game = MahjongGame(language="zh")
        game.players[0].hand = "1m 2m 3m 1p 2p 3p 1s 2s 3s E E E P P".split()
        game.players[0].riichi = True
        game.dora_indicators = ["9m"]
        game.ura_dora_indicators = ["C"]
        score = game._try_score(0, "P", "tsumo", include_ura=True)
        self.assertIsNotNone(score)
        self.assertNotIn("点", game._yaku_label(score))
        self.assertIn("里宝牌2", game._score_label(score))
        self.assertIn("点", game._score_label(score))

    def test_win_settlement_records_all_revealed_hands_and_relationship(self) -> None:
        game = MahjongGame(language="zh")
        game.players[1].hand = "1m 2m 3m 1p 2p 3p 1s 2s 3s E E E P".split()
        game.players[1].riichi = True
        game.dora_indicators = ["9m"]
        game.ura_dora_indicators = ["C"]
        score = game._try_score(1, "P", "ron", include_ura=True)
        self.assertIsNotNone(score)
        before = [player.points for player in game.players]
        game._settle_ron(0, [(1, score)])
        game._show_hand_settlement(before, False)
        settlement = game.last_hand_settlement
        self.assertEqual(len(settlement["hands"]), 4)
        self.assertEqual(settlement["wins"][0]["winner"], 1)
        self.assertEqual(settlement["wins"][0]["loser"], 0)
        self.assertEqual(settlement["wins"][0]["ura_indicators"], ["C"])

    def test_ron_confirmation_shows_yaku_but_not_points(self) -> None:
        game = MahjongGame(interactive=True, language="zh")
        game.players[0].hand = "1m 2m 3m 1p 2p 3p 1s 2s 3s E E E P".split()
        game.players[0].riichi = True
        prompts: list[str] = []

        def decline(prompt: str) -> str:
            prompts.append(prompt)
            return "否"

        with redirect_stdout(StringIO()), patch("builtins.input", side_effect=decline):
            self.assertIsNone(game._resolve_ron(1, "P"))
        self.assertTrue(prompts)
        self.assertIn("役种", prompts[0])
        self.assertNotIn("点", prompts[0])

    def test_ai_levels_are_explicit_and_validated(self) -> None:
        game = MahjongGame(ai_levels=["simple", "advanced", "simple", "advanced"])
        self.assertEqual([p.ai_level for p in game.players], ["simple", "advanced", "simple", "advanced"])
        self.assertEqual(
            [p.ai_profile for p in game.players],
            ["basic_v1", "advanced_v1", "basic_v1", "advanced_v1"],
        )
        versioned = MahjongGame(ai_levels=["basic_v1", "advanced_v1"] * 2)
        self.assertEqual(
            [p.ai_level for p in versioned.players],
            ["simple", "advanced", "simple", "advanced"],
        )
        with self.assertRaises(ValueError):
            MahjongGame(ai_levels=["advanced"])
        with self.assertRaises(ValueError):
            MahjongGame(ai_levels=["unknown"] * 4)
        with self.assertRaises(ValueError):
            MahjongGame(ai_temperatures=1.1)
        with self.assertRaises(ValueError):
            MahjongGame(match_length="west")

    def test_match_length_round_progression_and_extension_threshold(self) -> None:
        east = MahjongGame(match_length="east")
        east.round_hand = 3
        for player, points in zip(east.players, (29_000, 27_000, 24_000, 20_000)):
            player.points = points
        self.assertFalse(east._should_end_match_after_hand(False))
        east._advance_round()
        self.assertEqual((east.round_wind, east.round_hand), ("S", 0))
        east.players[0].points = 30_000
        self.assertTrue(east._should_end_match_after_hand(False))

        south = MahjongGame(match_length="south")
        south.round_wind_index = 1; south.round_hand = 3
        for player, points in zip(south.players, (29_000, 27_000, 24_000, 20_000)):
            player.points = points
        self.assertFalse(south._should_end_match_after_hand(False))
        south._advance_round()
        self.assertEqual((south.round_wind, south.round_hand), ("W", 0))

    def test_zero_points_survives_but_negative_points_busts(self) -> None:
        game = MahjongGame()
        game.round_hand = 3
        game.players[0].points = 0
        game.players[1].points = 29_000
        game.players[2].points = 36_000
        game.players[3].points = 35_000
        self.assertTrue(game._should_end_match_after_hand(False))  # leader reached 30k
        game.round_hand = 0
        self.assertFalse(game._should_end_match_after_hand(False))
        game.players[0].points = -100
        self.assertTrue(game._should_end_match_after_hand(True))

    def test_south_round_wind_is_used_for_yakuhai_scoring(self) -> None:
        game = MahjongGame()
        game.dealer = 2  # seat 0 is West, so South is only the round wind here
        game.players[0].hand = "1m 2m 3m 1p 2p 3p 1s 2s 3s S S S P".split()
        game.round_wind_index = 0
        self.assertIsNone(game._try_score(0, "P", "ron"))
        game.round_wind_index = 1
        self.assertIsNotNone(game._try_score(0, "P", "ron"))

    def test_player_below_1000_cannot_declare_riichi(self) -> None:
        game = MahjongGame(interactive=True, language="zh")
        player = game.players[0]
        player.points = 999
        player.hand = "1m 2m 3m 1p 2p 3p 1s 2s 3s E E E P 9m".split()
        player.sort()
        with patch("builtins.input", side_effect=["9m"]):
            self.assertEqual(game._choose_discard(0), "9m")
        self.assertFalse(player.riichi)
        self.assertEqual(player.points, 999)

    def test_temperature_is_reproducible_and_never_crosses_shanten_guard(self) -> None:
        game = MahjongGame(seed=77, ai_levels=["advanced"] * 4, ai_temperatures=0.8)
        report = {
            "mode": "push", "chosen": "1m",
            "candidates": [
                {"tile": "1m", "shanten": 1, "ukeire_total": 20, "ukeire_kinds": 6, "risk": 0.0, "tile_value": 0.0},
                {"tile": "2m", "shanten": 1, "ukeire_total": 19, "ukeire_kinds": 6, "risk": 0.2, "tile_value": 0.2},
                {"tile": "9p", "shanten": 2, "ukeire_total": 30, "ukeire_kinds": 8, "risk": 0.0, "tile_value": 0.0},
            ],
        }
        choices = [game._temperature_discard_choice(0, report) for _ in range(100)]
        self.assertTrue(set(choices) <= {"1m", "2m"})
        self.assertIn("2m", choices)
        replay = MahjongGame(seed=77, ai_levels=["advanced"] * 4, ai_temperatures=0.8)
        self.assertEqual(
            choices, [replay._temperature_discard_choice(0, report) for _ in range(100)]
        )

    def test_temperature_does_not_change_seeded_wall(self) -> None:
        fixed = MahjongGame(seed=88, ai_temperatures=0.0)
        varied = MahjongGame(seed=88, ai_temperatures=1.0)
        fixed._new_wall(); varied._new_wall()
        self.assertEqual(fixed.wall, varied.wall)
        self.assertEqual(fixed.dead_wall, varied.dead_wall)

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
        self.assertEqual(game.last_chi_options, [])

    def test_user_gets_riichi_confirmation_after_a_tenpai_discard(self) -> None:
        game = MahjongGame(interactive=True, language="zh")
        player = game.players[0]
        player.hand = "1m 2m 3m 1p 2p 3p 1s 2s 3s E E E P 9m".split()
        player.sort()
        with patch("builtins.input", side_effect=["9m", "是"]):
            self.assertEqual(game._choose_discard(0), "9m")
        self.assertTrue(player.riichi)
        self.assertEqual(player.points, 24_000)

    def test_hint_call_analysis_is_recorded_without_mutating_stats(self) -> None:
        game = MahjongGame(interactive=True, assist_mode="hint", ai_levels=["advanced"] * 4)
        player = game.players[0]
        player.hand = "E E 1m 2m 3m 4p 5p 6p 7s 8s 9s P P".split()
        before = player.stats.call_decisions
        with patch("builtins.input", side_effect=["n"]):
            self.assertIsNone(game._choose_user_call("E", [("pon", ["E"] * 3)]))
        self.assertIn(game.last_call_recommendation, {"pon", "pass"})
        self.assertEqual(player.stats.call_decisions, before)

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
        self.assertIn("万子:", text)
        self.assertIn("筒子:", text)
        self.assertIn("索子:", text)
        self.assertIn("字牌:", text)
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

    def test_japanese_game_view_is_localized(self) -> None:
        game = MahjongGame(
            interactive=True, assist_mode="hint", language="ja", ai_levels=["advanced"] * 4
        )
        game.wall = ["1m"] * 20
        game.dora_indicators = ["4p"]
        game.players[0].hand = "1m 2m 3m 4m 5m 6m 2p 3p 4p 5s 6s 7s E E".split()
        output = StringIO()
        with redirect_stdout(output):
            game._show_state("E")
        text = output.getvalue()
        self.assertIn("あなたの手牌", text)
        self.assertIn("プレイヤー状態", text)
        self.assertIn("推奨打牌", text)
        self.assertIn("牌カウンター", text)
        self.assertNotIn("Your hand", text)

    def test_automatic_match_collects_final_statistics(self) -> None:
        game = MahjongGame(seed=91, interactive=False, assist_mode="normal")
        with redirect_stdout(StringIO()):
            game.play()
        self.assertTrue(all(player.stats.hands >= 4 for player in game.players))
        self.assertEqual(sum(player.points for player in game.players), 100_000)
        self.assertIsNotNone(game.last_hand_settlement)
        self.assertIn(game.last_hand_settlement["win_type"], {"ron", "tsumo", "draw"})
        self.assertEqual(len(game.last_hand_settlement["scores"]), 4)
        self.assertIsNotNone(game.final_summary)
        ranking = game.final_summary["ranking"]
        self.assertEqual([row["rank"] for row in ranking], [1, 2, 3, 4])
        self.assertEqual(sum(row["points"] for row in ranking), 100_000)


if __name__ == "__main__":
    unittest.main()
