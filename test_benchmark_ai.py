from __future__ import annotations

import unittest

from benchmark_ai import levels_for, summarize


class BenchmarkAITests(unittest.TestCase):
    def test_one_and_three_advanced_rotate_every_seat(self) -> None:
        one = [levels_for("1_advanced", i) for i in range(4)]
        three = [levels_for("3_advanced", i) for i in range(4)]
        for seat in range(4):
            self.assertEqual(sum(levels[seat] == "advanced" for levels in one), 1)
            self.assertEqual(sum(levels[seat] == "simple" for levels in three), 1)

    def test_two_advanced_rotates_all_six_seat_pairs(self) -> None:
        pairs = {
            tuple(i for i, level in enumerate(levels_for("2_advanced", game)) if level == "advanced")
            for game in range(6)
        }
        self.assertEqual(len(pairs), 6)

    def test_summary_detects_invalid_point_total(self) -> None:
        games = []
        for matchup in ("1_advanced", "2_advanced", "3_advanced"):
            levels = levels_for(matchup, 0)
            games.append({
                "matchup": matchup,
                "elapsed_seconds": 1.0,
                "point_total": 99_900 if matchup == "1_advanced" else 100_000,
                "players": [
                    {
                        "level": level, "points": 25_000, "rank": seat + 1,
                        "hands": 4, "wins": 0, "ron": 0, "tsumo": 0,
                        "deal_in": 0, "riichi": 0, "chi": 0, "pon": 0, "kan": 0,
                    }
                    for seat, level in enumerate(levels)
                ],
            })
        result = summarize(games)
        self.assertEqual(result["1_advanced"]["invalid_point_totals"], 1)
        self.assertEqual(result["2_advanced"]["invalid_point_totals"], 0)
        self.assertIn("quality", result["1_advanced"]["advanced"])
        self.assertEqual(
            result["1_advanced"]["advanced"]["quality"]["riichi_wins"], 0
        )


if __name__ == "__main__":
    unittest.main()
