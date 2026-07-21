# Mahjong Card Reader (Riichi Mahjong)

## Updates 7/21/2026

- Added East-match and South-match selection to the desktop setup, CLI (`--match-length east|south`), JSON configuration (`game.match_length`), and desktop simulation tool.
- Added 30,000-point extension rules. An East match enters South if the leader is below 30,000 after East 4; a South match enters West if the leader is below 30,000 after South 4. During extension, the result is checked after every hand; West 4 is the safety cap.
- Corrected bankruptcy to trigger only below zero. A player on exactly zero remains in the match. Riichi remains legal at exactly 1,000 points and illegal below 1,000.
- Added true round-wind state throughout scoring, value-honor calls, AI hand valuation, table/settlement labels, and final results. South is therefore correctly treated as yakuhai during the South round.
- Updated Advanced AI v1 placement logic so final-hand push/fold and comeback decisions activate in the selected match's all-last and extension hands, rather than treating every East 4 as the end of a South match.
- Added round progression, South-round scoring, zero/negative-point, riichi affordability, desktop selection, and extension tests; the full suite now contains 61 passing tests. A fixed-seed East match was verified to enter South and finish with 100,000 total points.

## Updates 7/19/2026

- Added real in-match ura-dora scoring. Each shuffled dead wall now fixes parallel visible-dora and ura-dora indicators; ura-dora is revealed and counted only after a riichi player actually wins, including the additional indicator pairs revealed by kans.
- Split win handling into preview and final scoring. Ron/tsumo confirmation now shows the known yaku and visible/red dora but deliberately hides points; after acceptance, the engine reveals ura-dora, recalculates the final hand, and then displays yaku, dora, ura-dora, and points.
- Expanded the central hand-settlement card after a win to identify who ron'd whom or who tsumo'd, show the complete final yaku/point result and ura indicators, and reveal all four concealed hands plus their open melds. Exhaustive draws retain the simpler score-change settlement.
- Separated the four rinshan replacement tiles from the five dora/ura indicator pairs in the fixed dead wall, preventing a replacement draw from consuming an indicator tile.
- Added dedicated tests for riichi-only ura-dora, fixed dora/ura kan pairs, point-free win confirmation, final ura scoring, winner/loser relationships, four-hand reveal data, and the rendered desktop win overlay. The complete suite now contains 56 passing tests.
- Fixed the desktop `返回标题` action. It now safely unwinds the blocking game-input thread, ends the current match, and rebuilds the setup screen without closing the application. Closing the window remains a separate quit action.
- Added a prominent central settlement card after every hand. It identifies ron, tsumo, or exhaustive draw; names winners and deal-in players; shows all four score changes; states dealer continuation/rotation; and retains explicit confirmation before the next hand.
- Added a persistent final-match results card with ordered ranking, final points, wins, ron, tsumo, deal-ins, and riichi counts. The completed results remain visible until the player returns to the title screen.
- Added live seat-wind labels to all four player panels. Each panel prominently shows East/South/West/North relative to the current dealer and updates automatically after dealer rotation.
- Added structured hand-settlement and final-summary data to the game engine so the desktop UI does not need to parse human-readable log text.
- Verified 51 automated tests, hidden GUI checks for return-to-title and both result overlays, and complete fixed-seed Advanced AI v1 hint matches with active call decisions.

## Updates 7/18/2026

- Fixed stale desktop hints that could name a tile no longer present in the player's hand. Hint state now carries a hand snapshot, is recalculated when the live hand differs, and is rejected by a final membership guard before display.
- Kept the player's complete hand visible and full-color during every chi/pon/kan decision, with a permanent `当前手牌 / Your hand` heading so call choices can be evaluated without relying on memory.
- Made opponent riichi and calls conspicuous: a new public action triggers a large temporary table banner and sound, while riichi player panels remain red-highlighted and open-hand panels remain gold-highlighted.
- Added `小 / 中 / 大` desktop font sizing on the setup page. It scales table status, action controls, logs, hand tiles, and alert banners; tile widths adapt by size so a 14-tile hand and separated draw remain visible.
- Improved the desktop play view after hands-on testing: the latest drawn tile remains separated at the far right, opponent concealed-tile counts are rendered as tile backs, and Chinese tiles display as `东南西北白发中` plus `万/筒/索` labels without changing internal tile IDs.
- Added pre-discard riichi guidance. Every discard that leaves a legal closed tenpai is marked `可立直`; selecting it opens the existing explicit riichi yes/no confirmation.
- Extended hint mode to call opportunities. Pon, chi, and kan prompts now show whether Advanced AI v1 recommends accepting or passing, without changing the player's final choice or contaminating AI statistics.
- Clarified the currently supported kan prompt as **open kan / daiminkan / 大明杠**, explicitly stating that it uses an opponent discard. Closed kan and added kan remain future rule work.
- Added a scalable offline setup background with dark-green table felt, a warm frame, and restrained gold corner decoration. The controls remain high-contrast and the background requires no external asset or network access.
- Added display-helper regression tests and completed 10 automated Advanced AI v1 hint-mode East matches with active call choices, with no crashes, invalid point totals, or incomplete hint records.
- Integrated **Advanced AI v1** as a full-name desktop selection while retaining Basic AI v1. Blank desktop seeds now generate and display a secure random replay seed; manually entered seeds remain deterministic.
- Added `simulate_desktop_game.py` to complete East matches through the same discard, win, riichi, chi/pon/kan, pass, and settlement prompts used by the desktop UI.
- Promoted hint recommendations into the desktop action panel and highlight the recommended hand tile. Chi buttons now show only the legal sequences supplied by the engine.
- Fixed Chinese/Japanese hint tracker rows that were hidden by an indentation error; all four suit/honor remaining-count rows now display in every language.
- Completed 19 simulated desktop match runs in this update, including Advanced AI v1 hint games, Basic AI v1 normal games, fixed-seed replay, and active-call games, with no crashes or invalid point totals.
- Removed previously tracked Python bytecode caches from the repository. Existing `.gitignore` rules now keep regenerated `__pycache__`, `.pyc`, test/tool caches, virtual environments, and macOS metadata out of future commits.

## Updates 7/17/2026

- Removed committed Python bytecode caches and added `.gitignore` rules so future `__pycache__`, `.pyc`, test/tool caches, local virtual environments, and macOS metadata stay out of version control automatically.
- Corrected desktop table orientation: the human seat is fixed at the bottom, the opposite seat at the top, seat 3 on the left, and seat 1 on the right. Added a regression test for this perspective mapping and verified a live GUI discard updates the human river.
- Added the first playable desktop UI in `desktop_ui.py`, built with dependency-free Tkinter. It provides a setup screen, versioned AI selection, temperature/seed/assist settings, a four-seat table, live rivers/melds/scores, clickable hand tiles, action buttons, and a game log.
- Added a threaded compatibility adapter that turns the proven interactive engine prompts into GUI actions without duplicating Mahjong rules. This is an initial bridge toward a fully event-driven engine/UI split.
- Frozen the current computer policies as stable, reusable profiles: **Basic AI v1** and **Advanced AI v1**. Legacy `simple`/`advanced` names remain supported aliases.
- Added profile metadata for future UI selectors, including stable ID, display name, internal policy, recommended temperature, and description.
- Added advanced-AI quality telemetry for riichi wait quality/results/value, call shanten and ukeire gains, threatened-hand push/fold outcomes, and discard/riichi/call decision time.
- Extended benchmark JSON and console summaries with the new explainable quality metrics.
- Tightened value-honor calls that keep the same shanten: opening now requires a meaningful effective-tile gain instead of merely avoiding a large loss.
- Removed repeated shanten and tile-value work from advanced discard analysis; interactive decisions remain around tens of milliseconds on the current benchmark machine.
- A fixed-seed 12-match before/after check improved advanced-AI average points from 26,804 to 28,296 and average rank from 2.33 to 2.17. This is a diagnostic sample, not a statistically conclusive strength rating.
- Added constrained per-seat AI temperature (`0` to `1`). It randomizes only among near-equivalent, policy-safe discards, uses a decision RNG independent from the wall, and remains reproducible with a fixed seed.
- In a 72-match temperature comparison, average points were 26,685/26,729/26,679 at temperatures `0`/`0.2`/`0.5`. The guarded randomizer changed 4.2% of eligible decisions at `0.2` and 16.4% at `0.5`; aggregate strength stayed essentially flat, while `0.5` showed slightly more fourth-place variance. `0.2` is the recommended default for light style variety.

## Updates 7/16/2026

- Replaced the advanced AI's binary push/fold switch with three explainable modes: `push`, `balanced`, and `fold`.
- Added dealer-threat, dora, near-dora, one-chance, late-round, multi-riichi, rank, shanten, and remaining-ukeire context to defensive decisions.
- Added `advanced_discard_report()` with per-candidate shanten, ukeire, danger score, safety/danger tags, and selected decision mode; hint mode now shows the top candidates.
- Fixed tied-score rank handling: players now receive stable unique current ranks instead of all treating themselves as first place.
- Added open-meld tendency reads (flush/toitoi), estimated opponent hand value, and stronger dealer/late-round threat weighting.
- Added an explicit riichi decision layer using wait quality, visible remaining tiles, estimated hand value, dama yaku, chase-riichi pressure, current rank/score gaps, East-4 comeback requirements, and remaining wall size.

## Updates 7/15/2026

- Added a dedicated advanced-AI behavior test suite covering tile efficiency, visible-tile ukeire, dora/value retention, genbutsu, suji, walls, honor safety, multi-riichi risk, rank-aware folding, yaku-safe calls, closed-tenpai preservation, and conservative kan rules.
- Advanced AI visible-tile estimates now include public dora indicators.
- Advanced AI now preserves a closed tenpai riichi route instead of opening for a value honor, and rejects an equal-shanten kan when it reduces effective remaining tiles.
- Extracted rank/shanten folding policy into a directly testable decision function.
- Added `benchmark_ai.py` for reproducible, seat-rotated comparisons of 1-advanced/3-simple, 2-advanced/2-simple, and 3-advanced/1-simple lineups, with console summaries and detailed JSON output.
- Completed a 72-match/409-hand balanced benchmark (24 matches per lineup): advanced AI averaged 26,790 points and 2.29 rank versus simple AI's 23,210 points and 2.71 rank, with 202 versus 118 wins and 79 versus 162 deal-ins.

## Updates 7/13/2026

- Reworked the interactive player view: every discard shows the hand, draw, all four rivers, scores, dealer, riichi, and each player's open-meld count.
- Split call prompts by action: pon and kan use yes/no prompts, while chi lists every legal sequence separately.
- Added **normal** and **hint** modes. Hint mode shows current shanten, an advanced-AI discard recommendation, effective tile types/counts, and the existing remaining-tile tracker grouped by suit.
- Added a hand-settlement screen with score changes and dealer continuation/rotation; interactive games wait for confirmation before starting the next hand.
- Added final match statistics for hands, wins, ron, tsumo, deal-ins, riichi, chi, pon, and kan.
- Added `language = "en" | "zh" | "ja"` for game mode. Localized modes cover game prompts, player status, calls, wins, draws, settlements, rankings, statistics, and yaku names.
- Added Japanese game localization with `language = "ja"`, following the same configuration and interaction flow as Chinese mode.

## Updates 7/12/2026

- Added an interactive **East-round game simulation** with four players, fixed walls after each hand's initial shuffle, dealer continuations, honba, riichi sticks, early bankruptcy settlement, and final ranking.
- Added **furiten rules** in game mode:
  - A player cannot ron when any current winning tile appears in their own river.
  - Passing a valid ron causes temporary furiten until the player's next draw.
  - Passing ron after riichi causes furiten for the rest of the hand.
  - Furiten never prevents tsumo.
- The player view now displays all four rivers before every player-controlled discard and shows the current furiten reason when applicable.
- Game-mode wins continue to use the existing yaku and point calculation system; AI players normally pursue riichi and only open value-honor melds.
- Preserved the original shanten-only policy as **simple AI** and added an **advanced AI** that evaluates remaining improvements, wait breadth, dora and value-honor retention, genbutsu, suji, walls, honor safety, score/rank-based folding, and conservative call/kan value.
- Improved full-game simulation after two end-to-end East-round test matches:
  - Riichi hands are now locked and automatically discard every non-winning draw.
  - Exhaustive draws now exchange the standard 3,000-point tenpai/noten payment.
  - Open kans now draw a replacement tile, shorten the live wall, and reveal an additional dora indicator.
  - Discards made immediately after chi/pon/kan now go through the normal multi-ron and furiten checks.
  - `--auto-game` no longer prints the player hand and all rivers every turn, greatly reducing simulation output.
  - In `--auto-game`, the `You` seat now uses the same riichi and value-honor call policy as the other three AIs, making batch comparisons fair.
  - Any unclaimed riichi sticks at the end of the match are awarded to the current first-place player, preserving the 100,000-point total.

## Updates 3/02/2026

- Added **estimated points** when `riichi` is true (points mode, non-yakuman hands):
  - **Estimated Ron** or **Estimated Tsumo** (matches `win_type`) — expected total points weighted by ura-dora probability distribution.
  - Formula: P(0)×pts(0 ura) + P(1)×pts(1 ura) + P(2)×pts(2 ura) + P(3)×pts(3 ura) + P(4+)×pts(4 ura).
  - Ura-dora distribution P(0), P(1), P(2), P(3), P(4+) is computed from remaining tile counts and hand composition (e.g., triplets increase P(3) when the ura tile matches).

## Updates 3/01/2026

- Added **ura-dora prediction** in points mode (only when `riichi` is true; no ura is counted when riichi=false):
  - **Ura-dora rate**: proportion of remaining tiles that, when revealed as ura-dora indicators, would give at least 1 ura-dora han.
  - **Expected ura-dora**: expected number of ura-dora han, accounting for multiple copies in hand (e.g., 3×9m with indicator 8m yields 3 ura-dora).
  - Number of ura-dora indicators = 1 + number of kans.

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
- **`game`**: play a complete East or South match against three shanten-driven AIs.

## East/South match simulation

Start an interactive game (you are always `You`; enter a tile or its displayed index):

```bash
python main.py --mode game --seed 2026
```

The game asks for normal or hint mode at startup. It can also be selected directly:

```bash
python main.py --mode game --seed 2026 --assist-mode hint
```

Set the display language at the root of `default_config.json`:

```json
{
  "mode": "game",
  "language": "zh",
  "game": {
    "assist_mode": "hint",
    "match_length": "south",
    "ai_levels": ["basic_v1", "advanced_v1", "advanced_v1", "basic_v1"]
  }
}
```

Or override it from the command line:

```bash
python main.py --mode game --language zh --assist-mode hint
```

Japanese mode:

```bash
python main.py --mode game --language ja --assist-mode hint
```

Choose the four computer levels in seat order (`You,AI-1,AI-2,AI-3`):

```bash
python main.py --mode game --auto-game --seed 2026 \
  --ai-levels advanced_v1,basic_v1,advanced_v1,basic_v1
```

Run the deterministic AI regression tests with:

```bash
python -m unittest test_game_ai.py
```

Use `--auto-game` for a hands-off smoke test. A wall is shuffled once at the start
of each hand and is deterministic thereafter; the same seed plus the same choices
replays the same walls. The match uses 25,000 starting points, selectable East-only
or East+South regulation rounds, dealer continuations, honba, riichi sticks,
ron/tsumo settlement, exhaustive draws, 30,000-point extension, and immediate
termination when any score falls below zero. The three AIs
minimize standard-hand shanten and normally remain closed for riichi; they only
open value-honor pon/kan, so they do not claim a no-yaku win. Scoring is delegated
to the existing scoring module.

Game mode enforces discard furiten, temporary furiten after passing ron, and
permanent-for-the-hand furiten after passing ron while in riichi. Furiten blocks
ron but not tsumo. Before each of your discards, all four players' rivers are
shown along with your current furiten status.

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

---

## Game Guide and Feature Reference (English)

### 1. Starting a game

Launch the playable desktop preview (no third-party packages required):

```bash
python desktop_ui.py
```

The setup screen selects East/South match length, language, Basic AI v1 or Advanced AI v1 opponents,
temperature, normal/hint mode, and an optional replay seed. Leave the seed blank to
generate a random seed; the actual value is shown in the game log and center panel
so the match can be replayed later. During play, click a
tile to discard and use the action panel for ron/tsumo, riichi, chi/pon/kan, passing,
and proceeding after settlement. The right-side log retains full scoring and hint
details. This first desktop version is a compatibility UI; a later phase can replace
the prompt bridge with a native event/action API and add packaged app launchers,
tile artwork, animation, sound, and save/resume.

Run complete desktop-input stability simulations without manually clicking:

```bash
python simulate_desktop_game.py --games 4 --profile advanced_v1 \
  --temperature 0.2 --assist hint --calls accept --json desktop_simulation.json
```

Run an interactive South match:

```bash
python main.py --mode game --language en --match-length south
```

Useful options:

- `--seed 2026`: fixes every shuffled wall for reproducible play.
- `--assist-mode normal`: shows the table without strategic recommendations.
- `--assist-mode hint`: enables shanten, discard, effective-tile, and tile-tracker hints.
- `--ai-levels basic_v1,advanced_v1,advanced_v1,basic_v1`: selects one versioned computer profile for each seat in `You,AI-1,AI-2,AI-3` order. In an interactive game, the first seat remains user-controlled. The old `simple/advanced` names remain compatible aliases.
- `--ai-temperature 0.2`: controls constrained advanced-AI style variation. `0` is fully deterministic; `0.2` is recommended; high values create more variety and variance.
- `--auto-game`: lets the computer control all four seats for testing or simulation.
- `--language en|zh|ja`: selects English, Chinese, or Japanese game UI.
- `--match-length east|south`: selects an East-only match or an East+South match.

The same settings can be stored in JSON:

```json
{
  "mode": "game",
  "language": "en",
  "game": {
    "seed": 2026,
    "match_length": "south",
    "assist_mode": "hint",
    "ai_levels": ["basic_v1", "advanced_v1", "advanced_v1", "basic_v1"],
    "ai_temperature": [0.0, 0.2, 0.2, 0.35]
  }
}
```

### 2. Match structure

- Every player starts with 25,000 points.
- An East match normally runs East 1–4; a South match normally runs East 1–South 4.
- A dealer win or dealer tenpai at an exhaustive draw causes a continuation and adds one honba.
- A non-dealer win, or a dealer-noten exhaustive draw, rotates the dealer.
- At the regulation final hand, a leader on 30,000 or more ends the match; otherwise play extends into South (East match) or West (South match), checking the threshold after every extension hand.
- Exactly zero points remains playable; a post-settlement negative score ends the match. Riichi requires at least 1,000 points.
- Final ranking is sorted by score. Remaining riichi sticks are awarded to the current first-place player.

### 3. Player turn display

Before every user-controlled discard, the game shows:

- your indexed hand and latest draw;
- live-wall count and all four scores;
- dealer, riichi, closed/open status, and open-meld count for every player;
- all four rivers;
- your melds and furiten reason, when applicable.

Discard by entering either the displayed index or tile token, such as `7` or `5p`. A legal closed tenpai discard also offers a riichi confirmation. After riichi, non-winning draws are automatically discarded because the hand is locked.

### 4. Calls and wins

- **Pon** and **kan** use a yes/no confirmation.
- **Chi** lists every legal sequence; enter its number or `0` to pass.
- A ron or tsumo opportunity shows the detected yaku and points before confirmation.
- Passing ron causes temporary furiten until the next draw. Passing after riichi causes furiten for the rest of that hand.
- Discard furiten blocks ron when any current winning tile appears in your own river. Furiten never blocks tsumo.

### 5. Hint mode and tile tracker

Hint mode uses the advanced heuristic AI to show:

- current standard-hand shanten;
- recommended discard and resulting shanten;
- number of effective tile types;
- remaining effective copies after visible-tile adjustment;
- estimated remaining count for every tile, grouped by suit and honors.

The tracker only uses information visible to the player: your hand, every river, public melds, and dora indicators. It does not reveal opponents' concealed tiles or the actual future wall.

### 6. Computer profiles

- **Basic AI v1 (`basic_v1`):** frozen baseline policy that minimizes standard-hand shanten, normally remains closed for riichi, and opens mainly for value honors.
- **Advanced AI v1 (`advanced_v1`):** frozen explainable policy that additionally evaluates effective-tile breadth/count, dora and value-honor retention, genbutsu, suji, walls, honor safety, current rank, folding, call value, kan risk, riichi quality, and constrained style temperature.

These computers are deterministic heuristic agents; they do not require reinforcement-learning training.

#### Advanced AI push/fold details

The advanced AI uses three defensive modes:

- `push`: preserve minimum shanten and maximize remaining effective tiles; danger is a secondary tie-breaker.
- `balanced`: preserve the best shanten, then prefer the safer discard before comparing effective tiles.
- `fold`: select safety first and may accept a worse shanten to avoid dealing in.

Mode selection considers current shanten, remaining effective tiles, current rank,
round progress, number of riichi opponents, and whether the dealer is threatening.
Individual tile danger starts from a neutral risk and is adjusted by genbutsu,
suji, walls, one-chance shapes, exhausted honors, dora/near-dora, dealer riichi,
multiple threats, and late-round pressure. Hint mode exposes these values so the
decision can be audited instead of behaving like a black box.

Riichi is decided separately from discard selection. The AI estimates legal waits,
visible remaining copies, rough ron value, wait quality, and whether the hand already
has a dama yaku. It is more willing to riichi a good mangan-class wait, but may stay
dama with a cheap bad wait, avoid a weak chase against a dealer, protect a sufficient
lead, or decline a nearly dead late-round riichi. In East 4 it compares the expected
gain with the score needed to improve rank, so a last-place player can push for a
realistic comeback while a leader accounts for the gap to second place and the
1,000-point riichi-stick risk.

Run a balanced AI benchmark (24 games for each of the three lineups, 72 total):

```bash
python benchmark_ai.py --games 24 --workers 4 --seed 800 \
  --json ai_benchmark.json
```

The benchmark rotates seats automatically and reports wins, ron, tsumo, deal-ins,
riichi, calls, average points, average rank, first-place rate, fourth-place rate,
runtime, and invalid point totals. Detailed per-game/per-player data is written to
the optional JSON file.

The quality block also records good/bad-wait riichi, post-riichi wins and deal-ins,
accepted-call shanten/ukeire gain, open-hand wins and value, push/balanced/fold
decisions under riichi pressure, threatened-hand outcomes, and average time spent in
discard, riichi, and call decisions. These fields are intended for fixed-seed
before/after diagnostics; use larger samples before treating score changes as a
strength conclusion.

Add `--temperature 0.2` to benchmark the guarded style randomizer. Temperature does
not change shanten priority, defense mode, riichi policy, or kan safety gates. It
only samples near-equivalent discards, and the JSON reports how often an alternative
was actually selected.

### 7. Settlement and statistics

After each hand, the game displays every score change and whether the dealer continues or rotates. Interactive play waits for confirmation before the next hand. At match end it reports final ranking plus hands, wins, ron, tsumo, deal-ins, riichi, chi, pon, and kan for every player.

### 8. Current rules scope

The simulator includes fixed walls after the initial shuffle, ron/tsumo settlement, honba, riichi sticks, dealer continuations, exhaustive-draw tenpai payments, furiten, public calls, replacement draws after open kan, additional kan dora, and multi-ron checks. Scoring reuses the project's existing supported-yaku engine. Some less common rules—such as chankan, active closed/added kan choices, ippatsu, rinshan yaku, haitei/houtei, and abortive draws—remain future extensions.

---

## 麻将对局指引与功能介绍（中文）

### 1. 开始游戏

启动可游玩的桌面预览版（不需要安装第三方 UI 包）：

```bash
python desktop_ui.py
```

设置页可以选择语言、Basic AI v1 或 Advanced AI v1 对手、温度、普通/提示模式、`小/中/大`字体和可选复现种子。种子留空时会自动生成随机值，并在中央牌桌和牌局记录中显示，之后可以手动输入该值复现对局。牌局中直接点击手牌弃牌：本巡摸牌会与原手牌分开并固定显示在最右侧，其他三家的暗手会按真实张数显示为空白牌背。中文界面只在显示层把内部牌名转换为东南西北白发中和万/筒/索，计算逻辑与复现种子不受影响。任何玩家立直时会显示红色事件横幅并持续用红色牌框标记；玩家副露时显示事件横幅，并持续用金色牌框标记。

闭手达到听牌时，所有能够立直的弃牌会显示“可立直”；点击其中一张后，右侧会出现立直的是/否确认。通过右侧操作区还可以选择荣和/自摸、吃碰杠、跳过和结算后继续。提示模式会在出牌时显示推荐牌、向听和押引模式，并在吃、碰、大明杠机会出现时显示高级电脑建议接受或跳过。当前杠提示均为使用对手弃牌的“大明杠”；主动暗杠与加杠尚未加入。右侧牌局记录会保留完整计分、候选比较和记牌器信息。当前桌面版属于第一阶段兼容 UI，后续可以把输入桥接替换成正式事件接口，并加入应用打包、牌面美术、动画、音效和存档继续功能。

无需手动点击即可运行完整桌面输入稳定性模拟：

```bash
python simulate_desktop_game.py --games 4 --profile advanced_v1 \
  --temperature 0.2 --assist hint --calls accept --json desktop_simulation.json
```

启动主视角南风战：

```bash
python main.py --mode game --language zh --match-length south
```

常用参数：

- `--seed 2026`：固定每一局洗好的牌山，方便复现相同对局。
- `--assist-mode normal`：普通模式，只显示牌桌信息。
- `--assist-mode hint`：提示模式，提供向听、推荐弃牌、有效牌和记牌器。
- `--ai-levels basic_v1,advanced_v1,advanced_v1,basic_v1`：按照“玩家、电脑1、电脑2、电脑3”的座位顺序设置版本化电脑。交互模式下第一个座位仍由玩家控制；旧名称 `simple/advanced` 仍可兼容使用。
- `--auto-game`：四个座位全部交给电脑，用于测试和批量模拟。
- `--language en|zh|ja`：选择英文、中文或日文牌局界面。
- `--match-length east|south`：选择东风战或包含东场、南场的南风战。
- `--ai-temperature 0.2`：设置高级电脑的受约束风格随机性。`0` 完全固定，推荐使用 `0.2`；更高数值会增加变化和结果方差。

也可以写入 JSON 配置：

```json
{
  "mode": "game",
  "language": "zh",
  "game": {
    "seed": 2026,
    "match_length": "south",
    "assist_mode": "hint",
    "ai_levels": ["basic_v1", "advanced_v1", "advanced_v1", "basic_v1"],
    "ai_temperature": [0.0, 0.2, 0.2, 0.35]
  }
}
```

### 2. 对局结构

- 四家初始点数均为25,000点。
- 东风战通常进行东一至东四；南风战通常进行东一至南四。
- 庄家和牌，或流局时庄家听牌，则连庄并增加一本场。
- 闲家和牌，或流局时庄家未听牌，则轮庄。
- 规定最后一局结算后，首位达到30,000点则结束；不足30,000点时，东风战南入、南风战西入，并在延长赛每个小局后重新判断。西四为延长赛安全上限。
- 玩家恰好0点时仍可继续，结算后低于0点才击飞并结束；立直需要至少1,000点，低于1,000点不能立直。
- 最终按点数排名；终局无人领取的立直棒交给当前第一名。

### 3. 玩家出牌界面

每次轮到主视角弃牌前，程序会显示：

- 带编号的手牌与本巡摸牌；
- 牌山剩余数量和四家点数；
- 每家的庄家、立直、门清/副露状态与副露数量；
- 四家的完整牌河；
- 自己的副露和振听原因。

弃牌时可以输入显示编号，也可以直接输入牌名，例如 `7` 或 `5p`。闭手弃牌后达到听牌时，程序会询问是否立直。立直后手牌锁定，未和牌的摸牌会自动摸切。

### 4. 吃、碰、杠与和牌

- **碰**和**杠**使用“是/否”确认。
- **吃**会列出所有合法组合，输入编号选择，输入 `0` 跳过。
- 可以荣和或自摸时，程序会先显示检测到的役种，但不会提前显示点数。确认和牌后才翻开立直玩家的里宝牌、重新计算最终点数并进入中央结算。
- 放弃一次可以荣和的牌会进入同巡振听，持续到自己的下一次摸牌。
- 立直后见逃会在本局剩余时间内保持振听。
- 当前所有和牌张中只要有一张出现在自己的牌河，就构成舍牌振听。振听只阻止荣和，不阻止自摸。

### 5. 提示模式与记牌器

提示模式使用高级电脑的启发式分析，显示：

- 当前标准手向听数；
- 推荐弃牌及弃牌后的向听数；
- 有效牌种类；
- 扣除可见牌后的剩余有效牌数量；
- 按万子、筒子、索子和字牌分组的每种牌推算剩余数量。

记牌器只使用玩家能够看到的信息：自己的手牌、四家牌河、公开副露和宝牌指示牌。它不会读取其他家的暗手牌，也不会泄露真实后续牌山。

### 6. 电脑版本

- **Basic AI v1（`basic_v1`）**：冻结保留的基础策略，主要选择最低标准手向听数的弃牌，通常保持门清立直，只对役牌进行较简单的副露。
- **Advanced AI v1（`advanced_v1`）**：冻结保留的可解释高级策略，进一步考虑有效进张、剩余牌数、宝牌与役牌保留、防守、顺位押引、副露、杠牌、立直质量和受约束温度。

两种电脑均为确定性的启发式程序，不需要进行大量强化学习训练。

#### 高级电脑押引机制

高级电脑现在使用三档防守模式：

- `进攻`：保持最低向听并优先最大化剩余有效牌，危险度只作为次要比较。
- `平衡押引`：保持最佳向听，但在同向听候选中先选择更安全的牌，再比较有效进张。
- `完全弃和`：安全度优先，必要时允许向听数变差以避免放铳。

模式选择会综合当前向听、剩余有效牌、当前顺位、巡目、立直人数以及庄家是否构成威胁。单张牌危险度会根据现物、筋、壁、一枚机会、接近打光的字牌、宝牌、宝牌周边、庄家立直、多家威胁和晚巡进行修正。提示模式会显示这些候选数据，使高级电脑的决定可以被检查，而不是黑箱选择。

高级电脑也会单独判断是否立直，而不是听牌后一律立直。判断会综合合法待牌、根据可见牌计算的剩余张数、好型或愚型、预估荣和打点、是否已有默听役、追立直对象是否为庄家、剩余牌山、当前顺位和点差。满贯级好型听牌会更积极；低打点愚型面对庄家立直、晚巡接近枯竭的待牌、或大幅领先时则可能默听。东四会比较“提升顺位所需点数”，末位会为可实现的逆转更积极进攻，第一名则会结合与第二名的点差及一千点立直棒风险决定是否保守。

运行公平轮换座位的电脑对照测试（每种阵容24场，共72场）：

```bash
python benchmark_ai.py --games 24 --workers 4 --seed 800 \
  --json ai_benchmark.json
```

脚本会自动测试“1高级3初级”“2高级2初级”“3高级1初级”，并轮换电脑所在座位。报告包含和牌、荣和、自摸、放铳、立直、副露、平均点数、平均顺位、一位率、四位率、耗时和异常点数总和；可选 JSON 文件会保存每场、每位玩家的详细数据。

质量统计还会记录：好型/愚型立直、立直后的和牌与放铳、立直和牌收入、副露带来的向听与有效进张变化、开手后的和牌与收入、面对立直威胁时的进攻/平衡/弃和次数及小局结果，以及弃牌、立直和副露决策耗时。这些数据适合使用相同种子做优化前后诊断；最终强度结论仍应使用更大样本。

基准测试可增加 `--temperature 0.2` 测试受约束随机性。温度不会跨越向听优先级，不会改变押引模式、立直政策或杠牌安全门槛，只会在进张、危险度和牌价值足够接近的弃牌之间抽样；JSON 会记录实际采用不同弃牌的次数。

### 7. 小局结算与最终统计

每个小局结束后会显示四家当前点数、本局点数变化，以及连庄或轮庄结果。交互模式会等待玩家确认后再进入下一局。整场结束后自动显示最终点数、排名，以及每家的小局数、和牌、荣和、自摸、放铳、立直、吃、碰、杠数据。

桌面版会把每小局结算显示为牌桌中央的大型结算卡，明确标注荣和、自摸或流局、赢家、放铳者、四家点数变化和连庄/轮庄。有人和牌时还会展示最终役种、表宝牌/赤宝牌/里宝牌、最终点数、里宝牌指示牌，以及四家的完整暗手与副露；荣和会明确写出“谁和了谁”，自摸会明确标注自摸者。点击“确认并进入下一局”后才会继续。对局结束后，中央终局卡会持续显示最终场次（包括南入/西入）、排名、点数、和牌、荣和、自摸、放铳和立直次数，直到玩家主动返回标题。每家状态框还会持续显示相对当前庄家的自风；轮庄后东南西北会自动更新。

### 8. 当前规则支持范围

目前模拟器支持：开局一次洗牌后固定牌山、荣和/自摸结算、本场、立直棒、连庄、流局听牌罚符、振听、公开吃碰杠、明杠岭上摸牌、杠宝牌和多家荣和检查。和牌役种与点数沿用项目现有计分模块。抢杠、主动暗杠/加杠、一发、岭上开花役、海底/河底、途中流局等较少见规则仍属于后续扩展范围。
