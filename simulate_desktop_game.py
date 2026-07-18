from __future__ import annotations

import argparse
import io
import json
import time
from collections import Counter
from contextlib import redirect_stdout
from dataclasses import asdict
from pathlib import Path
from typing import Any
from unittest.mock import patch

from desktop_ui import classify_prompt
from game import MahjongGame


class SimulatedDesktopPlayer:
    """Exercise the same prompts used by the desktop UI for a complete match."""

    def __init__(self, game: MahjongGame, *, accept_calls: bool = False) -> None:
        self.game = game
        self.accept_calls = accept_calls
        self.prompts: Counter[str] = Counter()
        self.discards: list[str] = []

    def __call__(self, prompt: str = "") -> str:
        kind = classify_prompt(prompt)
        self.prompts[kind] += 1
        lower = prompt.lower()
        if kind == "discard":
            tile = str(self.game.advanced_discard_report(0)["chosen"])
            self.discards.append(tile)
            return tile
        if kind == "chi":
            return "1" if self.accept_calls and self.game.last_chi_options else "0"
        if kind == "continue":
            return ""
        if kind == "yes_no":
            # Always take a legal win and normally declare riichi. Calls are
            # declined so the simulation still tests pass/furiten prompt paths
            # without hiding the closed-hand discard flow.
            if any(word in lower for word in ("ron", "tsumo", "荣和", "自摸", "和了")):
                return "y"
            if any(word in lower for word in ("riichi", "立直", "リーチ")):
                return "y"
            if self.accept_calls and any(word in lower for word in ("pon", "kan", "碰", "杠", "ポン", "カン")):
                return "y"
            return "n"
        raise RuntimeError(f"Unhandled desktop prompt: {prompt!r}")


def run_simulated_match(
    *, seed: int, opponent_profile: str = "advanced_v1",
    temperature: float = 0.2, assist_mode: str = "hint", accept_calls: bool = False,
) -> dict[str, Any]:
    game = MahjongGame(
        seed=seed,
        interactive=True,
        ai_levels=["basic_v1", opponent_profile, opponent_profile, opponent_profile],
        ai_temperatures=[0.0, temperature, temperature, temperature],
        assist_mode=assist_mode,
        language="en",
    )
    player = SimulatedDesktopPlayer(game, accept_calls=accept_calls)
    output = io.StringIO()
    started = time.perf_counter()
    with redirect_stdout(output), patch("builtins.input", player):
        game.play()
    elapsed = time.perf_counter() - started
    text = output.getvalue()
    hints = text.count("Hint:")
    trackers = text.count("Tile tracker")
    statuses = text.count("Player status:")
    rivers = text.count("Rivers:")
    return {
        "seed": seed,
        "opponent_profile": opponent_profile,
        "temperature": temperature,
        "assist_mode": assist_mode,
        "accept_calls": accept_calls,
        "elapsed_seconds": elapsed,
        "point_total": sum(p.points for p in game.players),
        "round_hand": game.round_hand,
        "hands": game.players[0].stats.hands,
        "prompts": dict(player.prompts),
        "player_discards": len(player.discards),
        "hint_blocks": hints,
        "tracker_blocks": trackers,
        "status_blocks": statuses,
        "river_blocks": rivers,
        "hint_complete": assist_mode != "hint" or (
            hints == trackers == statuses == rivers and hints >= len(player.discards)
        ),
        "players": [
            {"seat": seat, "profile": p.ai_profile, "points": p.points, **asdict(p.stats)}
            for seat, p in enumerate(game.players)
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulate complete desktop-style East matches.")
    parser.add_argument("--games", type=int, default=4)
    parser.add_argument("--seed", type=int, default=6000)
    parser.add_argument("--profile", choices=("basic_v1", "advanced_v1"), default="advanced_v1")
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--assist", choices=("normal", "hint"), default="hint")
    parser.add_argument("--calls", choices=("pass", "accept"), default="pass")
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()
    if args.games < 1 or not 0 <= args.temperature <= 1:
        parser.error("--games must be positive and --temperature must be from 0 to 1")
    results = [
        run_simulated_match(
            seed=args.seed + index, opponent_profile=args.profile,
            temperature=args.temperature, assist_mode=args.assist,
            accept_calls=args.calls == "accept",
        )
        for index in range(args.games)
    ]
    elapsed = sum(result["elapsed_seconds"] for result in results)
    print(
        f"{len(results)} complete East matches | {sum(r['hands'] for r in results)} hands | "
        f"{elapsed:.1f}s | invalid totals={sum(r['point_total'] != 100_000 for r in results)} | "
        f"incomplete hints={sum(not r['hint_complete'] for r in results)}"
    )
    print(
        f"player discards={sum(r['player_discards'] for r in results)} | "
        f"prompts={dict(sum((Counter(r['prompts']) for r in results), Counter()))}"
    )
    if args.json:
        args.json.write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(f"Detailed JSON written to {args.json}")


if __name__ == "__main__":
    main()
