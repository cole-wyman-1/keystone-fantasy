import random

from lib.lineup import brute_force_optimal, display_lineup, optimal_lineup

# QB=0, RB=2, WR=4, TE=6, D/ST=16, K=17, BE=20, IR=21, FLEX=23
SLOTS = {0: 1, 2: 1, 4: 1, 6: 1, 23: 1, 20: 3, 21: 1}
QB = [0, 20, 21]
RB = [2, 23, 20, 21]
WR = [4, 23, 20, 21]
TE = [6, 23, 20, 21]


def P(name, elig, pts, slot=20):
    return {"name": name, "eligible_slots": elig, "points": pts, "lineup_slot_id": slot}


def test_flex_takes_best_leftover():
    players = [P("qb", QB, 20, 0), P("rb1", RB, 15, 2), P("rb2", RB, 12), P("wr1", WR, 10, 4), P("wr2", WR, 18),
               P("te", TE, 5, 6), P("te2", TE, 14)]
    total, chosen = optimal_lineup(players, SLOTS)
    # QB 20 + RB 15 + WR 18 + TE 14 + FLEX best leftover (rb2 12) = 79
    assert total == 79
    assert total == brute_force_optimal(players, SLOTS)


def test_ir_player_excluded():
    players = [P("qb", QB, 20, 0), P("qb-ir", QB, 99, 21), P("rb", RB, 10, 2), P("wr", WR, 10, 4), P("te", TE, 10, 6)]
    total, _ = optimal_lineup(players, SLOTS)
    assert total == 50


def test_matches_brute_force_random():
    rng = random.Random(7)
    for _ in range(30):
        players = []
        for i in range(8):
            elig = rng.choice([QB, RB, WR, TE])
            players.append(P(f"p{i}", elig, round(rng.uniform(0, 30), 1)))
        assert optimal_lineup(players, SLOTS)[0] == brute_force_optimal(players, SLOTS)


def test_display_lineup_orders_slots_and_pads_empty():
    names = {0: "QB", 2: "RB", 4: "WR", 6: "TE", 23: "FLEX", 20: "BE", 21: "IR"}
    players = [P("flex", WR, 9, 23), P("wr", WR, 10, 4), P("qb", QB, 20, 0), P("te", TE, 5, 6),   # RB slot left empty
               P("b-wr", {**P("x", WR, 3)}["eligible_slots"], 3), P("ir", RB, 0, 21)]
    for p, pos in zip(players, ["WR", "WR", "QB", "TE", "WR", "RB"]):
        p["position"], p["started"] = pos, p["lineup_slot_id"] not in (20, 21)
    players.append({**P("b-qb", QB, 1), "position": "QB", "started": False})
    d = display_lineup(players, {str(k): v for k, v in SLOTS.items()}, names)   # JSON gives string keys
    assert [s["slot"] for s in d["starters"]] == ["QB", "RB", "WR", "TE", "FLEX"]
    assert [s["player"] and s["player"]["name"] for s in d["starters"]] == ["qb", None, "wr", "te", "flex"]
    assert [p["name"] for p in d["bench"]] == ["b-qb", "b-wr"]
    assert [p["name"] for p in d["ir"]] == ["ir"]
