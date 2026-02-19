from __future__ import annotations

import argparse

from remaining import RemainingTileCounter
from shanten import calculate_shanten_all
from tenpai import tenpai_waits_for_13
from tiles import parse_tiles, tiles_to_counts


def main() -> None:
    ap = argparse.ArgumentParser(description="Riichi Mahjong: shanten + tenpai waits + remaining tiles")
    ap.add_argument("--hand", type=str, required=True, help="Hand tiles (13 or 14), e.g. '1m 2m 3m E E ...'")
    ap.add_argument("--river", type=str, default=None, help="River/discards tiles, space-separated")
    args = ap.parse_args()

    hand_tiles = parse_tiles(args.hand)
    river_tiles = parse_tiles(args.river) if args.river else []

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

