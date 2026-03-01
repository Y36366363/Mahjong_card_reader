from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from remaining import RemainingTileCounter
from scoring import score_points_from_config
from shanten import calculate_shanten_all
from tenpai import tenpai_waits_for_13
from tiles import index_to_tile, parse_tiles, tile_to_index, tiles_to_counts


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


def _tiles_field_to_list(value: Any, *, field_name: str) -> list[str]:
    s = _tiles_field_to_str(value, field_name=field_name)
    if not s:
        return []
    return parse_tiles(s, keep_red_fives=True)


def _tile_sort_key(tile: str) -> tuple[int, int]:
    if len(tile) == 2 and tile[1] in ("m", "p", "s"):
        suit_order = {"m": 0, "p": 1, "s": 2}[tile[1]]
        return (suit_order, int(tile[0]))
    honor_order = {"E": 3, "S": 4, "W": 5, "N": 6, "P": 7, "F": 8, "C": 9}
    return (honor_order.get(tile, 99), 0)


def _ura_dora_next_idx(idx: int) -> int:
    """Index of ura-dora tile when the indicator is tile at idx. E.g. 8m->9m, 9m->1m, E->S, C->E."""
    if idx < 27:  # suited
        return (idx // 9) * 9 + (idx % 9 + 1) % 9
    return 27 + ((idx - 27) + 1) % 7  # honors


def _compute_ura_dora(hand_counts: list[int], remaining_counts: list[int], num_ura_indicators: int) -> tuple[float, float]:
    """
    Returns (ura_dora_rate, expected_ura_dora).
    - ura_dora_rate: proportion of remaining tiles that, as indicators, would give at least 1 ura-dora han.
    - expected_ura_dora: expected total ura-dora han across all indicators.
    """
    total = sum(remaining_counts)
    if total <= 0:
        return (0.0, 0.0)
    rate = 0.0
    expected_per_ind = 0.0
    for i in range(34):
        ura_idx = _ura_dora_next_idx(i)
        if hand_counts[ura_idx] > 0:
            rate += remaining_counts[i] / total
        expected_per_ind += (remaining_counts[i] / total) * hand_counts[ura_idx]
    return (rate, expected_per_ind * num_ura_indicators)


def _draws_to_reach_tenpai(hand13_tiles: list[str]) -> list[str]:
    """
    For a 13-tile hand, return draw tiles which allow reaching tenpai
    after drawing 1 tile and discarding 1 tile.
    """
    counts13 = tiles_to_counts(hand13_tiles)
    good_draws: list[str] = []
    for draw_idx in range(34):
        if counts13[draw_idx] >= 4:
            continue
        counts14 = counts13.copy()
        counts14[draw_idx] += 1
        can_reach = False
        for discard_idx in range(34):
            if counts14[discard_idx] <= 0:
                continue
            counts13p = counts14.copy()
            counts13p[discard_idx] -= 1
            if tenpai_waits_for_13(counts13p).is_tenpai:
                can_reach = True
                break
        if can_reach:
            good_draws.append(index_to_tile(draw_idx))
    good_draws.sort(key=_tile_sort_key)
    return good_draws


def _validate_no_more_than_four(tiles: list[str]) -> list[tuple[str, int]]:
    counts = [0] * 34
    for t in tiles:
        counts[tile_to_index(t)] += 1
    over: list[tuple[str, int]] = []
    for i, c in enumerate(counts):
        if c > 4:
            over.append((index_to_tile(i), c))
    over.sort(key=lambda x: _tile_sort_key(x[0]))
    return over


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

    # Validate impossible inputs (more than 4 copies of a tile).
    used_for_validation = hand_tiles + river_tiles
    if mode == "points":
        points_cfg = config.get("points", config)
        win_tile_str = str(points_cfg.get("win_tile", "")).strip()
        if not win_tile_str:
            ap.error("Points mode requires points.win_tile (one tile like '5m' or '0p').")
        win_tiles = parse_tiles(win_tile_str)
        if len(win_tiles) != 1:
            ap.error("Points mode requires points.win_tile to be exactly one tile.")
        used_for_validation = used_for_validation + win_tiles

    over = _validate_no_more_than_four(used_for_validation)
    if over:
        msg = ", ".join(f"{tile}:{count}" for tile, count in over)
        ap.error(f"Invalid case: more than 4 copies of a tile were provided ({msg}).")

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
        elif sh.minimum == 1:
            draws = _draws_to_reach_tenpai(hand_tiles)
            print("  One draw to tenpai (draw + discard)")
            print(f"    {' '.join(draws) if draws else '(none)'}")
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
            furo_sets = int(points_cfg.get("furo_sets", 0))
            kan_sets = int(points_cfg.get("kan_sets", 0))
            ankan_tiles = _tiles_field_to_list(points_cfg.get("ankan_tiles"), field_name="ankan_tiles")
            kan_tiles = _tiles_field_to_list(points_cfg.get("kan_tiles"), field_name="kan_tiles")

            # Backward compatibility: old single-ankan fields
            if not ankan_tiles:
                old_ankan = bool(points_cfg.get("ankan", points_cfg.get("concealed_kong", False)))
                old_ankan_tile = str(points_cfg.get("ankan_tile", points_cfg.get("concealed_kong_tile", ""))).strip()
                if old_ankan and old_ankan_tile:
                    ankan_tiles = parse_tiles(old_ankan_tile, keep_red_fives=True)
        except Exception as e:
            ap.error(f"Invalid points config: {e}")

        if win_type not in {"tsumo", "ron"}:
            ap.error("Points mode requires points.win_type = 'tsumo' or 'ron'.")
        if not win_tile:
            ap.error("Points mode requires points.win_tile (one tile like '5m' or '0p').")

        # Remaining tiles should also exclude the winning tile.
        counter.set_used_tiles(hand_tiles + river_tiles + parse_tiles(win_tile))

        print("Points estimation")
        print(f"  win_type   : {win_type}")
        print(f"  win_tile   : {win_tile}")
        print(f"  is_dealer  : {'YES' if is_dealer else 'NO'}")
        print(f"  riichi     : {'YES' if riichi else 'NO'}")
        print(f"  furo_sets  : {furo_sets}")
        print(f"  kan_sets   : {kan_sets}")
        print(f"  ankan_tiles: {' '.join(ankan_tiles) if ankan_tiles else '(none)'}")
        print(f"  kan_tiles  : {' '.join(kan_tiles) if kan_tiles else '(none)'}")
        print(f"  seat_wind  : {seat_wind}")
        print(f"  round_wind : {round_wind}")
        print(f"  dora       : {dora_text or '(none)'}")

        hand_len = len(parse_tiles(hand_str, keep_red_fives=True))
        expected_len = 13 + len(ankan_tiles) + len(kan_tiles)
        if hand_len != expected_len:
            ap.error(
                f"In points mode, 'hand' must contain exactly {expected_len} tiles (13 + total_kans). "
                "Put furo tiles at the end, and put the winning tile in points.win_tile."
            )

        try:
            sb = score_points_from_config(
                hand_text=hand_str,
                win_tile_text=win_tile,
                win_type=win_type,
                is_dealer=is_dealer,
                dora_text=dora_text,
                seat_wind=seat_wind,
                round_wind=round_wind,
                riichi=riichi,
                furo_sets=furo_sets,
                kan_sets=kan_sets,
                ankan_tiles=ankan_tiles,
                kan_tiles=kan_tiles,
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

        # Ura-dora prediction (only when riichi would apply; ura exists for riichi wins)
        num_ura_indicators = 1 + len(ankan_tiles) + len(kan_tiles)
        hand_counts = tiles_to_counts(sb.full_normalized)
        remaining_counts = counter.remaining_counts()
        ura_rate, expected_ura = _compute_ura_dora(hand_counts, remaining_counts, num_ura_indicators)
        print(f"  Ura-dora rate     : {ura_rate:.1%}  (prob. an indicator yields ura-dora)")
        print(f"  Expected ura-dora : {expected_ura:.2f} han  ({num_ura_indicators} indicator(s))")
        print()

    print("Remaining tiles (including zeros)")
    print(f"  {counter.pretty_remaining(only_nonzero=False)}")


if __name__ == "__main__":
    main()

