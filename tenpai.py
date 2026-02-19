from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from tiles import TERMINAL_HONOR_INDICES, index_to_tile


@dataclass(frozen=True)
class TenpaiWaits:
    is_tenpai: bool
    standard_waits: list[str]
    chiitoi_waits: list[str]
    kokushi_waits: list[str]

    @property
    def all_waits(self) -> list[str]:
        s = set(self.standard_waits) | set(self.chiitoi_waits) | set(self.kokushi_waits)
        return sorted(s, key=_tile_sort_key)


def _tile_sort_key(tile: str) -> tuple[int, int]:
    if len(tile) == 2 and tile[1] in ("m", "p", "s"):
        suit_order = {"m": 0, "p": 1, "s": 2}[tile[1]]
        return (suit_order, int(tile[0]))
    honor_order = {"E": 3, "S": 4, "W": 5, "N": 6, "P": 7, "F": 8, "C": 9}
    return (honor_order.get(tile, 99), 0)


def is_agari_chiitoitsu(counts14: list[int]) -> bool:
    return sum(counts14) == 14 and sum(c // 2 for c in counts14) == 7


def is_agari_kokushi(counts14: list[int]) -> bool:
    if sum(counts14) != 14:
        return False
    unique = sum(1 for i in TERMINAL_HONOR_INDICES if counts14[i] > 0)
    if unique != 13:
        return False
    return any(counts14[i] >= 2 for i in TERMINAL_HONOR_INDICES)


def is_agari_standard(counts14: list[int]) -> bool:
    if sum(counts14) != 14:
        return False

    for pair_idx in range(34):
        if counts14[pair_idx] < 2:
            continue
        counts = counts14.copy()
        counts[pair_idx] -= 2
        if _honors_ok(counts) and _suits_ok(counts):
            return True
    return False


def _honors_ok(counts: list[int]) -> bool:
    return all(counts[i] % 3 == 0 for i in range(27, 34))


def _suits_ok(counts: list[int]) -> bool:
    return _suit_meldable(tuple(counts[0:9])) and _suit_meldable(tuple(counts[9:18])) and _suit_meldable(tuple(counts[18:27]))


@lru_cache(maxsize=50_000)
def _suit_meldable(counts9: tuple[int, ...]) -> bool:
    i = next((idx for idx, c in enumerate(counts9) if c), -1)
    if i == -1:
        return True
    c = list(counts9)

    if c[i] >= 3:
        c[i] -= 3
        if _suit_meldable(tuple(c)):
            return True
        c[i] += 3

    if i <= 6 and c[i + 1] > 0 and c[i + 2] > 0:
        c[i] -= 1
        c[i + 1] -= 1
        c[i + 2] -= 1
        if _suit_meldable(tuple(c)):
            return True

    return False


def tenpai_waits_for_13(counts13: list[int]) -> TenpaiWaits:
    if sum(counts13) != 13:
        raise ValueError("tenpai_waits_for_13 expects exactly 13 tiles.")

    standard: list[str] = []
    chiitoi: list[str] = []
    kokushi: list[str] = []

    for i in range(34):
        if counts13[i] >= 4:
            continue
        c14 = counts13.copy()
        c14[i] += 1
        if is_agari_standard(c14):
            standard.append(index_to_tile(i))
        if is_agari_chiitoitsu(c14):
            chiitoi.append(index_to_tile(i))
        if is_agari_kokushi(c14):
            kokushi.append(index_to_tile(i))

    standard.sort(key=_tile_sort_key)
    chiitoi.sort(key=_tile_sort_key)
    kokushi.sort(key=_tile_sort_key)
    return TenpaiWaits(
        is_tenpai=bool(standard or chiitoi or kokushi),
        standard_waits=standard,
        chiitoi_waits=chiitoi,
        kokushi_waits=kokushi,
    )

