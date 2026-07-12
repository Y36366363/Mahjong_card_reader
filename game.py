from __future__ import annotations

import random
from dataclasses import dataclass, field

from scoring import ScoreBreakdown, score_points_from_config
from shanten import shanten_standard
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
class PlayerState:
    name: str
    points: int = 25_000
    hand: list[str] = field(default_factory=list)
    melds: list[MeldState] = field(default_factory=list)
    river: list[str] = field(default_factory=list)
    riichi: bool = False
    temporary_furiten: bool = False
    riichi_furiten: bool = False

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

    def __init__(self, *, seed: int | None = None, interactive: bool = True) -> None:
        self.rng = random.Random(seed)
        self.seed = seed
        self.interactive = interactive
        self.players = [PlayerState("You"), PlayerState("AI-1"), PlayerState("AI-2"), PlayerState("AI-3")]
        self.dealer = 0
        self.round_hand = 0
        self.honba = 0
        self.riichi_sticks = 0
        self.wall: list[str] = []
        self.dead_wall: list[str] = []
        self.dora_indicators: list[str] = []
        self._call_win_dealer_continues: bool | None = None

    def play(self) -> None:
        print(f"East-round game started (seed={self.seed!r}).")
        while self.round_hand < 4 and all(p.points > 0 for p in self.players):
            dealer_continues = self._play_hand()
            if dealer_continues:
                self.honba += 1
            else:
                self.dealer = (self.dealer + 1) % 4
                self.round_hand += 1
                self.honba = 0
        print("\nFinal ranking")
        ranked = sorted(enumerate(self.players), key=lambda x: (-x[1].points, x[0]))
        for rank, (_, p) in enumerate(ranked, 1):
            print(f"  {rank}. {p.name}: {p.points}")

    def _new_wall(self) -> None:
        tiles = [index_to_tile(i) for i in range(34) for _ in range(4)]
        self.rng.shuffle(tiles)
        self.dead_wall = tiles[-14:]
        self.wall = tiles[:-14]
        self.dora_indicators = [self.dead_wall[4]]

    def _play_hand(self) -> bool:
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
        print(f"\nEast {self.round_hand + 1}, dealer={self.players[self.dealer].name}, honba={self.honba}")
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
            if score and (turn != 0 or self._yes_no(f"Tsumo {draw} for {self._score_label(score)}?", True)):
                self._settle_tsumo(turn, score)
                return turn == self.dealer
            if turn == 0 and self.interactive:
                self._show_state(draw)
            # After riichi the hand is locked: if the draw is not a winning tile,
            # the drawn tile must be discarded unchanged.
            discard = draw if p.riichi else self._choose_discard(turn)
            p.hand.remove(discard); p.river.append(discard)
            if turn == 0 and self.interactive:
                print(f"You discarded {discard}.")

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

        print("Exhaustive draw. Dealer continues only if tenpai.")
        tenpai = [i for i, player in enumerate(self.players) if self._standard_shanten(player) == 0]
        noten = [i for i in range(4) if i not in tenpai]
        if tenpai and noten:
            gain = 3000 // len(tenpai)
            loss = 3000 // len(noten)
            for i in tenpai:
                self.players[i].points += gain
            for i in noten:
                self.players[i].points -= loss
            print("Tenpai payment: " + ", ".join(self.players[i].name for i in tenpai) + " receive 3000 total.")
        dealer_tenpai = self.dealer in tenpai
        return dealer_tenpai

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
                    print(f"Ron on {discard} is unavailable: you are furiten.")
                continue
            accepted = other != 0 or self._yes_no(
                f"Ron on {discard} for {self._score_label(score)}?", True
            )
            if accepted:
                winners.append((other, score))
            else:
                missed = self.players[other]
                if missed.riichi:
                    missed.riichi_furiten = True
                    print("You passed ron after riichi: furiten lasts until this hand ends.")
                else:
                    missed.temporary_furiten = True
                    print("You passed ron: temporary furiten lasts until your next draw.")
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
                raw = input("Discard tile (or index): ").strip()
                if raw.isdigit() and 1 <= int(raw) <= len(p.hand):
                    return p.hand[int(raw) - 1]
                if raw in p.hand:
                    return raw
                print("That tile is not in your hand.")
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
        discard = best[0]
        # Closed AI declares riichi at tenpai. This both supplies a yaku and makes
        # its later discard behaviour deterministic.
        p.hand.remove(discard)
        can_riichi = best_shanten == 0 and p.is_closed and not p.riichi and p.points >= 1000
        declare = can_riichi and (seat != 0 or self._yes_no("Declare riichi?", False))
        if declare:
            p.riichi = True; p.points -= 1000; self.riichi_sticks += 1
            print(f"{p.name} declares riichi.")
        p.hand.append(discard); p.sort()
        return discard

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
            chosen: tuple[str, list[str]] | None = None
            if caller == 0 and opts and self.interactive:
                labels = [f"{i + 1}:{kind} {' '.join(ts)}" for i, (kind, ts) in enumerate(opts)]
                raw = input("Call? 0:pass, " + ", ".join(labels) + " > ").strip()
                if raw.isdigit() and 1 <= int(raw) <= len(opts):
                    chosen = opts[int(raw) - 1]
            elif caller != 0:
                seat_wind = WINDS[(caller - self.dealer) % 4]
                if tile in {"P", "F", "C", "E", seat_wind}:
                    chosen = next((o for o in reversed(opts) if o[0] in {"pon", "kan"}), None)
            if chosen:
                kind, meld_tiles = chosen
                p = self.players[caller]
                needed = meld_tiles.copy(); needed.remove(tile)
                for x in needed: p.hand.remove(x)
                p.melds.append(MeldState(kind, meld_tiles)); p.sort()
                print(f"{p.name} calls {kind} on {tile}.")
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
                    print(f"{p.name} draws a replacement tile; dora is now " +
                          " ".join(dora_from_indicator(x) for x in self.dora_indicators) + ".")
                    rinshan_score = self._try_score(caller, replacement, "tsumo")
                    accepts = rinshan_score and (
                        caller != 0 or self._yes_no(
                            f"Tsumo after kan for {self._score_label(rinshan_score)}?", True
                        )
                    )
                    if rinshan_score and accepts:
                        self._settle_tsumo(caller, rinshan_score)
                        self._call_win_dealer_continues = caller == self.dealer
                        return None
                discard = self._choose_discard(caller)
                p.hand.remove(discard); p.river.append(discard)
                print(f"{p.name} discarded {discard}.")
                ron_result = self._resolve_ron(caller, discard)
                if ron_result is not None:
                    self._call_win_dealer_continues = ron_result
                    return None
                # Calling consumes the caller's normal draw; after its immediate
                # discard, play advances to the following seat.
                return (caller + 1) % 4
        return None

    def _show_state(self, draw: str) -> None:
        p = self.players[0]
        print(f"\nWall: {len(self.wall)} | Scores: " + ", ".join(f"{x.name} {x.points}" for x in self.players))
        print("Your hand: " + " ".join(f"{i + 1}:{t}" for i, t in enumerate(p.hand)))
        print(f"Draw: {draw} | Shanten: {self._standard_shanten(p)}")
        print("Rivers:")
        for i, player in enumerate(self.players):
            marker = " (dealer)" if i == self.dealer else ""
            river = " ".join(player.river) if player.river else "(empty)"
            print(f"  {player.name}{marker}: {river}")
        if self._is_furiten(0):
            reasons: list[str] = []
            if self._discard_furiten(0): reasons.append("own-discard")
            if p.temporary_furiten: reasons.append("temporary")
            if p.riichi_furiten: reasons.append("riichi missed-ron")
            print(f"Furiten: YES ({', '.join(reasons)})")
        if p.melds:
            print("Melds: " + " / ".join(f"{m.kind}({' '.join(m.tiles)})" for m in p.melds))

    @staticmethod
    def _score_label(sb: ScoreBreakdown) -> str:
        names = [x.name for x in sb.yakuman] or [x.name for x in sb.yaku]
        pts = sb.points.ron_points or sb.points.tsumo_total_points
        return f"{', '.join(names)}; {pts} points"

    def _settle_ron(self, loser: int, winners: list[tuple[int, ScoreBreakdown]]) -> None:
        for winner, sb in winners:
            amount = int(sb.points.ron_points) + self.honba * 300
            self.players[loser].points -= amount; self.players[winner].points += amount
            print(f"{self.players[winner].name} ron: {self._score_label(sb)} from {self.players[loser].name}.")
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
        print(f"{self.players[winner].name} tsumo: {self._score_label(sb)}.")

    def _yes_no(self, prompt: str, default: bool) -> bool:
        if not self.interactive: return default
        answer = input(prompt + " [Y/n] ").strip().lower()
        return answer not in {"n", "no"}
