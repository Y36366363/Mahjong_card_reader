from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from remaining import RemainingTileCounter
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

    hand_str = args.hand if args.hand is not None else _tiles_field_to_str(config.get("hand"), field_name="hand")
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
    print(f"  Hand  ({len(hand_tiles)}): {' '.join(hand_tiles)}")
    print(f"  River ({len(river_tiles)}): {' '.join(river_tiles)}")
    print()

    print("Shanten")
    print(f"  Standard   : {sh.standard}")
    print(f"  Chiitoitsu : {sh.chiitoitsu}")
    print(f"  Kokushi    : {sh.kokushi}")
    print(f"  Minimum    : {sh.minimum}")
    print()

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

    print("Remaining tiles (nonzero)")
    print(f"  {counter.pretty_remaining(only_nonzero=True)}")


if __name__ == "__main__":
    main()

