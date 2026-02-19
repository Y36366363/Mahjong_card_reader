from __future__ import annotations

from dataclasses import dataclass

from tiles import index_to_tile, tile_to_index


@dataclass
class RemainingTileCounter:
    used_counts: list[int]

    def __init__(self) -> None:
        self.used_counts = [0] * 34

    def reset(self) -> None:
        self.used_counts = [0] * 34

    def add_used_tiles(self, tiles: list[str]) -> None:
        for t in tiles:
            self.used_counts[tile_to_index(t)] += 1

    def set_used_tiles(self, tiles: list[str]) -> None:
        self.reset()
        self.add_used_tiles(tiles)

    def remaining_counts(self) -> list[int]:
        return [max(0, 4 - u) for u in self.used_counts]

    def pretty_remaining(self, only_nonzero: bool = True) -> str:
        rem = self.remaining_counts()
        parts: list[str] = []
        for i, c in enumerate(rem):
            if only_nonzero and c == 0:
                continue
            parts.append(f"{index_to_tile(i)}:{c}")
        return " ".join(parts)

