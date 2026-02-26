from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PointsResult:
    han: int
    fu: int
    limit_name: str | None
    is_dealer: bool
    ron_points: int | None
    tsumo_non_dealer_points: int | None
    tsumo_dealer_points: int | None

    @property
    def tsumo_total_points(self) -> int | None:
        if self.tsumo_non_dealer_points is None and self.tsumo_dealer_points is None:
            return None
        if self.is_dealer:
            # each of the 3 other players pays the dealer amount
            return (self.tsumo_dealer_points or 0) * 3
        # dealer pays dealer amount, two non-dealers pay non-dealer amount
        return (self.tsumo_dealer_points or 0) + (self.tsumo_non_dealer_points or 0) * 2


def _ceil_to_100(x: int) -> int:
    return ((x + 99) // 100) * 100


def estimate_yakuman_points(*, yakuman_multiplier: int, is_dealer: bool, win_type: str) -> PointsResult:
    """
    Estimate points for (double/triple/...) yakuman hands.

    yakuman_multiplier:
      1 = Yakuman
      2 = Double Yakuman
      ...
    """
    if yakuman_multiplier < 1:
        raise ValueError("yakuman_multiplier must be >= 1.")
    if win_type not in {"ron", "tsumo", "both"}:
        raise ValueError("win_type must be one of: ron, tsumo, both")

    base = 8000 * yakuman_multiplier
    limit_name = "Yakuman" if yakuman_multiplier == 1 else f"{yakuman_multiplier}x Yakuman"

    ron_points: int | None = None
    tsumo_non: int | None = None
    tsumo_dealer: int | None = None

    if win_type in {"ron", "both"}:
        mult = 6 if is_dealer else 4
        ron_points = _ceil_to_100(base * mult)

    if win_type in {"tsumo", "both"}:
        if is_dealer:
            tsumo_dealer = _ceil_to_100(base * 2)
            tsumo_non = None
        else:
            tsumo_dealer = _ceil_to_100(base * 2)
            tsumo_non = _ceil_to_100(base * 1)

    return PointsResult(
        han=0,
        fu=0,
        limit_name=limit_name,
        is_dealer=is_dealer,
        ron_points=ron_points,
        tsumo_non_dealer_points=tsumo_non,
        tsumo_dealer_points=tsumo_dealer,
    )


def _limit_base_points(han: int, fu: int, base_points: int) -> tuple[int, str | None]:
    # Base points are capped by limit hands (mangan+).
    # See standard Japanese mahjong scoring rules.
    if han >= 13:
        return 8000, "Kazoe Yakuman"
    if han >= 11:
        return 6000, "Sanbaiman"
    if han >= 8:
        return 4000, "Baiman"
    if han >= 6:
        return 3000, "Haneman"

    is_mangan = han >= 5 or (han == 4 and fu >= 40) or (han == 3 and fu >= 70) or base_points >= 2000
    if is_mangan:
        return 2000, "Mangan"

    return base_points, None


def estimate_points(*, han: int, fu: int, is_dealer: bool, win_type: str) -> PointsResult:
    """
    Estimate points given already-known han/fu.

    win_type: "ron", "tsumo", or "both"
    """
    if han < 1:
        raise ValueError("han must be >= 1 for a winning hand.")
    if fu < 20:
        raise ValueError("fu must be >= 20.")
    if win_type not in {"ron", "tsumo", "both"}:
        raise ValueError("win_type must be one of: ron, tsumo, both")

    base_calc = fu * (2 ** (han + 2))
    base, limit_name = _limit_base_points(han, fu, base_calc)

    ron_points: int | None = None
    tsumo_non: int | None = None
    tsumo_dealer: int | None = None

    if win_type in {"ron", "both"}:
        mult = 6 if is_dealer else 4
        ron_points = _ceil_to_100(base * mult)

    if win_type in {"tsumo", "both"}:
        if is_dealer:
            # Each opponent pays ceil(base*2)
            tsumo_dealer = _ceil_to_100(base * 2)
            tsumo_non = None
        else:
            # Dealer pays ceil(base*2); each non-dealer pays ceil(base*1)
            tsumo_dealer = _ceil_to_100(base * 2)
            tsumo_non = _ceil_to_100(base * 1)

    return PointsResult(
        han=han,
        fu=fu,
        limit_name=limit_name,
        is_dealer=is_dealer,
        ron_points=ron_points,
        tsumo_non_dealer_points=tsumo_non,
        tsumo_dealer_points=tsumo_dealer,
    )

