# Mahjong Card Reader (Riichi Mahjong)

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
- **`game`**: play a complete East-round simulation against three shanten-driven AIs.

## East-round simulation

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
    "ai_levels": ["simple", "advanced", "advanced", "simple"]
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
  --ai-levels advanced,simple,advanced,simple
```

Run the deterministic AI regression tests with:

```bash
python -m unittest test_game_ai.py
```

Use `--auto-game` for a hands-off smoke test. A wall is shuffled once at the start
of each hand and is deterministic thereafter; the same seed plus the same choices
replays the same walls. The match uses 25,000 starting points, East 1 through East
4, dealer continuations, honba, riichi sticks, ron/tsumo settlement, exhaustive
draws, and immediate termination when any score falls below zero. The three AIs
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

Run an interactive East-round match:

```bash
python main.py --mode game --language en
```

Useful options:

- `--seed 2026`: fixes every shuffled wall for reproducible play.
- `--assist-mode normal`: shows the table without strategic recommendations.
- `--assist-mode hint`: enables shanten, discard, effective-tile, and tile-tracker hints.
- `--ai-levels simple,advanced,advanced,simple`: selects one computer level for each seat in `You,AI-1,AI-2,AI-3` order. In an interactive game, the first seat remains user-controlled.
- `--auto-game`: lets the computer control all four seats for testing or simulation.
- `--language en|zh|ja`: selects English, Chinese, or Japanese game UI.

The same settings can be stored in JSON:

```json
{
  "mode": "game",
  "language": "en",
  "game": {
    "seed": 2026,
    "assist_mode": "hint",
    "ai_levels": ["simple", "advanced", "advanced", "simple"]
  }
}
```

### 2. Match structure

- Every player starts with 25,000 points.
- A match runs from East 1 through East 4.
- A dealer win or dealer tenpai at an exhaustive draw causes a continuation and adds one honba.
- A non-dealer win, or a dealer-noten exhaustive draw, rotates the dealer.
- The match ends after East 4 rotates or immediately when any player reaches zero or below.
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

### 6. Computer levels

- **Simple computer:** minimizes standard-hand shanten, normally remains closed for riichi, and opens mainly for value honors.
- **Advanced computer:** additionally evaluates effective-tile breadth/count, dora and value-honor retention, genbutsu, suji, walls, honor safety, current rank, folding, call value, and kan risk.

These computers are deterministic heuristic agents; they do not require reinforcement-learning training.

Run a balanced AI benchmark (24 games for each of the three lineups, 72 total):

```bash
python benchmark_ai.py --games 24 --workers 4 --seed 800 \
  --json ai_benchmark.json
```

The benchmark rotates seats automatically and reports wins, ron, tsumo, deal-ins,
riichi, calls, average points, average rank, first-place rate, fourth-place rate,
runtime, and invalid point totals. Detailed per-game/per-player data is written to
the optional JSON file.

### 7. Settlement and statistics

After each hand, the game displays every score change and whether the dealer continues or rotates. Interactive play waits for confirmation before the next hand. At match end it reports final ranking plus hands, wins, ron, tsumo, deal-ins, riichi, chi, pon, and kan for every player.

### 8. Current rules scope

The simulator includes fixed walls after the initial shuffle, ron/tsumo settlement, honba, riichi sticks, dealer continuations, exhaustive-draw tenpai payments, furiten, public calls, replacement draws after open kan, additional kan dora, and multi-ron checks. Scoring reuses the project's existing supported-yaku engine. Some less common rules—such as chankan, active closed/added kan choices, ippatsu, rinshan yaku, haitei/houtei, and abortive draws—remain future extensions.

---

## 麻将对局指引与功能介绍（中文）

### 1. 开始游戏

启动主视角东风战：

```bash
python main.py --mode game --language zh
```

常用参数：

- `--seed 2026`：固定每一局洗好的牌山，方便复现相同对局。
- `--assist-mode normal`：普通模式，只显示牌桌信息。
- `--assist-mode hint`：提示模式，提供向听、推荐弃牌、有效牌和记牌器。
- `--ai-levels simple,advanced,advanced,simple`：按照“玩家、电脑1、电脑2、电脑3”的座位顺序设置电脑等级。交互模式下第一个座位仍由玩家控制。
- `--auto-game`：四个座位全部交给电脑，用于测试和批量模拟。
- `--language en|zh|ja`：选择英文、中文或日文牌局界面。

也可以写入 JSON 配置：

```json
{
  "mode": "game",
  "language": "zh",
  "game": {
    "seed": 2026,
    "assist_mode": "hint",
    "ai_levels": ["simple", "advanced", "advanced", "simple"]
  }
}
```

### 2. 对局结构

- 四家初始点数均为25,000点。
- 东风战从东一局进行至东四局。
- 庄家和牌，或流局时庄家听牌，则连庄并增加一本场。
- 闲家和牌，或流局时庄家未听牌，则轮庄。
- 东四局轮庄后结束；任何玩家点数降至0点或以下时立即提前结束。
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
- 可以荣和或自摸时，程序会先显示检测到的役种与点数，再询问是否和牌。
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

### 6. 电脑等级

- **简单电脑**：主要选择最低标准手向听数的弃牌，通常保持门清立直，只对役牌进行较简单的副露。
- **高级电脑**：进一步考虑有效进张、剩余牌数、宝牌与役牌保留、现物、筋、壁、字牌安全度、当前排名、弃和判断、副露收益和杠牌风险。

两种电脑均为确定性的启发式程序，不需要进行大量强化学习训练。

运行公平轮换座位的电脑对照测试（每种阵容24场，共72场）：

```bash
python benchmark_ai.py --games 24 --workers 4 --seed 800 \
  --json ai_benchmark.json
```

脚本会自动测试“1高级3初级”“2高级2初级”“3高级1初级”，并轮换电脑所在座位。报告包含和牌、荣和、自摸、放铳、立直、副露、平均点数、平均顺位、一位率、四位率、耗时和异常点数总和；可选 JSON 文件会保存每场、每位玩家的详细数据。

### 7. 小局结算与最终统计

每个小局结束后会显示四家当前点数、本局点数变化，以及连庄或轮庄结果。交互模式会等待玩家确认后再进入下一局。整场结束后自动显示最终点数、排名，以及每家的小局数、和牌、荣和、自摸、放铳、立直、吃、碰、杠数据。

### 8. 当前规则支持范围

目前模拟器支持：开局一次洗牌后固定牌山、荣和/自摸结算、本场、立直棒、连庄、流局听牌罚符、振听、公开吃碰杠、明杠岭上摸牌、杠宝牌和多家荣和检查。和牌役种与点数沿用项目现有计分模块。抢杠、主动暗杠/加杠、一发、岭上开花役、海底/河底、途中流局等较少见规则仍属于后续扩展范围。
