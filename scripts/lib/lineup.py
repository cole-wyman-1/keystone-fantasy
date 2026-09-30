"""Optimal-lineup solver.

Given the players a team rostered in a week (with their eligible lineup slots and points)
and the league's starting-slot counts, return the best achievable score. Players sitting in
the IR slot are excluded (they could not legally have been started). Slots are filled from
least flexible (QB, K, D/ST ...) to most flexible (FLEX, OP), which is optimal whenever each
flexible slot accepts a superset of some dedicated slots' positions — true for standard ESPN
lineups. tests/test_lineup.py checks it against brute force.
"""
from __future__ import annotations

BENCH_SLOT, IR_SLOT = 20, 21


def starting_slots(lineup_slot_counts: dict[int, int]) -> list[int]:
    slots: list[int] = []
    for slot_id, n in lineup_slot_counts.items():
        if int(slot_id) in (BENCH_SLOT, IR_SLOT):
            continue
        slots.extend([int(slot_id)] * int(n))
    return slots


def optimal_lineup(players: list[dict], lineup_slot_counts: dict[int, int]) -> tuple[float, list[dict]]:
    """Return (optimal_points, chosen [{player, slot}]) for one team-week."""
    pool = [p for p in players if p.get("lineup_slot_id") != IR_SLOT]
    slots = starting_slots(lineup_slot_counts)
    # flexibility = how many distinct pool players could fill this slot type
    flex_rank = {s: sum(1 for p in pool if s in p.get("eligible_slots", [])) for s in set(slots)}
    order = sorted(slots, key=lambda s: (flex_rank[s], s))
    used: set[int] = set()
    chosen: list[dict] = []
    total = 0.0
    for s in order:
        best = None
        for i, p in enumerate(pool):
            if i in used or s not in p.get("eligible_slots", []):
                continue
            if best is None or p["points"] > pool[best]["points"]:
                best = i
        if best is not None:
            used.add(best)
            chosen.append({"player": pool[best], "slot": s})
            total += pool[best]["points"]
    return round(total, 2), chosen


SLOT_ORDER = [0, 2, 4, 6, 23, 7, 16, 17]  # QB RB WR TE FLEX OP D/ST K: the order ESPN shows a lineup in
POSITION_ORDER = ["QB", "RB", "WR", "TE", "K", "D/ST"]


def display_lineup(players: list[dict], lineup_slot_counts: dict[int, int], slot_names: dict[int, str]) -> dict:
    """Lineup as the site shows it: starters in slot order (one entry per starting slot, None when the
    manager left it empty, so two teams in the same league line up row for row), then bench and IR."""
    def order(slot: int) -> tuple[int, int]:
        return (SLOT_ORDER.index(slot) if slot in SLOT_ORDER else len(SLOT_ORDER), slot)

    def pos_key(p: dict) -> tuple[int, float]:
        pos = p.get("position", "")
        return (POSITION_ORDER.index(pos) if pos in POSITION_ORDER else len(POSITION_ORDER), -p["points"])

    counts = {int(k): int(v) for k, v in lineup_slot_counts.items()}
    starters = []
    for slot in sorted((s for s in counts if s not in (BENCH_SLOT, IR_SLOT)), key=order):
        here = [p for p in players if p.get("lineup_slot_id") == slot]
        n = max(counts[slot], len(here))
        for p in (here + [None] * n)[:n]:
            starters.append({"slot": slot_names.get(slot, str(slot)), "player": p})
    known = set(counts) - {BENCH_SLOT, IR_SLOT}
    # a starter in a slot the league settings don't list (shouldn't happen) is still shown
    for p in players:
        if p.get("started") and p.get("lineup_slot_id") not in known:
            starters.append({"slot": slot_names.get(p["lineup_slot_id"], str(p["lineup_slot_id"])), "player": p})
    return {"starters": starters,
            "bench": sorted((p for p in players if p.get("lineup_slot_id") == BENCH_SLOT), key=pos_key),
            "ir": sorted((p for p in players if p.get("lineup_slot_id") == IR_SLOT), key=pos_key)}


def brute_force_optimal(players: list[dict], lineup_slot_counts: dict[int, int]) -> float:
    """Exponential reference implementation for tests only (a slot may stay empty)."""
    pool = [p for p in players if p.get("lineup_slot_id") != IR_SLOT]
    slots = starting_slots(lineup_slot_counts)

    def rec(i: int, used: frozenset) -> float:
        if i == len(slots):
            return 0.0
        best = rec(i + 1, used)  # leave this slot empty
        for j, p in enumerate(pool):
            if j not in used and slots[i] in p.get("eligible_slots", []):
                best = max(best, p["points"] + rec(i + 1, used | {j}))
        return best

    return round(rec(0, frozenset()), 2)
