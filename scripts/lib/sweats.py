"""Monday Night Sweats: the closest matchups still undecided heading into the last day of an NFL week.

Pure functions (tested). Times are ISO-8601 UTC strings or aware datetimes. A starter is "remaining"
when their NFL game kicks off after the moment the lineup was fetched; bye-week players have no game.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from math import erf, sqrt
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
GAME_LENGTH = timedelta(hours=4)   # a game that kicked off less than this long ago may still be live
N_SWEATS = 5


def _dt(v) -> datetime:
    return v if isinstance(v, datetime) else datetime.fromisoformat(v)


def in_final_day_window(kickoffs: list, as_of) -> bool:
    """True when the only NFL games left in the week are on its final day (Monday) and nothing is live:
    i.e. Sunday night is over and Monday night has not kicked off."""
    now = _dt(as_of)
    ks = sorted(_dt(k) for k in kickoffs)
    if not ks:
        return False
    final_day = ks[-1].astimezone(ET).date()
    remaining = [k for k in ks if k > now]
    if not remaining or any(k.astimezone(ET).date() != final_day for k in remaining):
        return False
    return all(k + GAME_LENGTH <= now for k in ks if k <= now)


def remaining_starters(players: list[dict], as_of) -> list[dict]:
    now = _dt(as_of)
    left = [p for p in players if p.get("started") and p.get("game_utc") and _dt(p["game_utc"]) > now]
    return sorted(left, key=lambda p: -(p.get("projected") or 0.0))


def estimate_win_prob(lead: float, mine: list[dict], theirs: list[dict]) -> float:
    """Fallback when ESPN gives no win probability: normal approximation on the projected final margin.
    `lead` is my current score minus theirs; each remaining player adds their projection, with a
    spread that grows with it."""
    mu = lead + sum(p.get("projected") or 0.0 for p in mine) - sum(p.get("projected") or 0.0 for p in theirs)
    var = sum(max(4.0, 0.6 * (p.get("projected") or 0.0)) ** 2 for p in mine + theirs)
    if var == 0:
        return 1.0 if mu > 0 else 0.0 if mu < 0 else 0.5
    return round(0.5 * (1 + erf(mu / sqrt(2 * var))), 3)


def pick_sweats(candidates: list[dict], n: int = N_SWEATS) -> list[dict]:
    """candidates: [{home: {points, win_prob, remaining}, away: {...}, ...}].
    Drops matchups where the trailing team has nobody left (or, if tied, nobody on either side),
    then returns the n whose win probability is closest to a coin flip."""
    keep = []
    for c in candidates:
        h, a = c["home"], c["away"]
        if h["points"] == a["points"]:
            alive = bool(h["remaining"] or a["remaining"])
        else:
            trailing = h if h["points"] < a["points"] else a
            alive = bool(trailing["remaining"])
        if alive and h.get("win_prob") is not None:
            keep.append(c)
    keep.sort(key=lambda c: (abs(c["home"]["win_prob"] - 0.5), -(len(c["home"]["remaining"]) + len(c["away"]["remaining"]))))
    return keep[:n]
