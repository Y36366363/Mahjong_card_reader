from __future__ import annotations

import random
import unittest
from unittest.mock import patch

from game import MahjongGame, MeldState
from tiles import index_to_tile


def make_game() -> MahjongGame:
    game = MahjongGame(interactive=False, ai_levels=["advanced"] * 4)
    game.wall = ["1p"] * 40
    game.dora_indicators = ["4m"]  # 5m is dora
    return game


class TileEfficiencyTests(unittest.TestCase):
    def test_shanten_is_the_first_offensive_priority(self) -> None:
        rng = random.Random(20260715)
        wall = [index_to_tile(i) for i in range(34) for _ in range(4)]
        game = make_game()
        for _ in range(8):
            rng.shuffle(wall)
            player = game.players[0]
            player.hand = sorted(wall[:14], key=lambda t: (t[-1] if len(t) == 2 else "z", t))
            chosen = game._choose_advanced_discard(0)
            shanten = {tile: game._shanten_after_discard(player, tile) for tile in set(player.hand)}
            self.assertEqual(shanten[chosen], min(shanten.values()))

    def test_equal_shanten_uses_the_largest_remaining_ukeire_first(self) -> None:
        game = make_game()
        player = game.players[0]
        player.hand = "1m 2m 4m 5m 7m 8m 1p 2p 4p 5p 7s 8s E E".split()
        visible = game._visible_counts(0)
        shanten = {tile: game._shanten_after_discard(player, tile) for tile in set(player.hand)}
        best = min(shanten.values())
        totals: dict[str, int] = {}
        for tile in (t for t, value in shanten.items() if value == best):
            player.hand.remove(tile)
            totals[tile] = game._ukeire(player, visible)[1]
            player.hand.append(tile); player.sort()
        chosen = game._choose_advanced_discard(0)
        self.assertEqual(totals[chosen], max(totals.values()))

    def test_visible_tiles_and_dora_indicator_reduce_remaining_ukeire(self) -> None:
        game = make_game()
        player = game.players[0]
        player.hand = "1m 2m 3m 4m 5m 6m 2p 3p 4p 5s 6s 7s E".split()
        visible = game._visible_counts(0)
        self.assertEqual(visible[3], 2)  # 4m in hand plus public dora indicator
        before = game._ukeire(player, visible)[1]
        game.players[1].river.extend(["E", "E"])
        after = game._ukeire(player, game._visible_counts(0))[1]
        self.assertLessEqual(after, before)

    def test_dora_value_honor_connections_and_isolated_terminal_values(self) -> None:
        game = make_game()
        player = game.players[0]
        player.hand = "4m 5m 5m 8p 1s E E 2p 3p 4p 6s 7s 8s 9s".split()
        self.assertGreater(game._tile_value(0, "5m"), game._tile_value(0, "8p"))
        self.assertGreater(game._tile_value(0, "E"), game._tile_value(0, "8p"))
        self.assertGreater(game._tile_value(0, "4m"), game._tile_value(0, "8p"))
        self.assertLess(game._tile_value(0, "1s"), game._tile_value(0, "8p"))


class DefenseTests(unittest.TestCase):
    def test_genbutsu_suji_wall_and_honor_safety(self) -> None:
        game = make_game()
        opponent = game.players[1]
        opponent.riichi = True
        opponent.river = ["1m", "6p"]
        visible = game._visible_counts(0)
        self.assertEqual(game._defense_risk(0, "6p", [1], visible), 0.0)  # genbutsu
        self.assertLess(
            game._defense_risk(0, "4m", [1], visible),
            game._defense_risk(0, "4s", [1], visible),
        )
        game.players[2].river = ["5s"] * 4
        walled = game._visible_counts(0)
        self.assertLess(
            game._defense_risk(0, "4s", [1], walled),
            game._defense_risk(0, "4p", [1], walled),
        )
        game.players[2].river = ["E", "E", "E"]
        honors = game._visible_counts(0)
        self.assertLess(
            game._defense_risk(0, "E", [1], honors),
            game._defense_risk(0, "P", [1], honors),
        )

    def test_multiple_riichi_threats_accumulate_risk(self) -> None:
        game = make_game()
        game.players[1].riichi = game.players[2].riichi = True
        visible = game._visible_counts(0)
        one = game._defense_risk(0, "5p", [1], visible)
        two = game._defense_risk(0, "5p", [1, 2], visible)
        self.assertGreater(two, one)

    def test_rank_and_shanten_control_folding(self) -> None:
        game = make_game()
        threats = [1]
        game.players[0].points = 35_000
        self.assertTrue(game._should_fold(0, 1, threats))
        game.players[0].points = 15_000
        game.players[1].points = game.players[2].points = game.players[3].points = 28_000
        self.assertFalse(game._should_fold(0, 1, threats))
        self.assertTrue(game._should_fold(0, 2, threats))

    def test_tied_scores_have_stable_unique_ranks(self) -> None:
        game = make_game()
        self.assertEqual([game._current_rank(i) for i in range(4)], [1, 2, 3, 4])

    def test_dealer_dora_and_late_round_raise_danger(self) -> None:
        game = make_game()
        game.dealer = 1
        game.players[1].riichi = True
        visible = game._visible_counts(0)
        dealer = game._defense_risk(0, "5p", [1], visible)
        game.dealer = 2
        nondealer = game._defense_risk(0, "5p", [1], visible)
        self.assertGreater(dealer, nondealer)
        self.assertGreater(
            game._defense_risk(0, "5m", [1], visible),
            game._defense_risk(0, "5p", [1], visible),
        )
        early = game._defense_risk(0, "5p", [1], visible)
        game.players[2].river = ["1s"] * 12
        late = game._defense_risk(0, "5p", [1], game._visible_counts(0))
        self.assertGreater(late, early)

    def test_push_balanced_and_fold_modes(self) -> None:
        game = make_game()
        game.players[1].riichi = True
        self.assertEqual(game._defense_mode(0, 0, [1], 8), "push")
        game.players[0].points = 20_000
        game.players[1].points = game.players[2].points = game.players[3].points = 28_000
        self.assertEqual(game._defense_mode(0, 1, [1], 10), "balanced")
        self.assertEqual(game._defense_mode(0, 3, [1], 30), "fold")
        game.players[0].points = 15_000
        game.players[1].points = game.players[2].points = game.players[3].points = 28_000
        self.assertEqual(game._defense_mode(0, 2, [1], 24), "balanced")

    def test_explainable_report_contains_candidate_metrics(self) -> None:
        game = make_game()
        player = game.players[0]
        player.hand = "1m 2m 4m 5m 7m 8m 1p 2p 4p 5p 7s 8s E E".split()
        game.players[1].riichi = True
        report = game.advanced_discard_report(0)
        self.assertIn(report["mode"], {"push", "balanced", "fold"})
        self.assertIn(report["chosen"], player.hand)
        self.assertTrue(report["candidates"])
        for candidate in report["candidates"]:
            self.assertIn("risk", candidate)
            self.assertIn("ukeire_total", candidate)
            self.assertIn("risk_tags", candidate)

    def test_open_flush_and_toitoi_tendencies_affect_risk(self) -> None:
        game = make_game()
        opponent = game.players[1]
        opponent.riichi = True
        opponent.melds = [
            MeldState("pon", ["2m"] * 3), MeldState("pon", ["8m"] * 3),
        ]
        visible = game._visible_counts(0)
        same_suit = game._defense_risk_breakdown(0, "5m", [1], visible)
        outside = game._defense_risk_breakdown(0, "5p", [1], visible)
        honor = game._defense_risk_breakdown(0, "P", [1], visible)
        self.assertGreater(float(same_suit["total"]), float(outside["total"]))
        self.assertIn("flush-suit", same_suit["tags"])
        self.assertIn("toitoi-terminal-honor", honor["tags"])


class RiichiDecisionTests(unittest.TestCase):
    def profile(self, **overrides: object) -> dict[str, object]:
        result: dict[str, object] = {
            "waits": [{"tile": "5m"}], "kinds": 1, "remaining": 2,
            "good_wait": False, "dama_yaku": True,
            "expected_points": 2600, "max_points": 2600,
        }
        result.update(overrides)
        return result

    def prepared(self) -> MahjongGame:
        game = make_game()
        game.players[0].hand = "1m 2m 3m 4m 5m 6m 2p 3p 4p 5s 6s 7s E".split()
        return game

    def test_bad_low_value_dama_wait_stays_dama(self) -> None:
        game = self.prepared()
        with patch.object(game, "_standard_shanten", return_value=0), \
             patch.object(game, "_tenpai_profile", return_value=self.profile()):
            self.assertFalse(game._should_declare_riichi(0))

    def test_mangan_good_wait_declares_and_bad_chase_does_not(self) -> None:
        game = self.prepared()
        strong = self.profile(kinds=2, remaining=6, good_wait=True, expected_points=8000, max_points=8000)
        with patch.object(game, "_standard_shanten", return_value=0), \
             patch.object(game, "_tenpai_profile", return_value=strong):
            self.assertTrue(game._should_declare_riichi(0))
        game.players[1].riichi = True
        weak = self.profile(dama_yaku=False, expected_points=3900, max_points=3900)
        with patch.object(game, "_standard_shanten", return_value=0), \
             patch.object(game, "_tenpai_profile", return_value=weak):
            self.assertFalse(game._should_declare_riichi(0))

    def test_late_dead_wait_and_large_lead_avoid_riichi(self) -> None:
        game = self.prepared(); game.wall = ["1p"] * 8
        with patch.object(game, "_standard_shanten", return_value=0), \
             patch.object(game, "_tenpai_profile", return_value=self.profile()):
            self.assertFalse(game._should_declare_riichi(0))
        game.wall = ["1p"] * 30; game.players[0].points = 40_000
        with patch.object(game, "_standard_shanten", return_value=0), \
             patch.object(game, "_tenpai_profile", return_value=self.profile(expected_points=5200)):
            self.assertFalse(game._should_declare_riichi(0))

    def test_east_four_last_place_uses_required_points(self) -> None:
        game = self.prepared(); game.round_hand = 3
        game.players[0].points = 20_000
        game.players[1].points = game.players[2].points = game.players[3].points = 25_000
        enough = self.profile(expected_points=5200, max_points=5200)
        with patch.object(game, "_standard_shanten", return_value=0), \
             patch.object(game, "_tenpai_profile", return_value=enough):
            self.assertTrue(game._should_declare_riichi(0))


class CallAndKanTests(unittest.TestCase):
    def test_unknown_yaku_call_is_rejected(self) -> None:
        game = make_game()
        player = game.players[0]
        player.hand = "1m 2m 4m 5m 7m 8m 1p 2p 4p 5p 7s 8s E".split()
        self.assertIsNone(game._advanced_call_choice(0, "3m", [("chi", ["1m", "2m", "3m"])]))

    def test_value_honor_call_is_allowed_when_it_does_not_slow_the_hand(self) -> None:
        game = make_game()
        player = game.players[0]
        player.points = 20_000
        game.players[1].points = 30_000
        player.hand = "E E 1m 2m 5m 6m 9m 1p 4p 7p 1s 4s 7s".split()
        choice = game._advanced_call_choice(0, "E", [("pon", ["E"] * 3)])
        self.assertEqual(choice, ("pon", ["E"] * 3))

    def test_closed_tenpai_preserves_riichi_route(self) -> None:
        game = make_game()
        player = game.players[0]
        player.hand = "E E E 1m 2m 3m 4p 5p 6p 7s 8s 9s P".split()
        self.assertEqual(game._standard_shanten(player), 0)
        self.assertIsNone(game._advanced_call_choice(0, "E", [("pon", ["E"] * 3)]))

    def test_call_rejects_worse_shanten_and_severe_iishanten_ukeire_loss(self) -> None:
        game = make_game()
        player = game.players[0]
        player.hand = "E E 1m 2m 5m 6m 9m 1p 4p 7p 1s 4s 7s".split()
        option = [("pon", ["E"] * 3)]
        with patch.object(game, "_standard_shanten", side_effect=[2, 3]), \
             patch.object(game, "_ukeire", side_effect=[(5, 20), (5, 20)]):
            self.assertIsNone(game._advanced_call_choice(0, "E", option))
        with patch.object(game, "_standard_shanten", side_effect=[1, 1]), \
             patch.object(game, "_ukeire", side_effect=[(5, 10), (2, 4)]):
            self.assertIsNone(game._advanced_call_choice(0, "E", option))

    def test_kan_is_rejected_for_riichi_threat_lead_and_short_wall(self) -> None:
        option = [("kan", ["E"] * 4)]

        def prepared() -> MahjongGame:
            game = make_game()
            game.players[0].hand = "E E E 1m 2m 5m 7m 9m 1p 4p 7p 1s 4s".split()
            game.players[0].points = 20_000
            game.players[1].points = 30_000
            return game

        threatened = prepared(); threatened.players[1].riichi = True
        self.assertIsNone(threatened._advanced_call_choice(0, "E", option))
        leading = prepared(); leading.players[0].points = 40_000
        self.assertIsNone(leading._advanced_call_choice(0, "E", option))
        late = prepared(); late.wall = ["1p"] * 12
        self.assertIsNone(late._advanced_call_choice(0, "E", option))

    def test_kan_rejects_equal_shanten_with_lower_ukeire(self) -> None:
        game = make_game()
        player = game.players[0]
        player.points = 20_000
        game.players[1].points = 30_000
        player.hand = "E E E 1m 2m 5m 7m 9m 1p 4p 7p 1s 4s".split()
        with patch.object(game, "_standard_shanten", side_effect=[2, 2]), \
             patch.object(game, "_ukeire", side_effect=[(5, 10), (4, 9)]):
            self.assertIsNone(game._advanced_call_choice(0, "E", [("kan", ["E"] * 4)]))


if __name__ == "__main__":
    unittest.main()
