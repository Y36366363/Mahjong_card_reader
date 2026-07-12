from __future__ import annotations

import random
from dataclasses import dataclass, field

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
    ) -> None:
        self.rng = random.Random(seed)
        self.seed = seed
        self.interactive = interactive
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

    def play(self) -> None:
        levels = ", ".join(f"{p.name}={p.ai_level}" for p in self.players)
        print(f"East-round game started (seed={self.seed!r}; {levels}).")
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
            print(f"Unclaimed riichi sticks ({self.riichi_sticks}) go to {self.players[leader].name}.")
            self.riichi_sticks = 0
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
        if p.ai_level == "advanced":
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
            print(f"{p.name} declares riichi.")
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
        visible = self.players[seat].hand.copy()
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

    def _defense_risk(self, seat: int, tile: str, threats: list[int], visible: list[int]) -> float:
        if not threats:
            return 0.0
        i = tile_to_index(tile)
        risk = 0.0
        for opponent in threats:
            river = self.players[opponent].river
            if tile in river:  # genbutsu
                continue
            one = 5.0
            if i >= 27:
                one = max(0.3, 3.2 - visible[i])  # exhausted honors become safer
            else:
                pos = i % 9
                river_pos = {tile_to_index(x) % 9 for x in river if tile_to_index(x) // 9 == i // 9}
                # Basic suji: 1/4/7, 2/5/8, 3/6/9 relationships.
                if any(abs(pos - r) == 3 for r in river_pos):
                    one -= 2.0
                # A complete adjacent wall reduces sequence danger.
                neighbors = [j for j in (i - 1, i + 1) if 0 <= j < 27 and j // 9 == i // 9]
                if any(visible[j] >= 4 for j in neighbors):
                    one -= 1.2
            risk += max(0.1, one)
        return risk

    def _choose_advanced_discard(self, seat: int) -> str:
        p = self.players[seat]
        visible = self._visible_counts(seat)
        threats = [i for i, other in enumerate(self.players) if i != seat and other.riichi]
        rank = 1 + sum(other.points > p.points for other in self.players)
        shanten_by_tile = {
            tile: self._shanten_after_discard(p, tile)
            for tile in sorted(set(p.hand), key=tile_sort_key)
        }
        best_shanten = min(shanten_by_tile.values())
        fold = bool(threats) and (best_shanten >= 2 or (rank == 1 and best_shanten >= 1))
        if fold:
            return min(
                shanten_by_tile,
                key=lambda tile: (
                    self._defense_risk(seat, tile, threats, visible),
                    shanten_by_tile[tile],
                    self._tile_value(seat, tile),
                    tile_to_index(tile),
                ),
            )

        # Ukeire is the expensive part of evaluation. Only equal-best-shanten
        # discards can win, so avoid evaluating candidates that are already slower.
        shortlist = [tile for tile, sh in shanten_by_tile.items() if sh == best_shanten]
        candidates: list[tuple[tuple[float, ...], str]] = []
        for tile in shortlist:
            p.hand.remove(tile)
            kinds, total = self._ukeire(p, visible)
            p.hand.append(tile); p.sort()
            risk = self._defense_risk(seat, tile, threats, visible)
            value = self._tile_value(seat, tile)
            key = (-float(total), -float(kinds), risk * 0.35, value, float(tile_to_index(tile)))
            candidates.append((key, tile))
        return min(candidates)[1]

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
        rank = 1 + sum(other.points > p.points for other in self.players)
        before_shanten = self._standard_shanten(p)
        before_visible = self._visible_counts(caller)
        before_ukeire = self._ukeire(p, before_visible)[1]
        seat_wind = WINDS[(caller - self.dealer) % 4]
        value_honor = tile in {"P", "F", "C", "E", seat_wind}
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
            choices.append(((after_shanten, -after_ukeire, 1 if kind == "kan" else 0), option))
        return min(choices, default=((), None))[1]

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
