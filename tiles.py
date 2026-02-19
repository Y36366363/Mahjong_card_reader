from __future__ import annotations

TILE_INDICES: dict[str, int] = {}

# Suits (0..26): m(0-8), p(9-17), s(18-26)
for suit_offset, suit in [(0, "m"), (9, "p"), (18, "s")]:
    for n in range(1, 10):
        TILE_INDICES[f"{n}{suit}"] = suit_offset + (n - 1)

# Honors (27..33)
HONOR_NAMES: list[str] = ["E", "S", "W", "N", "P", "F", "C"]  # winds + (white, green, red)
for i, name in enumerate(HONOR_NAMES):
    TILE_INDICES[name] = 27 + i

_INDEX_TO_TILE: list[str] = [""] * 34
for k, v in TILE_INDICES.items():
    _INDEX_TO_TILE[v] = k

TERMINAL_HONOR_INDICES: tuple[int, ...] = (
    0,
    8,
    9,
    17,
    18,
    26,
    27,
    28,
    29,
    30,
    31,
    32,
    33,
)


def normalize_tile(tile: str) -> str:
    """
    Normalize a tile string to canonical form.

    Accepted:
      - Suits: 1m..9m, 1p..9p, 1s..9s
      - Red fives: 0m/0p/0s -> 5m/5p/5s
      - Honors: E S W N P F C
    """
    t = tile.strip()
    if not t:
        raise ValueError("Empty tile token.")
    if len(t) == 2 and t[0] == "0" and t[1] in ("m", "p", "s"):
        return f"5{t[1]}"
    return t


def tile_to_index(tile: str) -> int:
    t = normalize_tile(tile)
    try:
        return TILE_INDICES[t]
    except KeyError as e:
        raise ValueError(f"Unknown tile token: {tile!r}") from e


def index_to_tile(idx: int) -> str:
    if not (0 <= idx < 34):
        raise ValueError(f"Tile index out of range: {idx}")
    return _INDEX_TO_TILE[idx]


def parse_tiles(text: str) -> list[str]:
    """
    Parse a space-separated tile string into canonical tokens.

    Example:
      "1m 2m 3m E E 0p" -> ["1m","2m","3m","E","E","5p"]
    """
    tokens = [tok for tok in text.replace(",", " ").split() if tok.strip()]
    return [normalize_tile(tok) for tok in tokens]


def tiles_to_counts(tiles: list[str]) -> list[int]:
    counts = [0] * 34
    for t in tiles:
        counts[tile_to_index(t)] += 1
    return counts

