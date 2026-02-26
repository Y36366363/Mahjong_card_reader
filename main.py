from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from remaining import RemainingTileCounter
from scoring import score_points_from_config
from shanten import calculate_shanten_all
from tenpai import tenpai_waits_for_13
from tiles import parse_tiles, tiles_to_counts


def _load_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    suffix = path.suffix.lower()
    if suffix == ".json":
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    elif suffix == ".toml":
        try:
            import tomllib  # py>=3.11
        except ModuleNotFoundError as e:  # pragma: no cover
            raise RuntimeError(
                "TOML config requires Python 3.11+ (tomllib). Use JSON instead."
            ) from e
        with path.open("rb") as f:
            data = tomllib.load(f)
    else:
        raise ValueError(f"Unsupported config type: '{suffix}'. Use .json or .toml")

    if not isinstance(data, dict):
        raise ValueError("Config file root must be an object/table (key-value map).")
    return data


def _tiles_field_to_str(value: Any, *, field_name: str) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, list) and all(isinstance(x, str) for x in value):
        return " ".join(value)
    raise ValueError(f"Config field '{field_name}' must be a string or a list of strings.")


def main() -> None:
    ap = argparse.ArgumentParser(description="Riichi Mahjong: shanten + tenpai waits + remaining tiles")
    ap.add_argument(
        "--config",
        "-c",
        type=str,
        default=None,
        help="Config file (.json/.toml) containing 'hand' and optional 'river'. "
        "If omitted and no --hand is given, tries ./default_config.json",
    )
    ap.add_argument(
        "--mode",
        type=str,
        choices=["tenpai", "points"],
        default=None,
        help="Run mode. Overrides config 'mode' if set.",
    )
    ap.add_argument(
        "--hand",
        type=str,
        required=False,
        help="Hand tiles (13 or 14), e.g. '1m 2m 3m E E ...' (can also be set in config)",
    )
    ap.add_argument(
        "--river",
        type=str,
        default=None,
        help="River/discards tiles, space-separated (can also be set in config)",
    )
    args = ap.parse_args()

    config: dict[str, Any] = {}
    config_path: Path | None = None
    if args.config:
        config_path = Path(args.config)
    elif args.hand is None and Path("default_config.json").exists():
        config_path = Path("default_config.json")

    if config_path is not None:
        try:
            config = _load_config(config_path)
        except Exception as e:
            ap.error(str(e))

    mode = args.mode if args.mode is not None else str(config.get("mode", "tenpai")).strip().lower()
    if mode not in {"tenpai", "points"}:
        ap.error("Config field 'mode' must be one of: tenpai, points")

    hand_value = args.hand if args.hand is not None else config.get("hand")
    hand_str = _tiles_field_to_str(hand_value, field_name="hand")
    if hand_str is None:
        ap.error("Missing hand tiles. Provide --hand or set 'hand' in the config file.")

    river_value = args.river if args.river is not None else config.get("river")
    river_str = _tiles_field_to_str(river_value, field_name="river")

    hand_tiles = parse_tiles(hand_str)
    river_tiles = parse_tiles(river_str) if river_str else []

    sh = calculate_shanten_all(hand_tiles)

    counter = RemainingTileCounter()
    counter.set_used_tiles(hand_tiles + river_tiles)

    print("Detected/Provided tiles")
    if mode == "points":
        hand_display = parse_tiles(hand_str, keep_red_fives=True)
        print(f"  Hand  ({len(hand_display)}): {' '.join(hand_display)}")
    else:
        print(f"  Hand  ({len(hand_tiles)}): {' '.join(hand_tiles)}")
    print(f"  River ({len(river_tiles)}): {' '.join(river_tiles)}")
    print()

    print("Shanten")
    print(f"  Standard   : {sh.standard}")
    print(f"  Chiitoitsu : {sh.chiitoitsu}")
    print(f"  Kokushi    : {sh.kokushi}")
    print(f"  Minimum    : {sh.minimum}")
    print()

    waits = None
    if len(hand_tiles) == 13:
        waits = tenpai_waits_for_13(tiles_to_counts(hand_tiles))
        print("Tenpai / waits")
        print(f"  Tenpai: {'YES' if waits.is_tenpai else 'NO'}")
        if waits.is_tenpai:
            if waits.standard_waits:
                print(f"  Standard waits   : {' '.join(waits.standard_waits)}")
            if waits.chiitoi_waits:
                print(f"  Chiitoitsu waits : {' '.join(waits.chiitoi_waits)}")
            if waits.kokushi_waits:
                print(f"  Kokushi waits    : {' '.join(waits.kokushi_waits)}")
            print(f"  All waits        : {' '.join(waits.all_waits)}")
        print()

    if mode == "points":
        points_cfg = config.get("points", config)
        try:
            win_type = str(points_cfg.get("win_type", "tsumo")).strip().lower()
            is_dealer = bool(points_cfg.get("is_dealer", False))
            win_tile = str(points_cfg.get("win_tile", "")).strip()
            dora_text = _tiles_field_to_str(points_cfg.get("dora"), field_name="dora")
            seat_wind = str(points_cfg.get("seat_wind", "E")).strip()
            round_wind = str(points_cfg.get("round_wind", "E")).strip()
            riichi = bool(points_cfg.get("riichi", False))
            concealed_kong = bool(points_cfg.get("concealed_kong", False))
            concealed_kong_tile = str(points_cfg.get("concealed_kong_tile", "")).strip() or None
        except Exception as e:
            ap.error(f"Invalid points config: {e}")

        if win_type not in {"tsumo", "ron"}:
            ap.error("Points mode requires points.win_type = 'tsumo' or 'ron'.")
        if not win_tile:
            ap.error("Points mode requires points.win_tile (one tile like '5m' or '0p').")

        print("Points estimation")
        print(f"  win_type   : {win_type}")
        print(f"  win_tile   : {win_tile}")
        print(f"  is_dealer  : {'YES' if is_dealer else 'NO'}")
        print(f"  riichi     : {'YES' if riichi else 'NO'}")
        print(f"  ankan      : {'YES' if concealed_kong else 'NO'}")
        if concealed_kong:
            print(f"  ankan tile : {concealed_kong_tile}")
        print(f"  seat_wind  : {seat_wind}")
        print(f"  round_wind : {round_wind}")
        print(f"  dora       : {dora_text or '(none)'}")

        if len(parse_tiles(hand_str, keep_red_fives=True)) != 13:
            ap.error("In points mode, 'hand' must contain exactly 13 tiles (winning tile goes in points.win_tile).")

        try:
            sb = score_points_from_config(
                hand13_text=hand_str,
                win_tile_text=win_tile,
                win_type=win_type,
                is_dealer=is_dealer,
                dora_text=dora_text,
                seat_wind=seat_wind,
                round_wind=round_wind,
                riichi=riichi,
                concealed_kong=concealed_kong,
                concealed_kong_tile_text=concealed_kong_tile,
            )
        except Exception as e:
            ap.error(str(e))

        if sb.yakuman:
            names = ", ".join(f"{y.name} x{y.multiplier}" if y.multiplier != 1 else y.name for y in sb.yakuman)
            print(f"  Yakuman: {names}")
        if sb.yaku:
            print(f"  Yaku   : {', '.join(y.name for y in sb.yaku)}")
        if sb.fu is not None:
            print(f"  Han/Fu : {sb.han} han / {sb.fu} fu (dora {sb.dora_han}, aka {sb.aka_dora_han})")

        p = sb.points
        if getattr(p, "ron_points", None) is not None:
            print(f"  Ron    : {p.ron_points}")
        if getattr(p, "tsumo_total_points", None) is not None:
            if sb.is_dealer:
                print(f"  Tsumo  : each pays {p.tsumo_dealer_points} (total {p.tsumo_total_points})")
            else:
                print(
                    f"  Tsumo  : dealer pays {p.tsumo_dealer_points}, others pay {p.tsumo_non_dealer_points} "
                    f"(total {p.tsumo_total_points})"
                )
        print()

    print("Remaining tiles (nonzero)")
    print(f"  {counter.pretty_remaining(only_nonzero=True)}")


if __name__ == "__main__":
    main()

