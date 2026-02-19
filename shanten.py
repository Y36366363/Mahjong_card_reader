from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Iterable

from tiles import TERMINAL_HONOR_INDICES, tiles_to_counts


@dataclass(frozen=True)
class ShantenResult:
    standard: int
    chiitoitsu: int
    kokushi: int

    @property
    def minimum(self) -> int:
        return min(self.standard, self.chiitoitsu, self.kokushi)


def calculate_shanten_all(hand_tiles: list[str]) -> ShantenResult:
    counts = tiles_to_counts(hand_tiles)
    return ShantenResult(
        standard=shanten_standard(counts),
        chiitoitsu=shanten_chiitoitsu(counts),
        kokushi=shanten_kokushi(counts),
    )


def _total_tiles(counts: Iterable[int]) -> int:
    return int(sum(counts))


def shanten_chiitoitsu(counts: list[int]) -> int:
    pairs = sum(c // 2 for c in counts)
    pairs = min(pairs, 7)
    unique = sum(1 for c in counts if c > 0)
    need_unique = max(0, 7 - unique)
    return 6 - pairs + need_unique


def shanten_kokushi(counts: list[int]) -> int:
    unique = sum(1 for i in TERMINAL_HONOR_INDICES if counts[i] > 0)
    has_pair = any(counts[i] >= 2 for i in TERMINAL_HONOR_INDICES)
    return 13 - unique - (1 if has_pair else 0)


def shanten_standard(counts: list[int]) -> int:
    total = _total_tiles(counts)
    if total == 14:
        best = 8
        for i in range(34):
            if counts[i] <= 0:
                continue
            counts[i] -= 1
            best = min(best, shanten_standard(counts))
            counts[i] += 1
        return best
    return _shanten_standard_general(tuple(counts))


@lru_cache(maxsize=200_000)
def _shanten_standard_general(counts_t: tuple[int, ...]) -> int:
    best = 8

    @lru_cache(maxsize=400_000)
    def dfs(state: tuple[int, ...], mentsu: int, taatsu: int, pair_used: int) -> int:
        nonlocal best
        if mentsu > 4:
            return 999

        taatsu_slots = max(0, 4 - mentsu)
        effective_taatsu = min(taatsu, taatsu_slots)
        sh = 8 - 2 * mentsu - effective_taatsu - pair_used
        if sh < best:
            best = sh

        counts_local = list(state)
        i = next((idx for idx, c in enumerate(counts_local) if c), -1)
        if i == -1:
            return sh

        res = sh

        def call_next() -> None:
            nonlocal res
            res = min(res, dfs(tuple(counts_local), mentsu, taatsu, pair_used))

        # Skip one tile (treat as isolated)
        counts_local[i] -= 1
        call_next()
        counts_local[i] += 1

        # Triplet
        if counts_local[i] >= 3:
            counts_local[i] -= 3
            res = min(res, dfs(tuple(counts_local), mentsu + 1, taatsu, pair_used))
            counts_local[i] += 3

        # Sequence
        if i <= 26:
            base = (i // 9) * 9
            pos = i - base
            if pos <= 6 and counts_local[i + 1] > 0 and counts_local[i + 2] > 0:
                counts_local[i] -= 1
                counts_local[i + 1] -= 1
                counts_local[i + 2] -= 1
                res = min(res, dfs(tuple(counts_local), mentsu + 1, taatsu, pair_used))
                counts_local[i] += 1
                counts_local[i + 1] += 1
                counts_local[i + 2] += 1

        # Pair as head
        if pair_used == 0 and counts_local[i] >= 2:
            counts_local[i] -= 2
            res = min(res, dfs(tuple(counts_local), mentsu, taatsu, 1))
            counts_local[i] += 2

        # Taatsu
        if taatsu < 4:
            if counts_local[i] >= 2:
                counts_local[i] -= 2
                res = min(res, dfs(tuple(counts_local), mentsu, taatsu + 1, pair_used))
                counts_local[i] += 2

            if i <= 26:
                base = (i // 9) * 9
                pos = i - base
                if pos <= 7 and counts_local[i + 1] > 0:
                    counts_local[i] -= 1
                    counts_local[i + 1] -= 1
                    res = min(res, dfs(tuple(counts_local), mentsu, taatsu + 1, pair_used))
                    counts_local[i] += 1
                    counts_local[i + 1] += 1

                if pos <= 6 and counts_local[i + 2] > 0:
                    counts_local[i] -= 1
                    counts_local[i + 2] -= 1
                    res = min(res, dfs(tuple(counts_local), mentsu, taatsu + 1, pair_used))
                    counts_local[i] += 1
                    counts_local[i + 2] += 1

        return res

    dfs(counts_t, 0, 0, 0)
    return best

