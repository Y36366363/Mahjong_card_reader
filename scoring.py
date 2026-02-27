from __future__ import annotations

from dataclasses import dataclass

from points import estimate_points, estimate_yakuman_points
from tenpai import is_agari_chiitoitsu, is_agari_kokushi, is_agari_standard
from tiles import TERMINAL_HONOR_INDICES, TILE_INDICES, index_to_tile, parse_tiles, red_five_to_five, tile_to_index


@dataclass(frozen=True)
class Yaku:
    name: str
    han_closed: int


@dataclass(frozen=True)
class Yakuman:
    name: str
    multiplier: int = 1


@dataclass(frozen=True)
class ScoreBreakdown:
    win_type: str  # "tsumo" or "ron"
    is_dealer: bool
    hand: list[str]  # raw tokens excluding win tile; may include 0m/0p/0s
    win_tile: str  # raw token
    full_normalized: list[str]  # normalized (0->5); includes extra tiles for kans
    yaku: list[Yaku]
    yakuman: list[Yakuman]
    han: int
    fu: int | None
    dora_han: int
    aka_dora_han: int
    points: object


@dataclass(frozen=True)
class Meld:
    kind: str  # "chi" | "pon" | "kan"
    open: bool  # True if furo/open meld, False if concealed
    tiles: tuple[int, int, int]  # indices (normalized)


@dataclass(frozen=True)
class Decomposition:
    pair: int
    melds: tuple[Meld, Meld, Meld, Meld]


def _is_terminal_or_honor_idx(idx: int) -> bool:
    return idx in TERMINAL_HONOR_INDICES


def _is_simple_idx(idx: int) -> bool:
    # numbered tile 2-8
    if 0 <= idx <= 26:
        n = (idx % 9) + 1
        return 2 <= n <= 8
    return False


def _suit_of_idx(idx: int) -> str | None:
    if 0 <= idx <= 8:
        return "m"
    if 9 <= idx <= 17:
        return "p"
    if 18 <= idx <= 26:
        return "s"
    return None


def _counts_to_tiles(counts: list[int]) -> list[int]:
    out: list[int] = []
    for i, c in enumerate(counts):
        out.extend([i] * c)
    return out


def _decompose_standard_all(counts14: list[int]) -> list[Decomposition]:
    if sum(counts14) != 14:
        raise ValueError("Expected 14 tiles for decomposition.")
    if not is_agari_standard(counts14):
        return []

    decomps: list[Decomposition] = []

    def rec(counts: list[int], melds: list[Meld]) -> None:
        i = next((idx for idx, c in enumerate(counts) if c), -1)
        if i == -1:
            if len(melds) == 4:
                decomps.append(Decomposition(pair=pair_idx, melds=tuple(melds)))  # type: ignore[arg-type]
            return
        if len(melds) > 4:
            return

        # triplet
        if counts[i] >= 3:
            counts[i] -= 3
            melds.append(Meld(kind="pon", open=False, tiles=(i, i, i)))
            rec(counts, melds)
            melds.pop()
            counts[i] += 3

        # sequence
        suit = _suit_of_idx(i)
        if suit is not None:
            pos = i % 9
            if pos <= 6 and counts[i + 1] > 0 and counts[i + 2] > 0:
                counts[i] -= 1
                counts[i + 1] -= 1
                counts[i + 2] -= 1
                melds.append(Meld(kind="chi", open=False, tiles=(i, i + 1, i + 2)))
                rec(counts, melds)
                melds.pop()
                counts[i] += 1
                counts[i + 1] += 1
                counts[i + 2] += 1

    for pair_idx in range(34):
        if counts14[pair_idx] < 2:
            continue
        counts = counts14.copy()
        counts[pair_idx] -= 2
        # honors must be in triplets
        if any(counts[i] % 3 != 0 for i in range(27, 34)):
            continue
        rec(counts, [])

    # de-duplicate (same meld sets can be generated via different recursion orders)
    uniq: dict[tuple[int, tuple[tuple[str, tuple[int, int, int]], ...]], Decomposition] = {}
    for d in decomps:
        meld_sig = tuple(sorted(((m.kind, m.tiles) for m in d.melds), key=lambda x: (x[0], x[1])))
        key = (d.pair, meld_sig)
        uniq[key] = d
    return list(uniq.values())


def _decompose_standard_with_fixed_melds(
    counts: list[int],
    *,
    fixed_melds: list[Meld],
    melds_needed: int,
) -> list[Decomposition]:
    """
    Decompose counts into melds_needed melds + pair, then attach fixed_melds.
    Intended for concealed kan handling (kan is treated as a fixed meld).
    """
    decomps: list[Decomposition] = []

    def rec(counts_work: list[int], melds: list[Meld], pair_idx: int) -> None:
        i = next((idx for idx, c in enumerate(counts_work) if c), -1)
        if i == -1:
            if len(melds) == melds_needed:
                all_melds = fixed_melds + melds
                if len(all_melds) == 4:
                    decomps.append(Decomposition(pair=pair_idx, melds=tuple(all_melds)))  # type: ignore[arg-type]
            return
        if len(melds) > melds_needed:
            return

        # triplet
        if counts_work[i] >= 3:
            counts_work[i] -= 3
            melds.append(Meld(kind="pon", open=False, tiles=(i, i, i)))
            rec(counts_work, melds, pair_idx)
            melds.pop()
            counts_work[i] += 3

        # sequence
        suit = _suit_of_idx(i)
        if suit is not None:
            pos = i % 9
            if pos <= 6 and counts_work[i + 1] > 0 and counts_work[i + 2] > 0:
                counts_work[i] -= 1
                counts_work[i + 1] -= 1
                counts_work[i + 2] -= 1
                melds.append(Meld(kind="chi", open=False, tiles=(i, i + 1, i + 2)))
                rec(counts_work, melds, pair_idx)
                melds.pop()
                counts_work[i] += 1
                counts_work[i + 1] += 1
                counts_work[i + 2] += 1

    for pair_idx in range(34):
        if counts[pair_idx] < 2:
            continue
        counts_work = counts.copy()
        counts_work[pair_idx] -= 2
        # honors must be in triplets
        if any(counts_work[i] % 3 != 0 for i in range(27, 34)):
            continue
        rec(counts_work, [], pair_idx)

    uniq: dict[tuple[int, tuple[tuple[str, tuple[int, int, int]], ...]], Decomposition] = {}
    for d in decomps:
        meld_sig = tuple(sorted(((m.kind, m.tiles) for m in d.melds), key=lambda x: (x[0], x[1])))
        key = (d.pair, meld_sig)
        uniq[key] = d
    return list(uniq.values())


def _aka_dora_han(hand13_raw: list[str], win_raw: str) -> int:
    reds = {"0m", "0p", "0s"}
    return sum(1 for t in hand13_raw if t in reds) + (1 if win_raw in reds else 0)


def _dora_han(full14_normalized: list[str], dora_tiles_raw: list[str]) -> int:
    if not dora_tiles_raw:
        return 0
    dora_norm = [red_five_to_five(t) for t in dora_tiles_raw]
    dset = set(dora_norm)
    return sum(1 for t in full14_normalized if t in dset)


def _is_all_simples(full14_norm: list[str]) -> bool:
    for t in full14_norm:
        if len(t) == 2 and t[1] in ("m", "p", "s"):
            if t[0] in {"1", "9"}:
                return False
        else:
            return False
    return True


def _suits_used(full14_norm: list[str]) -> tuple[set[str], bool]:
    suits: set[str] = set()
    has_honors = False
    for t in full14_norm:
        if len(t) == 2 and t[1] in ("m", "p", "s"):
            suits.add(t[1])
        else:
            has_honors = True
    return suits, has_honors


def _yakuhai_han(decomp: Decomposition, *, seat_wind: str, round_wind: str) -> int:
    value_tiles = {"P", "F", "C", seat_wind, round_wind}
    value_idxs = {TILE_INDICES[v] for v in value_tiles if v in TILE_INDICES}
    han = 0
    for m in decomp.melds:
        if m.kind in {"pon", "kan"} and m.tiles[0] in value_idxs:
            han += 1
    return han


def _is_toitoi(decomp: Decomposition) -> bool:
    return all(m.kind in {"pon", "kan"} for m in decomp.melds)


def _is_pinfu_candidate(decomp: Decomposition, *, seat_wind: str, round_wind: str) -> bool:
    if any(m.kind != "chi" for m in decomp.melds):
        return False
    pair_tile = index_to_tile(decomp.pair)
    if pair_tile in {"P", "F", "C", seat_wind, round_wind}:
        return False
    return True


def _wait_fu(decomp: Decomposition, *, win_idx: int) -> int:
    # Determine if the win tile is a pair wait / closed wait / edge wait.
    if decomp.pair == win_idx:
        return 2  # tanki

    for m in decomp.melds:
        if win_idx not in m.tiles:
            continue
        if m.kind in {"pon", "kan"}:
            return 0
        a, b, c = m.tiles
        # edge waits: 1-2 waiting 3 OR 8-9 waiting 7
        if win_idx == c and (a % 9) == 0 and (b % 9) == 1 and (c % 9) == 2:
            return 2
        if win_idx == a and (a % 9) == 6 and (b % 9) == 7 and (c % 9) == 8:
            return 2
        # closed wait: winning tile is the middle of a sequence
        if win_idx == b:
            return 2
        return 0
    return 0


def _meld_fu(decomp: Decomposition) -> int:
    fu = 0
    for m in decomp.melds:
        if m.kind not in {"pon", "kan"}:
            continue
        is_term = _is_terminal_or_honor_idx(m.tiles[0])
        if m.kind == "pon":
            if m.open:
                fu += 4 if is_term else 2
            else:
                fu += 8 if is_term else 4
        else:  # kan
            if m.open:
                fu += 16 if is_term else 8
            else:
                fu += 32 if is_term else 16
    return fu


def _pair_fu(pair_idx: int, *, seat_wind: str, round_wind: str) -> int:
    t = index_to_tile(pair_idx)
    if t in {"P", "F", "C"}:
        return 2
    if t == seat_wind:
        return 2
    if t == round_wind:
        return 2
    return 0


def _fu_standard(
    decomp: Decomposition,
    *,
    win_type: str,
    win_idx: int,
    seat_wind: str,
    round_wind: str,
    is_pinfu: bool,
    is_closed: bool,
) -> int:
    # Base fu
    if is_pinfu and win_type == "tsumo":
        return 20

    fu = 20
    if win_type == "ron":
        if is_closed:
            fu += 10  # menzen ron
    else:
        fu += 2  # tsumo

    fu += _pair_fu(decomp.pair, seat_wind=seat_wind, round_wind=round_wind)
    fu += _meld_fu(decomp)
    fu += _wait_fu(decomp, win_idx=win_idx)

    # Pinfu special: no fu other than tsumo/ron; still rounds
    if is_pinfu:
        fu = 30 if (win_type == "ron" and is_closed) else 20

    # round up to 10
    fu = ((fu + 9) // 10) * 10
    return max(fu, 30)


def _yakuman_from_tiles(full14_counts: list[int], full14_norm: list[str], *, win_type: str, decomp: Decomposition | None, win_idx: int | None) -> list[Yakuman]:
    y: list[Yakuman] = []

    if is_agari_kokushi(full14_counts):
        y.append(Yakuman("Kokushi Musou"))
        return y

    # Chuuren Poutou (closed-only; we assume closed)
    suits, has_honors = _suits_used(full14_norm)
    if len(suits) == 1 and not has_honors:
        suit = next(iter(suits))
        base = [0] * 34
        for n in [1, 1, 1, 2, 3, 4, 5, 6, 7, 8, 9, 9, 9]:
            base[tile_to_index(f"{n}{suit}")] += 1
        ok = True
        extra = 0
        for i in range(34):
            if full14_counts[i] < base[i]:
                ok = False
                break
            extra += full14_counts[i] - base[i]
        if ok and extra == 1:
            y.append(Yakuman("Chuuren Poutou"))

    if decomp is not None:
        # Daisangen
        dragon_idxs = {TILE_INDICES["P"], TILE_INDICES["F"], TILE_INDICES["C"]}
        if all(any(m.kind in {"pon", "kan"} and m.tiles[0] == di for m in decomp.melds) for di in dragon_idxs):
            y.append(Yakuman("Daisangen"))

        # Suuankou (simplified, closed hand assumed)
        triplets = [m for m in decomp.melds if m.kind in {"pon", "kan"}]
        if len(triplets) == 4 and win_idx is not None:
            if win_type == "tsumo":
                y.append(Yakuman("Suuankou"))
            else:
                # ron only allowed on tanki in this simplified rule
                if decomp.pair == win_idx:
                    y.append(Yakuman("Suuankou Tanki", multiplier=2))

    return y


def score_points_from_config(
    *,
    hand_text: str,
    win_tile_text: str,
    win_type: str,
    is_dealer: bool,
    dora_text: str | None = None,
    seat_wind: str = "E",
    round_wind: str = "E",
    riichi: bool = False,
    furo_sets: int = 0,
    kan_sets: int = 0,
    ankan_tiles: list[str] | None = None,
    kan_tiles: list[str] | None = None,
) -> ScoreBreakdown:
    """
    Main entrypoint for points mode.

    Inputs:
      - hand_text: tiles excluding the win tile (may include 0m/0p/0s)
      - win_tile_text: the winning tile (tsumo draw or ron tile)
      - win_type: "tsumo" or "ron"
      - dora_text: optional tiles that are dora (NOT indicators), space-separated

    Assumptions:
      - supports open melds (furo) and multiple kans via config
    """
    if win_type not in {"tsumo", "ron"}:
        raise ValueError("win_type must be 'tsumo' or 'ron'")

    hand_raw = parse_tiles(hand_text, keep_red_fives=True)
    win_raw_list = parse_tiles(win_tile_text, keep_red_fives=True)
    if len(win_raw_list) != 1:
        raise ValueError("'win_tile' must be exactly one tile.")
    win_raw = win_raw_list[0]

    ankan_tiles = ankan_tiles or []
    kan_tiles = kan_tiles or []
    if kan_sets != len(kan_tiles):
        raise ValueError("kan_sets must equal len(kan_tiles).")
    if furo_sets < 0 or kan_sets < 0 or kan_sets > furo_sets:
        raise ValueError("Invalid furo/kan counts: require 0 <= kan_sets <= furo_sets.")

    total_kans = len(ankan_tiles) + len(kan_tiles)
    expected_hand_len = 13 + total_kans
    if len(hand_raw) != expected_hand_len:
        raise ValueError(f"In points mode, 'hand' must contain exactly {expected_hand_len} tiles (13 + total_kans).")

    # Parse furo melds from the end of hand (open melds).
    remaining = hand_raw.copy()
    fixed_melds: list[Meld] = []

    # Open kans: last kan_sets melds among the furo block; each is 4 identical tiles.
    open_kan_tiles_norm = [red_five_to_five(t) for t in kan_tiles]
    open_kan_pool = open_kan_tiles_norm.copy()

    for _ in range(kan_sets):
        if len(remaining) < 4:
            raise ValueError("Not enough tiles to parse open kan meld(s) from the end of hand.")
        meld_tiles_raw = [remaining.pop(), remaining.pop(), remaining.pop(), remaining.pop()]
        meld_tiles_norm = [red_five_to_five(t) for t in meld_tiles_raw]
        if len(set(meld_tiles_norm)) != 1:
            raise ValueError("Open kan meld must be four identical tiles.")
        tile_norm = meld_tiles_norm[0]
        if tile_norm not in open_kan_pool:
            raise ValueError(f"Open kan tile '{tile_norm}' not found in kan_tiles list.")
        open_kan_pool.remove(tile_norm)
        idx = tile_to_index(tile_norm)
        fixed_melds.append(Meld(kind="kan", open=True, tiles=(idx, idx, idx)))

    # Remaining open furo melds (chi/pon): 3 tiles each.
    open_melds_to_parse = furo_sets - kan_sets
    for _ in range(open_melds_to_parse):
        if len(remaining) < 3:
            raise ValueError("Not enough tiles to parse furo meld(s) from the end of hand.")
        meld_tiles_raw = [remaining.pop(), remaining.pop(), remaining.pop()]
        meld_tiles_norm = [red_five_to_five(t) for t in meld_tiles_raw]
        if len(set(meld_tiles_norm)) == 1:
            idx = tile_to_index(meld_tiles_norm[0])
            fixed_melds.append(Meld(kind="pon", open=True, tiles=(idx, idx, idx)))
            continue
        # chi: same suit, consecutive
        try:
            idxs = sorted(tile_to_index(t) for t in meld_tiles_norm)
        except Exception as e:
            raise ValueError(f"Invalid tiles in furo meld: {meld_tiles_raw}") from e
        suits = {_suit_of_idx(i) for i in idxs}
        if None in suits or len(suits) != 1:
            raise ValueError(f"Furo chi meld must be suited tiles: got {meld_tiles_norm}")
        if not (idxs[0] + 1 == idxs[1] and idxs[1] + 1 == idxs[2]):
            raise ValueError(f"Furo chi meld must be consecutive tiles: got {meld_tiles_norm}")
        fixed_melds.append(Meld(kind="chi", open=True, tiles=(idxs[0], idxs[1], idxs[2])))

    # Concealed kans (ankan): provided as a list of tile names.
    for t in ankan_tiles:
        tile_norm = red_five_to_five(t)
        idx = tile_to_index(tile_norm)
        fixed_melds.append(Meld(kind="kan", open=False, tiles=(idx, idx, idx)))

    # Normalize for structural analysis (0->5), but preserve raw for aka dora
    full_norm = [red_five_to_five(t) for t in hand_raw] + [red_five_to_five(win_raw)]
    full_counts = [0] * 34
    for t in full_norm:
        full_counts[tile_to_index(t)] += 1

    dora_tiles_raw: list[str] = []
    if dora_text:
        dora_tiles_raw = parse_tiles(dora_text, keep_red_fives=True)

    aka_dora = _aka_dora_han(hand_raw, win_raw)
    dora_han = _dora_han(full_norm, dora_tiles_raw)

    yakuman: list[Yakuman] = []
    yaku: list[Yaku] = []

    # Special hands first
    is_closed = not any(m.open for m in fixed_melds)
    if riichi and not is_closed:
        raise ValueError("riichi=true is not allowed when the hand is open (furo).")

    if total_kans == 4:
        yakuman.append(Yakuman("Suukantsu"))

    if total_kans == 0 and is_agari_kokushi(full_counts):
        yakuman = [Yakuman("Kokushi Musou")]
        yakuman_mult = sum(y.multiplier for y in yakuman)
        pts = estimate_yakuman_points(yakuman_multiplier=yakuman_mult, is_dealer=is_dealer, win_type=win_type)
        return ScoreBreakdown(
            win_type=win_type,
            is_dealer=is_dealer,
            hand=hand_raw,
            win_tile=win_raw,
            full_normalized=full_norm,
            yaku=[],
            yakuman=yakuman,
            han=0,
            fu=None,
            dora_han=0,
            aka_dora_han=0,
            points=pts,
        )

    # Chiitoitsu
    if total_kans == 0 and furo_sets == 0 and is_agari_chiitoitsu(full_counts):
        yaku.append(Yaku("Chiitoitsu", 2))
        if riichi:
            yaku.append(Yaku("Riichi", 1))
        if win_type == "tsumo" and is_closed:
            yaku.append(Yaku("Menzen Tsumo", 1))
        han = sum(y.han_closed for y in yaku) + dora_han + aka_dora
        fu = 25
        if not yaku:
            raise ValueError("Winning hand has no yaku (dora/aka-dora do not count as yaku).")
        pts = estimate_points(han=han, fu=fu, is_dealer=is_dealer, win_type=win_type)
        return ScoreBreakdown(
            win_type=win_type,
            is_dealer=is_dealer,
            hand=hand_raw,
            win_tile=win_raw,
            full_normalized=full_norm,
            yaku=yaku,
            yakuman=[],
            han=han,
            fu=fu,
            dora_han=dora_han,
            aka_dora_han=aka_dora,
            points=pts,
        )

    # Standard hand (4 melds + pair)
    melds_needed = 4 - len(fixed_melds)
    if melds_needed < 0:
        raise ValueError("Too many fixed melds (furo + kans).")

    counts_for_decomp = full_counts.copy()
    for m in fixed_melds:
        remove_n = 4 if m.kind == "kan" else 3
        idxs = list(m.tiles)
        for i in range(remove_n):
            idx = idxs[0] if m.kind in {"pon", "kan"} else idxs[i]
            counts_for_decomp[idx] -= 1
            if counts_for_decomp[idx] < 0:
                raise ValueError("Fixed meld tiles do not match the provided hand tiles.")

    decomps = _decompose_standard_with_fixed_melds(counts_for_decomp, fixed_melds=fixed_melds, melds_needed=melds_needed)
    if not decomps:
        raise ValueError("Hand is not a winning hand with the provided win_tile.")

    win_idx = tile_to_index(red_five_to_five(win_raw))

    best: ScoreBreakdown | None = None
    for decomp in decomps:
        yakuman = _yakuman_from_tiles(full_counts, full_norm, win_type=win_type, decomp=decomp, win_idx=win_idx)
        if total_kans == 4:
            yakuman = [Yakuman("Suukantsu")]
        if yakuman:
            # For now, treat yakuman as limit; do not add dora/aka-dora.
            yakuman_mult = sum(y.multiplier for y in yakuman)
            pts = estimate_yakuman_points(yakuman_multiplier=yakuman_mult, is_dealer=is_dealer, win_type=win_type)
            cand = ScoreBreakdown(
                win_type=win_type,
                is_dealer=is_dealer,
                hand=hand_raw,
                win_tile=win_raw,
                full_normalized=full_norm,
                yaku=[],
                yakuman=yakuman,
                han=0,
                fu=None,
                dora_han=0,
                aka_dora_han=0,
                points=pts,
            )
        else:
            yaku = []
            if riichi:
                yaku.append(Yaku("Riichi", 1))
            if win_type == "tsumo" and is_closed:
                yaku.append(Yaku("Menzen Tsumo", 1))
            if total_kans == 3:
                yaku.append(Yaku("Sankantsu", 2))

            # Tile-only yaku
            if _is_all_simples(full_norm):
                yaku.append(Yaku("Tanyao", 1))

            suits, has_honors = _suits_used(full_norm)
            if len(suits) == 1:
                if has_honors:
                    yaku.append(Yaku("Honitsu", 3 if is_closed else 2))
                else:
                    yaku.append(Yaku("Chinitsu", 6 if is_closed else 5))

            if _is_toitoi(decomp):
                yaku.append(Yaku("Toitoi", 2))

            yakuhai = _yakuhai_han(decomp, seat_wind=seat_wind, round_wind=round_wind)
            for _ in range(yakuhai):
                yaku.append(Yaku("Yakuhai", 1))

            # Pinfu (needs ryanmen wait; we approximate by "not (edge/closed/pair wait)")
            pinfu_candidate = _is_pinfu_candidate(decomp, seat_wind=seat_wind, round_wind=round_wind)
            wait_fu = _wait_fu(decomp, win_idx=win_idx)
            is_pinfu = is_closed and pinfu_candidate and wait_fu == 0
            if is_pinfu:
                yaku.append(Yaku("Pinfu", 1))

            if not yaku:
                raise ValueError("Winning hand has no yaku (dora/aka-dora do not count as yaku).")

            han = sum(y.han_closed for y in yaku) + dora_han + aka_dora
            fu = _fu_standard(
                decomp,
                win_type=win_type,
                win_idx=win_idx,
                seat_wind=seat_wind,
                round_wind=round_wind,
                is_pinfu=is_pinfu,
                is_closed=is_closed,
            )
            pts = estimate_points(han=han, fu=fu, is_dealer=is_dealer, win_type=win_type)
            cand = ScoreBreakdown(
                win_type=win_type,
                is_dealer=is_dealer,
                hand=hand_raw,
                win_tile=win_raw,
                full_normalized=full_norm,
                yaku=yaku,
                yakuman=[],
                han=han,
                fu=fu,
                dora_han=dora_han,
                aka_dora_han=aka_dora,
                points=pts,
            )

        if best is None:
            best = cand
        else:
            # pick the higher total (ron/tsumo total). prefer larger total points.
            def total_points(sb: ScoreBreakdown) -> int:
                p = sb.points
                if getattr(p, "ron_points", None) is not None:
                    return int(p.ron_points)
                t = getattr(p, "tsumo_total_points", None)
                return int(t) if t is not None else 0

            if total_points(cand) > total_points(best):
                best = cand

    assert best is not None
    return best

