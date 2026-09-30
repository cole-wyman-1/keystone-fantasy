from lib.sweats import estimate_win_prob, in_final_day_window, pick_sweats, remaining_starters

# NFL week: Thu night, Sunday slate, Sunday night, Monday night (UTC)
THU, SUN1, SNF, MNF = "2026-09-25T00:15:00+00:00", "2026-09-27T17:00:00+00:00", "2026-09-28T00:20:00+00:00", "2026-09-29T00:15:00+00:00"
WEEK = [THU, SUN1, SNF, MNF]


def test_window_is_between_sunday_night_and_monday_night():
    assert in_final_day_window(WEEK, "2026-09-28T11:00:00+00:00")        # Monday 7am ET refresh
    assert in_final_day_window(WEEK, "2026-09-28T04:30:00+00:00")        # late Sunday night, SNF over
    assert not in_final_day_window(WEEK, "2026-09-28T02:00:00+00:00")    # SNF still being played
    assert not in_final_day_window(WEEK, "2026-09-25T11:00:00+00:00")    # Friday: Sunday still to come
    assert not in_final_day_window(WEEK, "2026-09-29T11:00:00+00:00")    # Tuesday: nothing left
    assert not in_final_day_window([], "2026-09-28T11:00:00+00:00")


def P(name, started, game_utc, proj=10.0):
    return {"name": name, "started": started, "game_utc": game_utc, "projected": proj}


def test_remaining_starters_skips_bench_byes_and_finished_games():
    players = [P("mnf-starter", True, MNF, 8), P("mnf-star", True, MNF, 20), P("mnf-bench", False, MNF),
               P("sunday", True, SUN1), P("bye", True, None)]
    assert [p["name"] for p in remaining_starters(players, "2026-09-28T11:00:00+00:00")] == ["mnf-star", "mnf-starter"]


def side(points, wp, remaining):
    return {"points": points, "win_prob": wp, "remaining": [P(f"p{i}", True, MNF) for i in range(remaining)]}


def test_pick_drops_dead_matchups_and_ranks_by_coin_flip():
    cands = [
        {"key": "blowout", "home": side(140, 0.95, 1), "away": side(90, 0.05, 1)},
        {"key": "trailer-done", "home": side(100, 0.52, 1), "away": side(98, 0.48, 0)},   # loser has nobody left
        {"key": "closest", "home": side(100, 0.49, 0), "away": side(95, 0.51, 1)},        # leader done, trailer alive
        {"key": "close", "home": side(80, 0.40, 2), "away": side(101, 0.60, 1)},
        {"key": "tied-dead", "home": side(100, 0.5, 0), "away": side(100, 0.5, 0)},
    ]
    assert [c["key"] for c in pick_sweats(cands)] == ["closest", "close", "blowout"]
    assert [c["key"] for c in pick_sweats(cands, n=1)] == ["closest"]


def test_estimate_win_prob():
    star = [P("a", True, MNF, 15)]
    assert estimate_win_prob(0, star, star) == 0.5
    assert estimate_win_prob(10, [], star) < 0.5 < estimate_win_prob(20, [], star)   # trailing by 10 with a 15-pt player left
    assert estimate_win_prob(5, [], []) == 1.0 and estimate_win_prob(-5, [], []) == 0.0
