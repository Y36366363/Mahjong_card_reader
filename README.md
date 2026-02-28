# Mahjong Card Reader (Riichi Mahjong)

## Updates 2/28/2026

- Tenpai mode enhancement: when `Tenpai: NO` but **minimum shanten = 1**, the program now lists **which draw tile(s)** can reach tenpai after **one draw + one discard**.
- Added **invalid-case validation**: if any tile appears **more than 4 times** across inputs (e.g. `9m:5`), the run stops and reports the invalid tile counts instead of computing results.
- Remaining tiles output is now more explicit:
  - In points mode, `points.win_tile` is removed from remaining tiles.
  - Remaining tiles include **zeros** (e.g. `9m:0`).

## Updates 2/27/2026

- Added **Furo (open-hand) support** in points mode:
  - `points.furo_sets` controls how many meld sets at the end of `hand` are treated as open melds.
  - `points.kan_sets` controls how many of those open melds are kans.
- Upgraded kan handling to support **multiple kans**:
  - `points.ankan_tiles` (concealed kans) and `points.kan_tiles` (open kans).
  - Added **Sankantsu** (Three Kans) and **Suukantsu** yakuman (Four Kans).
- Updated scoring rules for **open vs closed** hands (e.g. riichi/menzen-tsumo/pinfu restrictions and open/closed han differences for flushes).
- Remaining tiles output fixes:
  - In points mode, `points.win_tile` is also removed from remaining tiles.
  - Remaining tiles now include **zeros** (e.g. `9m:0`).

## Updates 2/26/2026

- Added config-driven **modes**: `tenpai` (analysis) and `points` (scoring).
- Added **points estimation** for `ron` / `tsumo`, including **dealer/non-dealer** payment differences.
- Added scoring options: **`riichi`** (+1 han) and **one concealed kong (ankan)** with fu adjustment.
- Added **“Ron requires yaku”** enforcement (dora/aka-dora do not count as yaku).
- Red fives are supported as `0m/0p/0s` and counted as **aka-dora** in points mode.

This project computes Riichi Mahjong outputs from **formatted tile text inputs**, including:

- Standard hands (4 melds + 1 pair)
- Seven pairs (chiitoitsu)
- Thirteen orphans (kokushi musou)

It also tracks remaining tile counts (tiles unseen in your hand + river).

## Modes

- **`tenpai`**: shanten + tenpai waits + remaining tiles.
- **`points`**: estimate Ron/Tsumo points for a winning hand, using:
  - `hand` (exactly 13 tiles)
  - `points.win_tile` (the winning tile)
  - `points.win_type` (`"ron"` or `"tsumo"`)
  - optional: dora / riichi / ankan

Notes/assumptions for `points` mode (current implementation):
- Hands are treated as **closed (menzen)**.
- Dora is provided as **dora tiles** (not indicators).
- Supported yaku set is partial (includes common yaku + some yakuman); extendable in `scoring.py`.
- Supports at most **one concealed kong (ankan)** via config.

## Folder structure

```
Mahjong_card_reader/
  default_config.json
  main.py
  tiles.py
  shanten.py
  tenpai.py
  remaining.py
  points.py
  scoring.py
  requirements.txt
  README.md
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Quick start

Tenpai analysis:

```bash
python main.py --hand "1m 1m 1m 2m 3m 4p 5p 6p 7s 8s 9s E E"
```

## Using a config file (recommended)

You can store your inputs in a config file and run without typing long tile strings each time.

- `default_config.json` is auto-loaded if you run `python main.py` with no `--hand`.
- Or pass a config path explicitly with `--config` / `-c`.

### JSON example

`default_config.json`:

```json
{
  "mode": "tenpai",
  "hand": "1m 1m 1m 2m 3m 4p 5p 6p 7s 8s 9s E E",
  "river": "9m 9m 9m",
  "points": {
    "win_type": "tsumo",
    "win_tile": "5m",
    "is_dealer": false,
    "riichi": true,
    "ankan": false,
    "ankan_tile": "5m",
    "dora": ["5m"]
  }
}
```

Run:

```bash
python main.py
```

Or:

```bash
python main.py -c default_config.json
```

## Points estimation mode

Set `"mode": "points"` and configure `"points"`:

- `win_type`: `"ron"` or `"tsumo"`
- `win_tile`: the winning tile (one tile, e.g. `"5m"` or `"0p"`)
- `is_dealer`: `true/false`
- `riichi`: `true/false` (adds 1 han if true)
- `furo_sets`: number of open meld sets (furo) in `hand` (0..4). These meld tiles must be placed at the very end of `hand`.
- `kan_sets`: number of open kan melds among the furo sets. These are assumed to be the last `kan_sets` sets in the furo block.
- `ankan_tiles`: list of concealed kan tiles (each entry is one tile name). Example: `["1m","9s"]`
- `kan_tiles`: list of open kan tiles (each entry is one tile name). Example: `["5p"]`
- `dora`: list of dora tiles (e.g. `["3m","7p"]`) (tiles, not indicators)
- `seat_wind`: `"E"|"S"|"W"|"N"` (optional; default `"E"`)
- `round_wind`: `"E"|"S"|"W"|"N"` (optional; default `"E"`)

In points mode, `hand` must be exactly \(13 + \text{total_kans}\) tiles (excluding `win_tile`), where `total_kans = len(ankan_tiles) + len(kan_tiles)`.
Red fives should be written as `0m/0p/0s` and are automatically counted as aka-dora.

### TOML example (Python 3.11+)

```toml
mode = "tenpai"
hand = "1m 1m 1m 2m 3m 4p 5p 6p 7s 8s 9s E E"
river = "9m 9m 9m"

[points]
win_type = "tsumo"
win_tile = "5m"
is_dealer = false
riichi = true
furo_sets = 0
kan_sets = 0
ankan_tiles = []
kan_tiles = []
dora = ["5m"]
seat_wind = "E"
round_wind = "E"
```

Run:

```bash
python main.py -c my_config.toml
```

## Tile notation

- Suits: `1m..9m`, `1p..9p`, `1s..9s`
- Winds: `E S W N`
- Dragons: `P F C` (white/green/red)

Red fives are accepted as `0m 0p 0s` and are treated as normal 5s for shanten/counting.

