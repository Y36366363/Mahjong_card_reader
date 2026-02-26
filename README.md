# Mahjong Card Reader (Riichi Mahjong)

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
    "concealed_kong": false,
    "concealed_kong_tile": "5m",
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
- `concealed_kong`: `true/false` (ankan)
- `concealed_kong_tile`: one tile (required if `concealed_kong=true`). The hand must contain exactly 3 copies across (hand + win_tile); the 4th copy is implied by the kan for fu/dora counting.
- `dora`: list of dora tiles (e.g. `["3m","7p"]`) (tiles, not indicators)
- `seat_wind`: `"E"|"S"|"W"|"N"` (optional; default `"E"`)
- `round_wind`: `"E"|"S"|"W"|"N"` (optional; default `"E"`)

In points mode, `hand` must be exactly 13 tiles. Red fives should be written as `0m/0p/0s` and are automatically counted as aka-dora.

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
concealed_kong = false
concealed_kong_tile = "5m"
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

