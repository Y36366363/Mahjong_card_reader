from __future__ import annotations

import argparse
import io
import json
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from contextlib import redirect_stdout
from dataclasses import asdict
from itertools import combinations
from pathlib import Path
from typing import Any

from game import MahjongGame


MATCHUPS = ("1_advanced", "2_advanced", "3_advanced")


def levels_for(matchup: str, game_index: int) -> list[str]:
    levels = ["simple"] * 4
    if matchup == "1_advanced":
        levels[game_index % 4] = "advanced"
    elif matchup == "2_advanced":
        pair = list(combinations(range(4), 2))[game_index % 6]
        for seat in pair:
            levels[seat] = "advanced"
    elif matchup == "3_advanced":
        levels = ["advanced"] * 4
        levels[game_index % 4] = "simple"
    else:
        raise ValueError(f"Unknown matchup: {matchup}")
    return levels


def run_one(matchup: str, game_index: int, seed: int) -> dict[str, Any]:
    levels = levels_for(matchup, game_index)
    game = MahjongGame(seed=seed, interactive=False, ai_levels=levels, language="en")
    started = time.perf_counter()
    with redirect_stdout(io.StringIO()):
        game.play()
    elapsed = time.perf_counter() - started
    ranked = sorted(range(4), key=lambda i: (-game.players[i].points, i))
    ranks = {seat: rank for rank, seat in enumerate(ranked, 1)}
    return {
        "matchup": matchup,
        "game_index": game_index,
        "seed": seed,
        "elapsed_seconds": elapsed,
        "point_total": sum(player.points for player in game.players),
        "players": [
            {
                "seat": seat,
                "level": levels[seat],
                "points": player.points,
                "rank": ranks[seat],
                **asdict(player.stats),
            }
            for seat, player in enumerate(game.players)
        ],
    }


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for matchup in MATCHUPS:
        games = [result for result in results if result["matchup"] == matchup]
        block: dict[str, Any] = {
            "games": len(games),
            "hands": sum(game["players"][0]["hands"] for game in games),
            "elapsed_seconds": sum(game["elapsed_seconds"] for game in games),
            "invalid_point_totals": sum(game["point_total"] != 100_000 for game in games),
        }
        for level in ("advanced", "simple"):
            rows = [player for game in games for player in game["players"] if player["level"] == level]
            entries = len(rows)
            block[level] = {
                "entries": entries,
                "wins": sum(row["wins"] for row in rows),
                "ron": sum(row["ron"] for row in rows),
                "tsumo": sum(row["tsumo"] for row in rows),
                "deal_in": sum(row["deal_in"] for row in rows),
                "riichi": sum(row["riichi"] for row in rows),
                "calls": sum(row["chi"] + row["pon"] + row["kan"] for row in rows),
                "average_points": sum(row["points"] for row in rows) / entries,
                "average_rank": sum(row["rank"] for row in rows) / entries,
                "first_rate": sum(row["rank"] == 1 for row in rows) / entries,
                "fourth_rate": sum(row["rank"] == 4 for row in rows) / entries,
            }
        summary[matchup] = block
    return summary


def print_summary(summary: dict[str, Any]) -> None:
    for matchup in MATCHUPS:
        block = summary[matchup]
        print(f"\n{matchup}: {block['games']} games, {block['hands']} hands, {block['elapsed_seconds']:.1f}s")
        print("  level      entries wins ron tsumo deal-in riichi calls avg-points avg-rank first% fourth%")
        for level in ("advanced", "simple"):
            row = block[level]
            print(
                f"  {level:<10} {row['entries']:>7} {row['wins']:>4} {row['ron']:>3} "
                f"{row['tsumo']:>5} {row['deal_in']:>7} {row['riichi']:>6} {row['calls']:>5} "
                f"{row['average_points']:>10.0f} {row['average_rank']:>8.2f} "
                f"{row['first_rate']:>6.1%} {row['fourth_rate']:>7.1%}"
            )


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark advanced/simple Mahjong AI matchups.")
    parser.add_argument(
        "--games", type=int, default=24,
        help="Games per matchup (default: 24; divisible by both 4 seats and 6 seat pairs)",
    )
    parser.add_argument("--seed", type=int, default=800, help="First shared seed (default: 800)")
    parser.add_argument("--index-offset", type=int, default=0, help="Rotation index offset for batched runs")
    parser.add_argument("--workers", type=int, default=4, help="Parallel worker processes")
    parser.add_argument("--json", type=Path, default=None, help="Optional detailed JSON output path")
    args = parser.parse_args()
    if args.games < 1 or args.workers < 1:
        parser.error("--games and --workers must be positive.")

    tasks = [
        (matchup, args.index_offset + index, args.seed + index)
        for matchup in MATCHUPS
        for index in range(args.games)
    ]
    results: list[dict[str, Any]] = []
    try:
        with ProcessPoolExecutor(max_workers=args.workers) as executor:
            futures = [executor.submit(run_one, *task) for task in tasks]
            for future in as_completed(futures):
                results.append(future.result())
    except PermissionError:
        # Restricted environments may disallow process semaphores. Preserve
        # correctness with a sequential fallback.
        results = [run_one(*task) for task in tasks]
    results.sort(key=lambda item: (item["matchup"], item["game_index"]))
    summary = summarize(results)
    print_summary(summary)
    if args.json:
        args.json.write_text(
            json.dumps({"summary": summary, "games": results}, indent=2), encoding="utf-8"
        )
        print(f"\nDetailed JSON written to {args.json}")


if __name__ == "__main__":
    main()
