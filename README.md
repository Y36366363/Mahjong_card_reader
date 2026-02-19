# Mahjong Card Reader (Riichi Mahjong)

This project computes Riichi Mahjong outputs from **formatted tile text inputs**, including:

- Standard hands (4 melds + 1 pair)
- Seven pairs (chiitoitsu)
- Thirteen orphans (kokushi musou)

It also tracks remaining tile counts (tiles unseen in your hand + river).

## Folder structure

```
Mahjong_card_reader/
  main.py
  tiles.py
  shanten.py
  tenpai.py
  remaining.py
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

```bash
python main.py --hand "1m 1m 1m 2m 3m 4p 5p 6p 7s 8s 9s E E"
```

## Tile notation

- Suits: `1m..9m`, `1p..9p`, `1s..9s`
- Winds: `E S W N`
- Dragons: `P F C` (white/green/red)

Red fives are accepted as `0m 0p 0s` and are treated as normal 5s for shanten/counting.

