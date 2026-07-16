from __future__ import annotations

import random
import re
from dataclasses import dataclass, field

from remaining import RemainingTileCounter
from scoring import ScoreBreakdown, score_points_from_config
from shanten import shanten_standard, shanten_standard_draw_state
from tiles import index_to_tile, tile_to_index, tiles_to_counts


WINDS = ("E", "S", "W", "N")


def tile_sort_key(tile: str) -> tuple[int, int]:
    i = tile_to_index(tile)
    return (i, 0)


def dora_from_indicator(tile: str) -> str:
    i = tile_to_index(tile)
    if i < 27:
        return index_to_tile((i // 9) * 9 + (i % 9 + 1) % 9)
    if i < 31:
        return index_to_tile(27 + (i - 27 + 1) % 4)
    return index_to_tile(31 + (i - 31 + 1) % 3)


@dataclass
class MeldState:
    kind: str
    tiles: list[str]
    open: bool = True


@dataclass
class PlayerStats:
    hands: int = 0
    wins: int = 0
    ron: int = 0
    tsumo: int = 0
    deal_in: int = 0
    riichi: int = 0
    chi: int = 0
    pon: int = 0
    kan: int = 0


@dataclass
class PlayerState:
    name: str
    ai_level: str = "simple"
    points: int = 25_000
    hand: list[str] = field(default_factory=list)
    melds: list[MeldState] = field(default_factory=list)
    river: list[str] = field(default_factory=list)
    riichi: bool = False
    temporary_furiten: bool = False
    riichi_furiten: bool = False
    stats: PlayerStats = field(default_factory=PlayerStats)

    def sort(self) -> None:
        self.hand.sort(key=tile_sort_key)

    @property
    def is_closed(self) -> bool:
        return not any(m.open for m in self.melds)


class MahjongGame:
    """Small, deterministic-after-deal East-round simulator.

    The wall (including the dead wall) is shuffled exactly once per hand. All later
    draws are simple pops, so replaying a seed and the same decisions gives the same
    hand.
    """

    def __init__(
        self,
        *,
        seed: int | None = None,
        interactive: bool = True,
        ai_levels: list[str] | None = None,
        assist_mode: str | None = None,
        language: str = "en",
    ) -> None:
        self.rng = random.Random(seed)
        self.seed = seed
        self.interactive = interactive
        language = language.strip().lower()
        language = {
            "chinese": "zh", "中文": "zh", "english": "en", "英文": "en",
            "japanese": "ja", "日本語": "ja", "日语": "ja",
        }.get(language, language)
        if language not in {"en", "zh", "ja"}:
            raise ValueError("language must be en, zh, or ja.")
        self.language = language
        if assist_mode not in {None, "normal", "hint"}:
            raise ValueError("assist_mode must be normal or hint.")
        self.assist_mode = assist_mode
        levels = ai_levels or ["simple"] * 4
        if len(levels) != 4 or any(level not in {"simple", "advanced"} for level in levels):
            raise ValueError("ai_levels must contain four values: simple or advanced.")
        self.players = [
            PlayerState(name, ai_level=level)
            for name, level in zip(("You", "AI-1", "AI-2", "AI-3"), levels)
        ]
        self.dealer = 0
        self.round_hand = 0
        self.honba = 0
        self.riichi_sticks = 0
        self.wall: list[str] = []
        self.dead_wall: list[str] = []
        self.dora_indicators: list[str] = []
        self._call_win_dealer_continues: bool | None = None

    def _t(self, en: str, zh: str, ja: str | None = None) -> str:
        if self.language == "en":
            return en
        if self.language == "zh":
            return zh
        if ja is not None:
            return ja
        return self._ja_from_zh(zh)

    @staticmethod
    def _ja_from_zh(text: str) -> str:
        """Translate the compact game UI strings while preserving tiles/numbers."""
        exact = {
            "\n最终排名": "\n最終順位", "\n最终统计": "\n最終統計",
            "  玩家    小局 和牌 荣和 自摸 放铳 立直 吃 碰 杠":
                "  プレイヤー 局数 和了 ロン ツモ 放銃 リーチ チー ポン カン",
            "选择游戏模式：": "ゲームモードを選択してください：",
            "  1. 普通模式": "  1. 通常モード",
            "  2. 提示模式（向听、推荐弃牌、记牌器）": "  2. ヒントモード（シャンテン数・推奨打牌・牌カウンター）",
            "请输入 1 或 2。": "1 または 2 を入力してください。",
            "按回车进入下一局……": "Enterキーで次局へ進みます……",
            "流局。庄家听牌时连庄。": "流局。親がテンパイなら連荘です。",
            "\n本局结算": "\n局の精算", "玩家状态：": "プレイヤー状態：",
            "牌河：": "河：", "提示：": "ヒント：",
            "  记牌器（从你的视角推算剩余）：": "  牌カウンター（自分視点の推定残り枚数）：",
            "请输入是或否。": "はい、またはいいえを入力してください。",
            "选择无效。": "無効な選択です。", "  0. 跳过": "  0. パス",
            "该牌不在你的手牌中。": "その牌は手牌にありません。",
            "（空）": "（なし）",
        }
        if text in exact:
            return exact[text]
        patterns = (
            (r"^(.+)宣布立直。$", r"\1がリーチを宣言しました。"),
            (r"^(.+)对 (.+) 宣布吃。$", r"\1が \2 をチーしました。"),
            (r"^(.+)对 (.+) 宣布碰。$", r"\1が \2 をポンしました。"),
            (r"^(.+)对 (.+) 宣布杠。$", r"\1が \2 をカンしました。"),
            (r"^(.+)打出了 (.+)。$", r"\1の打牌：\2。"),
            (r"^(.+)荣和：(.+)，放铳者为(.+)。$", r"\1のロン：\2、放銃者は\3。"),
            (r"^(.+)自摸：(.+)。$", r"\1のツモ：\2。"),
            (r"^听牌罚符：(.+)合计获得3000点。$", r"ノーテン罰符：\1が合計3000点を受け取ります。"),
            (r"^未领取的立直棒（(.+)根）归当前第一名(.+)。$", r"未供託のリーチ棒（\1本）は現在1位の\2が受け取ります。"),
            (r"^你打出了 (.+)。$", r"あなたの打牌：\1。"),
            (r"^可以吃 (.+)：$", r"\1 をチーできます："),
            (r"^是否杠 (.+)？$", r"\1 をカンしますか？"),
            (r"^是否碰 (.+)？$", r"\1 をポンしますか？"),
            (r"^是否荣和 (.+)（(.+)）？$", r"\1 でロンしますか（\2）？"),
            (r"^是否自摸 (.+)（(.+)）？$", r"\1 でツモ和了しますか（\2）？"),
            (r"^(.+)进行岭上摸牌；当前宝牌为 (.+)。$", r"\1が嶺上牌をツモしました。現在のドラは \2 です。"),
        )
        for pattern, replacement in patterns:
            if re.match(pattern, text):
                return re.sub(pattern, replacement, text)
        replacements = (
            ("最终", "最終"), ("统计", "統計"), ("小局", "局数"),
            ("和牌", "和了"), ("荣和", "ロン"), ("自摸", "ツモ"),
            ("放铳", "放銃"), ("立直", "リーチ"), ("副露", "副露"),
            ("庄家", "親"), ("门清", "門前"), ("点数", "点数"),
            ("你的手牌", "あなたの手牌"), ("摸牌", "ツモ牌"),
            ("牌山剩余", "山の残り"), ("事件", "イベント"),
            ("当前向听数", "現在のシャンテン数"), ("推荐弃牌", "推奨打牌"),
            ("弃牌后", "打牌後"), ("向听", "シャンテン"),
            ("种有效牌", "種の有効牌"), ("按可见牌修正后共", "見えている牌を反映して合計"),
            ("张", "枚"), ("结果", "結果"), ("连庄", "連荘"), ("轮庄", "親流れ"),
            ("听牌罚符", "ノーテン罰符"), ("合计获得", "が合計"),
            ("可以吃", "チーできます"), ("请选择吃法", "チーの形を選択してください"),
            ("请输入要打出的牌或编号", "捨てる牌または番号を入力してください"),
            ("是否杠", "カンしますか"), ("是否碰", "ポンしますか"),
            ("是否荣和", "ロンしますか"), ("是否自摸", "ツモ和了しますか"),
            ("是否", ""), ("宣布", "を宣言しました"), ("打出了", "の打牌："),
            ("进行了", "をしました："), ("对 ", ""),
            ("进行岭上摸牌", "嶺上牌をツモしました"), ("当前宝牌为", "現在のドラは"),
            ("振听", "フリテン"), ("舍牌", "捨て牌"), ("同巡", "同巡"),
            ("立直见逃", "リーチ後見逃し"), ("你处于", "現在"),
            ("无法", "できません"), ("本局结束前将保持", "この局が終わるまで継続します："),
            ("你放弃了", "見逃したため"), ("进入", "になりました："),
            ("持续到下次摸牌", "次の自摸まで継続します"),
            ("本局", "この局"), ("精算", "精算"), ("宝牌", "ドラ"),
            ("玩家", "プレイヤー"), ("电脑", "CPU"), ("简单", "初級"), ("高级", "上級"),
            ("万子", "萬子"), ("筒子", "筒子"), ("索子", "索子"), ("字牌", "字牌"),
            ("是", "はい"), ("否", "いいえ"), ("默认", "既定値："),
            ("点", "点"), ("。", "。"), ("：", "："), ("（", "（"), ("）", "）"),
            ("，", "、"),
        )
        out = text
        for old, new in replacements:
            out = out.replace(old, new)
        return out

    def _name(self, player: PlayerState) -> str:
        if self.language == "en":
            return player.name
        if self.language == "zh":
            return {"You": "玩家", "AI-1": "电脑1", "AI-2": "电脑2", "AI-3": "电脑3"}[player.name]
        return {"You": "あなた", "AI-1": "CPU1", "AI-2": "CPU2", "AI-3": "CPU3"}[player.name]

    def _meld_name(self, kind: str) -> str:
        if self.language == "en":
            return kind
        if self.language == "zh":
            return {"chi": "吃", "pon": "碰", "kan": "杠"}.get(kind, kind)
        return {"chi": "チー", "pon": "ポン", "kan": "カン"}.get(kind, kind)

    def play(self) -> None:
        if self.interactive and self.assist_mode is None:
            self.assist_mode = self._choose_assist_mode()
        elif self.assist_mode is None:
            self.assist_mode = "normal"
        levels = ", ".join(
            f"{self._name(p)}=" + (
                (("高级" if p.ai_level == "advanced" else "简单") if self.language == "zh" else
                 ("上級" if p.ai_level == "advanced" else "初級") if self.language == "ja" else p.ai_level)
            )
            for p in self.players
        )
        if self.language == "zh":
            mode = "提示" if self.assist_mode == "hint" else "普通"
            print(f"东风战开始（种子={self.seed!r}；模式={mode}；{levels}）。")
        elif self.language == "ja":
            mode = "ヒント" if self.assist_mode == "hint" else "通常"
            print(f"東風戦開始（シード={self.seed!r}；モード={mode}；{levels}）。")
        else:
            print(f"East-round game started (seed={self.seed!r}; mode={self.assist_mode}; {levels}).")
        while self.round_hand < 4 and all(p.points > 0 for p in self.players):
            dealer_continues = self._play_hand()
            if dealer_continues:
                self.honba += 1
            else:
                self.dealer = (self.dealer + 1) % 4
                self.round_hand += 1
                self.honba = 0
        # If the match ends with unclaimed riichi sticks, award them to the current
        # first-place player so the final player scores still total 100,000.
        if self.riichi_sticks:
            leader = max(range(4), key=lambda i: (self.players[i].points, -i))
            self.players[leader].points += self.riichi_sticks * 1000
            print(self._t(
                f"Unclaimed riichi sticks ({self.riichi_sticks}) go to {self._name(self.players[leader])}.",
                f"未领取的立直棒（{self.riichi_sticks}根）归当前第一名{self._name(self.players[leader])}。",
            ))
            self.riichi_sticks = 0
        print(self._t("\nFinal ranking", "\n最终排名"))
        ranked = sorted(enumerate(self.players), key=lambda x: (-x[1].points, x[0]))
        for rank, (_, p) in enumerate(ranked, 1):
            print(f"  {rank}. {self._name(p)}: {p.points}")
        print(self._t("\nFinal statistics", "\n最终统计"))
        print(self._t(
            "  Player  Hands Wins Ron Tsumo Deal-in Riichi Chi Pon Kan",
            "  玩家    小局 和牌 荣和 自摸 放铳 立直 吃 碰 杠",
        ))
        for p in self.players:
            s = p.stats
            print(
                f"  {self._name(p):<7} {s.hands:>5} {s.wins:>4} {s.ron:>3} {s.tsumo:>5} "
                f"{s.deal_in:>7} {s.riichi:>6} {s.chi:>3} {s.pon:>3} {s.kan:>3}"
            )

    def _choose_assist_mode(self) -> str:
        print(self._t("Select play mode:", "选择游戏模式："))
        print(self._t("  1. Normal", "  1. 普通模式"))
        print(self._t("  2. Hint (shanten, recommended discard, tile tracker)", "  2. 提示模式（向听、推荐弃牌、记牌器）"))
        while True:
            answer = input(self._t("Mode [1/2]: ", "请选择模式 [1/2]：")).strip().lower()
            if answer in {"1", "normal", "普通"}:
                return "normal"
            if answer in {"2", "hint", "提示"}:
                return "hint"
            print(self._t("Please enter 1 or 2.", "请输入 1 或 2。"))

    def _new_wall(self) -> None:
        tiles = [index_to_tile(i) for i in range(34) for _ in range(4)]
        self.rng.shuffle(tiles)
        self.dead_wall = tiles[-14:]
        self.wall = tiles[:-14]
        self.dora_indicators = [self.dead_wall[4]]

    def _play_hand(self) -> bool:
        before = [p.points for p in self.players]
        for p in self.players:
            p.stats.hands += 1
        dealer_continues = self._play_hand_core()
        self._show_hand_settlement(before, dealer_continues)
        match_ends = any(p.points <= 0 for p in self.players) or (
            self.round_hand == 3 and not dealer_continues
        )
        if self.interactive and not match_ends:
            input(self._t("Press Enter to continue to the next hand...", "按回车进入下一局……"))
        return dealer_continues

    def _play_hand_core(self) -> bool:
        self._new_wall()
        self._call_win_dealer_continues = None
        for p in self.players:
            p.hand.clear(); p.melds.clear(); p.river.clear(); p.riichi = False
            p.temporary_furiten = False; p.riichi_furiten = False
        for _ in range(13):
            for offset in range(4):
                self.players[(self.dealer + offset) % 4].hand.append(self.wall.pop(0))
        for p in self.players:
            p.sort()
        if self.language == "zh":
            print(f"\n东{self.round_hand + 1}局，庄家={self._name(self.players[self.dealer])}，本场={self.honba}")
            print(f"宝牌：{' '.join(dora_from_indicator(x) for x in self.dora_indicators)}")
        elif self.language == "ja":
            print(f"\n東{self.round_hand + 1}局、親={self._name(self.players[self.dealer])}、本場={self.honba}")
            print(f"ドラ：{' '.join(dora_from_indicator(x) for x in self.dora_indicators)}")
        else:
            print(f"\nEast {self.round_hand + 1}, dealer={self._name(self.players[self.dealer])}, honba={self.honba}")
            print(f"Dora: {' '.join(dora_from_indicator(x) for x in self.dora_indicators)}")

        turn = self.dealer
        while self.wall:
            p = self.players[turn]
            # Same-turn furiten ends on this player's next normal draw. A missed
            # ron after riichi is stored separately and lasts for the whole hand.
            p.temporary_furiten = False
            draw = self.wall.pop(0)
            p.hand.append(draw); p.sort()
            score = self._try_score(turn, draw, "tsumo")
            if score and (turn != 0 or self._yes_no(self._t(
                f"Tsumo {draw} for {self._score_label(score)}?",
                f"是否自摸 {draw}（{self._score_label(score)}）？",
            ), True)):
                self._settle_tsumo(turn, score)
                return turn == self.dealer
            if turn == 0 and self.interactive:
                self._show_state(draw)
            # After riichi the hand is locked: if the draw is not a winning tile,
            # the drawn tile must be discarded unchanged.
            discard = draw if p.riichi else self._choose_discard(turn)
            p.hand.remove(discard); p.river.append(discard)
            if turn == 0 and self.interactive:
                print(self._t(f"You discarded {discard}.", f"你打出了 {discard}。"))

            ron_result = self._resolve_ron(turn, discard)
            if ron_result is not None:
                return ron_result

            caller = self._offer_calls(turn, discard)
            if self._call_win_dealer_continues is not None:
                return self._call_win_dealer_continues
            if caller is not None:
                turn = caller
            else:
                turn = (turn + 1) % 4

        print(self._t("Exhaustive draw. Dealer continues only if tenpai.", "流局。庄家听牌时连庄。"))
        tenpai = [i for i, player in enumerate(self.players) if self._standard_shanten(player) == 0]
        noten = [i for i in range(4) if i not in tenpai]
        if tenpai and noten:
            gain = 3000 // len(tenpai)
            loss = 3000 // len(noten)
            for i in tenpai:
                self.players[i].points += gain
            for i in noten:
                self.players[i].points -= loss
            names = "、".join(self._name(self.players[i]) for i in tenpai)
            print(self._t(
                "Tenpai payment: " + ", ".join(self._name(self.players[i]) for i in tenpai) + " receive 3000 total.",
                f"听牌罚符：{names}合计获得3000点。",
            ))
        dealer_tenpai = self.dealer in tenpai
        return dealer_tenpai

    def _show_hand_settlement(self, before: list[int], dealer_continues: bool) -> None:
        print(self._t("\nHand settlement", "\n本局结算"))
        for i, p in enumerate(self.players):
            delta = p.points - before[i]
            print(f"  {self._name(p):<5}: {p.points:>6} ({delta:+d})")
        result = self._t(
            "dealer continues" if dealer_continues else "dealer rotates",
            "连庄" if dealer_continues else "轮庄",
        )
        print(self._t(f"  Result: {result}", f"  结果：{result}"))

    def _full_for_analysis(self, p: PlayerState, extra: str | None = None) -> list[str]:
        result = p.hand.copy()
        if extra:
            result.append(extra)
        for meld in p.melds:
            result.extend(meld.tiles[:3])
        return result

    def _standard_shanten(self, p: PlayerState, extra: str | None = None) -> int:
        return shanten_standard(tiles_to_counts(self._full_for_analysis(p, extra)))

    def _score_args(self, seat: int, win_tile: str, win_type: str) -> dict[str, object]:
        p = self.players[seat]
        concealed = p.hand.copy()
        # Ron tile is not in hand; a tsumo tile already is and must be removed once.
        if win_type == "tsumo":
            concealed.remove(win_tile)
        open_melds = [m for m in p.melds if m.open and m.kind != "kan"] + [
            m for m in p.melds if m.open and m.kind == "kan"
        ]
        closed_kans = [m for m in p.melds if not m.open and m.kind == "kan"]
        ordered = concealed.copy()
        for m in open_melds:
            ordered.extend(m.tiles)
        dora = " ".join(dora_from_indicator(x) for x in self.dora_indicators)
        return dict(
            hand_text=" ".join(ordered), win_tile_text=win_tile, win_type=win_type,
            is_dealer=seat == self.dealer, dora_text=dora,
            seat_wind=WINDS[(seat - self.dealer) % 4], round_wind="E",
            riichi=p.riichi, furo_sets=len(open_melds),
            kan_sets=sum(m.kind == "kan" for m in open_melds),
            ankan_tiles=[m.tiles[0] for m in closed_kans],
            kan_tiles=[m.tiles[0] for m in open_melds if m.kind == "kan"],
        )

    def _try_score(self, seat: int, tile: str, win_type: str) -> ScoreBreakdown | None:
        try:
            return score_points_from_config(**self._score_args(seat, tile, win_type))
        except (ValueError, IndexError):
            return None

    def _ron_waits(self, seat: int) -> set[str]:
        """Return the tiles this player can legally ron on, ignoring furiten."""
        p = self.players[seat]
        visible = tiles_to_counts(self._full_for_analysis(p))
        waits: set[str] = set()
        for i in range(34):
            if visible[i] >= 4:
                continue
            tile = index_to_tile(i)
            if self._try_score(seat, tile, "ron") is not None:
                waits.add(tile)
        return waits

    def _resolve_ron(self, discarder: int, discard: str) -> bool | None:
        """Resolve every legal ron on a discard; return dealer continuation if won."""
        winners: list[tuple[int, ScoreBreakdown]] = []
        for other in range(4):
            if other == discarder:
                continue
            score = self._try_score(other, discard, "ron")
            if not score:
                continue
            if self._is_furiten(other):
                if other == 0:
                        print(self._t(
                            f"Ron on {discard} is unavailable: you are furiten.",
                            f"无法荣和 {discard}：你处于振听状态。",
                        ))
                continue
            accepted = other != 0 or self._yes_no(
                self._t(
                    f"Ron on {discard} for {self._score_label(score)}?",
                    f"是否荣和 {discard}（{self._score_label(score)}）？",
                ), True
            )
            if accepted:
                winners.append((other, score))
            else:
                missed = self.players[other]
                if missed.riichi:
                    missed.riichi_furiten = True
                    print(self._t(
                        "You passed ron after riichi: furiten lasts until this hand ends.",
                        "你在立直后见逃，本局结束前将保持振听。",
                    ))
                else:
                    missed.temporary_furiten = True
                    print(self._t(
                        "You passed ron: temporary furiten lasts until your next draw.",
                        "你放弃了荣和，进入同巡振听，持续到下次摸牌。",
                    ))
        if not winners:
            return None
        self._settle_ron(discarder, winners)
        return any(winner == self.dealer for winner, _ in winners)

    def _discard_furiten(self, seat: int) -> bool:
        p = self.players[seat]
        waits = self._ron_waits(seat)
        return bool(waits.intersection(p.river))

    def _is_furiten(self, seat: int) -> bool:
        p = self.players[seat]
        return p.temporary_furiten or p.riichi_furiten or self._discard_furiten(seat)

    def _choose_discard(self, seat: int) -> str:
        p = self.players[seat]
        if seat == 0 and self.interactive:
            while True:
                raw = input(self._t("Discard tile (or index): ", "请输入要打出的牌或编号：")).strip()
                if raw.isdigit() and 1 <= int(raw) <= len(p.hand):
                    discard = p.hand[int(raw) - 1]
                    break
                if raw in p.hand:
                    discard = raw
                    break
                print(self._t("That tile is not in your hand.", "该牌不在你的手牌中。"))
            best_shanten = self._shanten_after_discard(p, discard)
        elif p.ai_level == "advanced":
            discard = self._choose_advanced_discard(seat)
            best_shanten = self._shanten_after_discard(p, discard)
        else:
            discard, best_shanten = self._choose_simple_discard(p)

        # Closed AI declares riichi at tenpai. This both supplies a yaku and makes
        # its later discard behaviour deterministic.
        p.hand.remove(discard)
        can_riichi = best_shanten == 0 and p.is_closed and not p.riichi and p.points >= 1000
        declare = can_riichi and (
            seat != 0 or not self.interactive or self._yes_no("Declare riichi?", False)
        )
        if declare:
            p.riichi = True; p.points -= 1000; self.riichi_sticks += 1
            p.stats.riichi += 1
            print(self._t(f"{self._name(p)} declares riichi.", f"{self._name(p)}宣布立直。"))
        p.hand.append(discard); p.sort()
        return discard

    def _choose_simple_discard(self, p: PlayerState) -> tuple[str, int]:
        best: list[str] = []
        best_shanten = 99
        for tile in sorted(set(p.hand), key=tile_sort_key):
            p.hand.remove(tile)
            sh = self._standard_shanten(p)
            p.hand.append(tile); p.sort()
            if sh < best_shanten:
                best_shanten, best = sh, [tile]
            elif sh == best_shanten:
                best.append(tile)
        return best[0], best_shanten

    def _shanten_after_discard(self, p: PlayerState, tile: str) -> int:
        p.hand.remove(tile)
        sh = self._standard_shanten(p)
        p.hand.append(tile); p.sort()
        return sh

    def _visible_counts(self, seat: int) -> list[int]:
        visible = self.players[seat].hand.copy() + self.dora_indicators.copy()
        for player in self.players:
            visible.extend(player.river)
            for meld in player.melds:
                visible.extend(meld.tiles)
        return tiles_to_counts(visible)

    def _ukeire(self, p: PlayerState, visible: list[int]) -> tuple[int, int]:
        current = self._standard_shanten(p)
        base_counts = tiles_to_counts(self._full_for_analysis(p))
        kinds = total = 0
        for i in range(34):
            left = max(0, 4 - visible[i])
            if not left:
                continue
            drawn = base_counts.copy(); drawn[i] += 1
            improves = shanten_standard_draw_state(drawn) < current
            if improves:
                kinds += 1; total += left
        return kinds, total

    def _tile_value(self, seat: int, tile: str) -> float:
        p = self.players[seat]
        value = 0.0
        if tile in {dora_from_indicator(x) for x in self.dora_indicators}:
            value += 6.0
        seat_wind = WINDS[(seat - self.dealer) % 4]
        if tile in {"P", "F", "C", "E", seat_wind}:
            value += 2.0 + min(2, p.hand.count(tile))
        i = tile_to_index(tile)
        if i < 27:
            pos = i % 9
            counts = tiles_to_counts(p.hand)
            for delta in (-2, -1, 1, 2):
                j = i + delta
                if 0 <= j < 27 and j // 9 == i // 9 and counts[j]:
                    value += 0.5 if abs(delta) == 2 else 1.0
            if pos in {0, 8}:
                value -= 0.3
        return value

    def _defense_risk_breakdown(
        self, seat: int, tile: str, threats: list[int], visible: list[int]
    ) -> dict[str, object]:
        if not threats:
            return {"total": 0.0, "tags": ["no-threat"]}
        i = tile_to_index(tile)
        risk = 0.0
        tags: set[str] = set()
        dora_indices = {tile_to_index(dora_from_indicator(x)) for x in self.dora_indicators}
        late_round = max((len(player.river) for player in self.players), default=0) >= 12
        for opponent in threats:
            river = self.players[opponent].river
            if tile in river:  # genbutsu
                tags.add("genbutsu")
                continue
            one = 5.0
            if i >= 27:
                one = max(0.3, 3.2 - visible[i])  # exhausted honors become safer
                tags.add("honor")
                if visible[i] >= 3:
                    tags.add("exhausted-honor")
            else:
                pos = i % 9
                river_pos = {tile_to_index(x) % 9 for x in river if tile_to_index(x) // 9 == i // 9}
                # Basic suji: 1/4/7, 2/5/8, 3/6/9 relationships.
                if any(abs(pos - r) == 3 for r in river_pos):
                    one -= 2.0
                    tags.add("suji")
                # A complete wall or one-chance adjacent tile reduces sequence danger.
                neighbors = [j for j in (i - 1, i + 1) if 0 <= j < 27 and j // 9 == i // 9]
                if any(visible[j] >= 4 for j in neighbors):
                    one -= 1.2
                    tags.add("wall")
                elif any(visible[j] == 3 for j in neighbors):
                    one -= 0.5
                    tags.add("one-chance")
            if i in dora_indices:
                one += 2.5
                tags.add("dora")
            elif i < 27 and any(
                d < 27 and d // 9 == i // 9 and abs(d - i) == 1 for d in dora_indices
            ):
                one += 0.8
                tags.add("near-dora")
            if opponent == self.dealer:
                one *= 1.2
                tags.add("dealer-threat")
            if late_round:
                one *= 1.1
                tags.add("late-round")
            risk += max(0.1, one)
        return {"total": risk, "tags": sorted(tags)}

    def _defense_risk(self, seat: int, tile: str, threats: list[int], visible: list[int]) -> float:
        return float(self._defense_risk_breakdown(seat, tile, threats, visible)["total"])

    def _defense_mode(
        self, seat: int, shanten: int, threats: list[int], ukeire_total: int = 0
    ) -> str:
        """Return push, balanced, or fold for the current threat/hand context."""
        if not threats:
            return "push"
        rank = self._current_rank(seat)
        late_round = max((len(other.river) for other in self.players), default=0) >= 12
        multiple = len(threats) >= 2
        dealer_threat = self.dealer in threats
        if shanten >= 3:
            return "fold"
        if shanten == 2:
            if rank == 4 and not late_round and not multiple and ukeire_total >= 20:
                return "balanced"
            return "fold"
        if shanten == 1:
            if rank == 1 or (multiple and rank != 4):
                return "fold"
            if late_round and ukeire_total < 12:
                return "fold"
            if dealer_threat or multiple or ukeire_total < 16:
                return "balanced"
            return "push"
        if multiple and (rank == 1 or late_round):
            return "balanced"
        return "push"

    def _current_rank(self, seat: int) -> int:
        order = sorted(range(4), key=lambda i: (-self.players[i].points, i))
        return order.index(seat) + 1

    def _should_fold(self, seat: int, shanten: int, threats: list[int]) -> bool:
        """Decide whether rank and distance justify switching to defense."""
        return self._defense_mode(seat, shanten, threats) == "fold"

    def advanced_discard_report(self, seat: int) -> dict[str, object]:
        """Return an explainable advanced-AI discard decision."""
        player = self.players[seat]
        visible = self._visible_counts(seat)
        threats = [i for i, other in enumerate(self.players) if i != seat and other.riichi]
        shanten_by_tile = {
            tile: self._shanten_after_discard(player, tile)
            for tile in sorted(set(player.hand), key=tile_sort_key)
        }
        best_shanten = min(shanten_by_tile.values())
        candidates: list[dict[str, object]] = []
        for tile, shanten in shanten_by_tile.items():
            kinds = total = 0
            if shanten == best_shanten:
                player.hand.remove(tile)
                kinds, total = self._ukeire(player, visible)
                player.hand.append(tile); player.sort()
            defense = self._defense_risk_breakdown(seat, tile, threats, visible)
            candidates.append({
                "tile": tile, "shanten": shanten, "ukeire_kinds": kinds,
                "ukeire_total": total, "risk": defense["total"],
                "risk_tags": defense["tags"], "tile_value": self._tile_value(seat, tile),
            })
        best_ukeire = max(
            (int(candidate["ukeire_total"]) for candidate in candidates if candidate["shanten"] == best_shanten),
            default=0,
        )
        mode = self._defense_mode(seat, best_shanten, threats, best_ukeire)
        if mode == "fold":
            chosen = min(candidates, key=lambda c: (
                float(c["risk"]), int(c["shanten"]), float(c["tile_value"]), tile_to_index(str(c["tile"]))
            ))
        elif mode == "balanced":
            shortlist = [candidate for candidate in candidates if candidate["shanten"] == best_shanten]
            chosen = min(shortlist, key=lambda c: (
                float(c["risk"]), -int(c["ukeire_total"]), -int(c["ukeire_kinds"]),
                float(c["tile_value"]), tile_to_index(str(c["tile"]))
            ))
        else:
            shortlist = [candidate for candidate in candidates if candidate["shanten"] == best_shanten]
            chosen = min(shortlist, key=lambda c: (
                -int(c["ukeire_total"]), -int(c["ukeire_kinds"]), float(c["risk"]) * 0.35,
                float(c["tile_value"]), tile_to_index(str(c["tile"]))
            ))
        return {"mode": mode, "threats": threats, "chosen": chosen["tile"], "candidates": candidates}

    def _choose_advanced_discard(self, seat: int) -> str:
        return str(self.advanced_discard_report(seat)["chosen"])

    def _call_options(self, caller: int, discarder: int, tile: str) -> list[tuple[str, list[str]]]:
        p = self.players[caller]
        opts: list[tuple[str, list[str]]] = []
        if p.hand.count(tile) >= 2:
            opts.append(("pon", [tile, tile, tile]))
        if p.hand.count(tile) >= 3:
            opts.append(("kan", [tile] * 4))
        if caller == (discarder + 1) % 4 and tile_to_index(tile) < 27:
            i = tile_to_index(tile); pos = i % 9
            for a in (pos - 2, pos - 1, pos):
                if 0 <= a <= 6:
                    seq = [index_to_tile(i - pos + a + j) for j in range(3)]
                    needed = seq.copy(); needed.remove(tile)
                    hand = p.hand.copy()
                    if all((hand.remove(x) is None) for x in needed if x in hand) and len(needed) == 2:
                        # Re-check counts because the compact test above operates on a copy.
                        if all(p.hand.count(x) >= needed.count(x) for x in set(needed)):
                            opts.append(("chi", seq))
        return opts

    def _offer_calls(self, discarder: int, tile: str) -> int | None:
        # User gets every legal choice. AI only opens for a value-honor pon/kan;
        # otherwise it stays closed and aims for riichi, ensuring it has a yaku.
        order = [(discarder + n) % 4 for n in range(1, 4)]
        for caller in order:
            opts = self._call_options(caller, discarder, tile)
            if self.players[caller].riichi:
                opts = []
            chosen: tuple[str, list[str]] | None = None
            if caller == 0 and opts and self.interactive:
                chosen = self._choose_user_call(tile, opts)
            elif caller != 0 or not self.interactive:
                seat_wind = WINDS[(caller - self.dealer) % 4]
                if self.players[caller].ai_level == "advanced":
                    chosen = self._advanced_call_choice(caller, tile, opts)
                elif tile in {"P", "F", "C", "E", seat_wind}:
                    chosen = next((o for o in reversed(opts) if o[0] in {"pon", "kan"}), None)
            if chosen:
                kind, meld_tiles = chosen
                p = self.players[caller]
                needed = meld_tiles.copy(); needed.remove(tile)
                for x in needed: p.hand.remove(x)
                p.melds.append(MeldState(kind, meld_tiles)); p.sort()
                setattr(p.stats, kind, getattr(p.stats, kind) + 1)
                print(self._t(
                    f"{self._name(p)} calls {kind} on {tile}.",
                    f"{self._name(p)}对 {tile} 宣布{self._meld_name(kind)}。",
                    f"{self._name(p)}が {tile} を{self._meld_name(kind)}しました。",
                ))
                if kind == "kan":
                    # Daiminkan receives a replacement tile from the dead wall and
                    # reveals another dora indicator. The live wall is shortened by
                    # one so the total number of drawable tiles stays correct.
                    replacement = self.dead_wall.pop()
                    p.hand.append(replacement); p.sort()
                    if self.wall:
                        self.wall.pop()
                    indicator_pos = 4 + 2 * len(self.dora_indicators)
                    if indicator_pos < len(self.dead_wall):
                        self.dora_indicators.append(self.dead_wall[indicator_pos])
                    doras = " ".join(dora_from_indicator(x) for x in self.dora_indicators)
                    print(self._t(
                        f"{self._name(p)} draws a replacement tile; dora is now {doras}.",
                        f"{self._name(p)}进行岭上摸牌；当前宝牌为 {doras}。",
                    ))
                    rinshan_score = self._try_score(caller, replacement, "tsumo")
                    accepts = rinshan_score and (
                        caller != 0 or self._yes_no(
                            self._t(
                                f"Tsumo after kan for {self._score_label(rinshan_score)}?",
                                f"杠后是否自摸（{self._score_label(rinshan_score)}）？",
                            ), True
                        )
                    )
                    if rinshan_score and accepts:
                        self._settle_tsumo(caller, rinshan_score)
                        self._call_win_dealer_continues = caller == self.dealer
                        return None
                if caller == 0 and self.interactive:
                    event = self._t(
                        f"replacement draw {replacement}" if kind == "kan" else f"called {kind} on {tile}",
                        f"岭上摸牌 {replacement}" if kind == "kan" else f"对 {tile} 进行了{self._meld_name(kind)}",
                    )
                    self._show_state(replacement if kind == "kan" else tile, event_label=event)
                discard = self._choose_discard(caller)
                p.hand.remove(discard); p.river.append(discard)
                print(self._t(
                    f"{self._name(p)} discarded {discard}.",
                    f"{self._name(p)}打出了 {discard}。",
                ))
                ron_result = self._resolve_ron(caller, discard)
                if ron_result is not None:
                    self._call_win_dealer_continues = ron_result
                    return None
                # Calling consumes the caller's normal draw; after its immediate
                # discard, play advances to the following seat.
                return (caller + 1) % 4
        return None

    def _choose_user_call(
        self, tile: str, opts: list[tuple[str, list[str]]]
    ) -> tuple[str, list[str]] | None:
        """Prompt pon/kan as yes-no and chi as an explicit sequence choice."""
        by_kind = {kind: [option for option in opts if option[0] == kind] for kind in ("kan", "pon", "chi")}
        if by_kind["kan"] and self._yes_no(self._t(f"Kan {tile}?", f"是否杠 {tile}？"), False):
            return by_kind["kan"][0]
        if by_kind["pon"] and self._yes_no(self._t(f"Pon {tile}?", f"是否碰 {tile}？"), False):
            return by_kind["pon"][0]
        chi = by_kind["chi"]
        if chi:
            print(self._t(f"Chi opportunity on {tile}:", f"可以吃 {tile}："))
            print(self._t("  0. Pass", "  0. 跳过"))
            for i, (_, sequence) in enumerate(chi, 1):
                print(f"  {i}. {' '.join(sequence)}")
            while True:
                raw = input(self._t("Choose chi: ", "请选择吃法：")).strip()
                if raw in {"", "0"}:
                    return None
                if raw.isdigit() and 1 <= int(raw) <= len(chi):
                    return chi[int(raw) - 1]
                print(self._t("Invalid choice.", "选择无效。"))
        return None

    def _advanced_call_choice(
        self, caller: int, tile: str, opts: list[tuple[str, list[str]]]
    ) -> tuple[str, list[str]] | None:
        """Conservative, deterministic call policy for the advanced AI."""
        if not opts:
            return None
        p = self.players[caller]
        if p.riichi:
            return None
        threats = any(i != caller and other.riichi for i, other in enumerate(self.players))
        rank = self._current_rank(caller)
        before_shanten = self._standard_shanten(p)
        before_visible = self._visible_counts(caller)
        before_ukeire = self._ukeire(p, before_visible)[1]
        seat_wind = WINDS[(caller - self.dealer) % 4]
        value_honor = tile in {"P", "F", "C", "E", seat_wind}
        # A closed hand that is already tenpai should preserve its riichi route.
        if p.is_closed and before_shanten <= 0:
            return None
        choices: list[tuple[tuple[int, int, int], tuple[str, list[str]]]] = []
        for option in opts:
            kind, meld_tiles = option
            # Opening without a known yaku is deliberately avoided. This keeps
            # tanyao/flush speculation from creating no-yaku hands.
            if not value_honor:
                continue
            if kind == "kan" and (threats or rank == 1 or len(self.wall) <= 12):
                continue
            needed = meld_tiles.copy(); needed.remove(tile)
            for x in needed:
                p.hand.remove(x)
            p.melds.append(MeldState(kind, meld_tiles))
            after_shanten = self._standard_shanten(p)
            after_visible = self._visible_counts(caller)
            after_ukeire = self._ukeire(p, after_visible)[1]
            p.melds.pop()
            p.hand.extend(needed); p.sort()
            # Do not call if it makes the hand slower. Near tenpai, require the
            # remaining improvement count not to collapse too severely.
            if after_shanten > before_shanten:
                continue
            if before_shanten <= 1 and after_ukeire * 2 < before_ukeire:
                continue
            if kind == "kan" and after_shanten >= before_shanten and after_ukeire < before_ukeire:
                continue
            choices.append(((after_shanten, -after_ukeire, 1 if kind == "kan" else 0), option))
        return min(choices, default=((), None))[1]

    def _show_state(self, draw: str, *, event_label: str | None = None) -> None:
        p = self.players[0]
        scores = ", ".join(f"{self._name(x)} {x.points}" for x in self.players)
        print(self._t(f"\nWall: {len(self.wall)} | Scores: {scores}", f"\n牌山剩余：{len(self.wall)} | 点数：{scores}"))
        hand = " ".join(f"{i + 1}:{t}" for i, t in enumerate(p.hand))
        print(self._t(f"Your hand: {hand}", f"你的手牌：{hand}"))
        print(self._t(
            f"Event: {event_label}" if event_label else f"Draw: {draw}",
            f"事件：{event_label}" if event_label else f"摸牌：{draw}",
        ))
        print(self._t("Player status:", "玩家状态："))
        for i, player in enumerate(self.players):
            dealer = self._t(" dealer", " 庄家") if i == self.dealer else ""
            riichi = self._t(" riichi", " 立直") if player.riichi else ""
            meld_count = len(player.melds)
            meld_status = self._t(
                f" {meld_count} open meld(s)" if meld_count else " closed",
                f" {meld_count}副露" if meld_count else " 门清",
            )
            print(f"  {self._name(player)}:{dealer}{riichi}{meld_status}")
        print(self._t("Rivers:", "牌河："))
        for i, player in enumerate(self.players):
            marker = self._t(" (dealer)", "（庄家）") if i == self.dealer else ""
            river = " ".join(player.river) if player.river else self._t("(empty)", "（空）")
            print(f"  {self._name(player)}{marker}: {river}")
        if self._is_furiten(0):
            reasons: list[str] = []
            if self._discard_furiten(0): reasons.append("own-discard")
            if p.temporary_furiten: reasons.append("temporary")
            if p.riichi_furiten: reasons.append("riichi missed-ron")
            reason_text = {
                "own-discard": "舍牌振听", "temporary": "同巡振听", "riichi missed-ron": "立直见逃振听"
            }
            reason_ja = {
                "own-discard": "捨て牌フリテン", "temporary": "同巡フリテン", "riichi missed-ron": "リーチ後見逃しフリテン"
            }
            reasons_display = (
                reasons if self.language == "en" else
                [reason_text[x] for x in reasons] if self.language == "zh" else
                [reason_ja[x] for x in reasons]
            )
            print(self._t(
                f"Furiten: YES ({', '.join(reasons_display)})",
                f"振听：是（{'、'.join(reasons_display)}）",
            ))
        if p.melds:
            melds = " / ".join(f"{self._meld_name(m.kind)}({' '.join(m.tiles)})" for m in p.melds)
            print(self._t(f"Melds: {melds}", f"副露：{melds}"))
        if self.assist_mode == "hint":
            shanten = self._standard_shanten(p)
            report = None if p.riichi else self.advanced_discard_report(0)
            recommendation = draw if p.riichi else str(report["chosen"])
            after = self._shanten_after_discard(p, recommendation)
            visible = self._visible_counts(0)
            p.hand.remove(recommendation)
            kinds, total = self._ukeire(p, visible)
            p.hand.append(recommendation); p.sort()
            print(self._t("Hint:", "提示："))
            print(self._t(f"  Current shanten: {shanten}", f"  当前向听数：{shanten}"))
            if report is not None:
                mode = str(report["mode"])
                mode_display = {
                    "push": self._t("push", "进攻", "押し"),
                    "balanced": self._t("balanced", "平衡押引", "押し引き"),
                    "fold": self._t("fold", "完全弃和", "ベタオリ"),
                }[mode]
                print(self._t(
                    f"  Decision mode: {mode_display}",
                    f"  决策模式：{mode_display}",
                    f"  判断モード：{mode_display}",
                ))
            print(self._t(
                f"  Recommended discard: {recommendation} (after: {after} shanten, "
                f"{kinds} effective types / {total} visible-adjusted tiles)",
                f"  推荐弃牌：{recommendation}（弃牌后{after}向听，"
                f"{kinds}种有效牌／按可见牌修正后共{total}张）",
            ))
            if report is not None:
                candidates = sorted(
                    report["candidates"],
                    key=lambda c: (
                        0 if c["tile"] == recommendation else 1,
                        int(c["shanten"]), -int(c["ukeire_total"]), float(c["risk"]),
                    ),
                )[:3]
                print(self._t("  Top candidates:", "  候选牌对比：", "  候補比較："))
                for candidate in candidates:
                    tag_names = {
                        "no-threat": ("no-threat", "无威胁", "脅威なし"),
                        "genbutsu": ("genbutsu", "现物", "現物"),
                        "suji": ("suji", "筋", "スジ"), "wall": ("wall", "壁", "壁"),
                        "one-chance": ("one-chance", "一枚机会", "ワンチャンス"),
                        "honor": ("honor", "字牌", "字牌"),
                        "exhausted-honor": ("exhausted-honor", "字牌接近打光", "字牌枯れ"),
                        "dora": ("dora", "宝牌", "ドラ"), "near-dora": ("near-dora", "宝牌周边", "ドラそば"),
                        "dealer-threat": ("dealer-threat", "庄家威胁", "親リーチ"),
                        "late-round": ("late-round", "晚巡", "終盤"),
                    }
                    language_index = {"en": 0, "zh": 1, "ja": 2}[self.language]
                    tags = ",".join(
                        tag_names.get(str(tag), (str(tag), str(tag), str(tag)))[language_index]
                        for tag in candidate["risk_tags"]
                    ) or "-"
                    print(self._t(
                        f"    {candidate['tile']}: shanten={candidate['shanten']}, "
                        f"ukeire={candidate['ukeire_total']}, risk={float(candidate['risk']):.1f}, {tags}",
                        f"    {candidate['tile']}：向听={candidate['shanten']}，"
                        f"进张={candidate['ukeire_total']}，危险度={float(candidate['risk']):.1f}，{tags}",
                        f"    {candidate['tile']}：シャンテン={candidate['shanten']}、"
                        f"受け入れ={candidate['ukeire_total']}、危険度={float(candidate['risk']):.1f}、{tags}",
                    ))
            counter = RemainingTileCounter()
            known = p.hand.copy() + self.dora_indicators
            for player in self.players:
                known.extend(player.river)
                for meld in player.melds:
                    known.extend(meld.tiles)
            counter.set_used_tiles(known)
            remaining = counter.remaining_counts()
            print(self._t("  Tile tracker (estimated remaining from your view):", "  记牌器（从你的视角推算剩余）："))
            labels = ((0, "m/万子"), (9, "p/筒子"), (18, "s/索子"), (27, "honors/字牌"))
            for start, label in labels:
                end = start + (9 if start < 27 else 7)
                row = " ".join(f"{index_to_tile(i)}:{remaining[i]}" for i in range(start, end))
                if self.language == "zh":
                    display_label = label.split("/")[1]
                elif self.language == "ja":
                    display_label = {"m/万子": "萬子", "p/筒子": "筒子", "s/索子": "索子", "honors/字牌": "字牌"}[label]
                else:
                    display_label = label.split("/")[0]
                print(f"    {display_label}: {row}")

    def _score_label(self, sb: ScoreBreakdown) -> str:
        names = [x.name for x in sb.yakuman] or [x.name for x in sb.yaku]
        if self.language in {"zh", "ja"}:
            translations_zh = {
                "Riichi": "立直", "Menzen Tsumo": "门前清自摸和", "Pinfu": "平和",
                "Tanyao": "断幺九", "Yakuhai": "役牌", "Chiitoitsu": "七对子",
                "Toitoi": "对对和", "Honitsu": "混一色", "Chinitsu": "清一色",
                "Sankantsu": "三杠子", "Kokushi Musou": "国士无双",
                "Chuuren Poutou": "九莲宝灯", "Daisangen": "大三元",
                "Suuankou": "四暗刻", "Suuankou Tanki": "四暗刻单骑", "Suukantsu": "四杠子",
            }
            translations_ja = {
                "Riichi": "立直", "Menzen Tsumo": "門前清自摸和", "Pinfu": "平和",
                "Tanyao": "断么九", "Yakuhai": "役牌", "Chiitoitsu": "七対子",
                "Toitoi": "対々和", "Honitsu": "混一色", "Chinitsu": "清一色",
                "Sankantsu": "三槓子", "Kokushi Musou": "国士無双",
                "Chuuren Poutou": "九蓮宝燈", "Daisangen": "大三元",
                "Suuankou": "四暗刻", "Suuankou Tanki": "四暗刻単騎", "Suukantsu": "四槓子",
            }
            translations = translations_zh if self.language == "zh" else translations_ja
            names = [translations.get(name, name) for name in names]
        pts = sb.points.ron_points or sb.points.tsumo_total_points
        return self._t(
            f"{', '.join(names)}; {pts} points",
            f"{'、'.join(names)}；{pts}点",
            f"{'・'.join(names)}、{pts}点",
        )

    def _settle_ron(self, loser: int, winners: list[tuple[int, ScoreBreakdown]]) -> None:
        for winner, sb in winners:
            amount = int(sb.points.ron_points) + self.honba * 300
            self.players[loser].points -= amount; self.players[winner].points += amount
            self.players[winner].stats.wins += 1
            self.players[winner].stats.ron += 1
            self.players[loser].stats.deal_in += 1
            print(self._t(
                f"{self._name(self.players[winner])} ron: {self._score_label(sb)} from {self._name(self.players[loser])}.",
                f"{self._name(self.players[winner])}荣和：{self._score_label(sb)}，放铳者为{self._name(self.players[loser])}。",
            ))
        if winners and self.riichi_sticks:
            self.players[winners[0][0]].points += self.riichi_sticks * 1000
            self.riichi_sticks = 0

    def _settle_tsumo(self, winner: int, sb: ScoreBreakdown) -> None:
        p = sb.points
        for loser in range(4):
            if loser == winner: continue
            if winner == self.dealer:
                amount = int(p.tsumo_dealer_points)
            elif loser == self.dealer:
                amount = int(p.tsumo_dealer_points)
            else:
                amount = int(p.tsumo_non_dealer_points)
            amount += self.honba * 100
            self.players[loser].points -= amount; self.players[winner].points += amount
        self.players[winner].points += self.riichi_sticks * 1000; self.riichi_sticks = 0
        self.players[winner].stats.wins += 1
        self.players[winner].stats.tsumo += 1
        print(self._t(
            f"{self._name(self.players[winner])} tsumo: {self._score_label(sb)}.",
            f"{self._name(self.players[winner])}自摸：{self._score_label(sb)}。",
        ))

    def _yes_no(self, prompt: str, default: bool) -> bool:
        if not self.interactive:
            return default
        marker = self._t(
            "[Y/n]" if default else "[y/N]",
            "[是/否，默认是]" if default else "[是/否，默认否]",
        )
        while True:
            answer = input(f"{prompt} {marker} ").strip().lower()
            if not answer:
                return default
            if answer in {"y", "yes", "是", "s"}:
                return True
            if answer in {"n", "no", "否", "f"}:
                return False
            print(self._t("Please answer yes or no.", "请输入是或否。"))
