"""Pure functions that turn normalized weekly data into standings, streaks, records, luck
and power rankings. No file I/O here so everything is unit-testable.

Input shape (one league):
  games: list of {week, team_id, points, opp_id, opp_points, result: "W"|"L"|"T", is_playoff}
         — two rows per matchup (one per side), completed weeks only.
"""
from __future__ import annotations

from collections import defaultdict


def games_from_weeks(weeks: list[dict]) -> list[dict]:
    """Flatten completed weeks' matchups into per-team game rows."""
    games = []
    for w in weeks:
        if not w.get("complete"):
            continue
        for m in w["matchups"]:
            if m.get("is_bye") or m["away_team_id"] is None:
                continue
            hp, ap = m["home_points"], m["away_points"]
            hres = "T" if hp == ap else ("W" if hp > ap else "L")
            ares = "T" if hres == "T" else ("L" if hres == "W" else "W")
            base = {"week": w["matchup_period"], "is_playoff": m.get("playoff_tier", "NONE") != "NONE"}
            games.append({**base, "team_id": m["home_team_id"], "points": hp, "opp_id": m["away_team_id"], "opp_points": ap, "result": hres})
            games.append({**base, "team_id": m["away_team_id"], "points": ap, "opp_id": m["home_team_id"], "opp_points": hp, "result": ares})
    return games


def streaks(results: list[str]) -> dict:
    """results in week order. Returns current streak + longest W / L runs (with end index)."""
    cur_type, cur_len = "", 0
    longest = {"W": (0, None), "L": (0, None)}
    run_type, run_len = "", 0
    for i, r in enumerate(results):
        if r == run_type and r in ("W", "L"):
            run_len += 1
        else:
            run_type, run_len = r, 1 if r in ("W", "L") else 0
        if r in ("W", "L") and run_len > longest[r][0]:
            longest[r] = (run_len, i)
    if results:
        cur_type, cur_len = run_type, run_len
    return {"current": f"{cur_type}{cur_len}" if cur_len else "-", "current_type": cur_type, "current_len": cur_len,
            "longest_win": longest["W"][0], "longest_win_end_idx": longest["W"][1],
            "longest_loss": longest["L"][0], "longest_loss_end_idx": longest["L"][1]}


def standings(games: list[dict], team_ids: list[int], regular_season_weeks: int | None = None) -> list[dict]:
    """W-L-T, PF, PA, streak, all-play expected wins and luck. Regular season games only."""
    per = {t: [] for t in team_ids}
    for g in games:
        if regular_season_weeks and g["week"] > regular_season_weeks:
            continue
        per[g["team_id"]].append(g)
    # all-play: for each week, count league teams each team outscored
    by_week: dict[int, list[dict]] = defaultdict(list)
    for t, gs in per.items():
        for g in gs:
            by_week[g["week"]].append(g)
    all_play = {t: {"w": 0.0, "l": 0.0, "n": 0} for t in team_ids}
    for wk, gs in by_week.items():
        for g in gs:
            others = [o for o in gs if o["team_id"] != g["team_id"]]
            w = sum(1 for o in others if g["points"] > o["points"]) + 0.5 * sum(1 for o in others if g["points"] == o["points"])
            all_play[g["team_id"]]["w"] += w
            all_play[g["team_id"]]["l"] += len(others) - w
            all_play[g["team_id"]]["n"] += 1
    rows = []
    for t in team_ids:
        gs = sorted(per[t], key=lambda g: g["week"])
        wins = sum(g["result"] == "W" for g in gs)
        losses = sum(g["result"] == "L" for g in gs)
        ties = sum(g["result"] == "T" for g in gs)
        pf = round(sum(g["points"] for g in gs), 2)
        pa = round(sum(g["opp_points"] for g in gs), 2)
        pts = [g["points"] for g in gs]
        ap = all_play[t]
        n_opp = (len(team_ids) - 1) or 1
        exp_wins = round(ap["w"] / n_opp, 2)
        st = streaks([g["result"] for g in gs])
        rows.append({
            "team_id": t, "wins": wins, "losses": losses, "ties": ties, "games": len(gs),
            "points_for": pf, "points_against": pa,
            "ppg": round(pf / len(gs), 2) if gs else 0.0,
            "high": max(pts) if pts else 0.0, "low": min(pts) if pts else 0.0,
            "streak": st["current"], "streak_type": st["current_type"], "streak_len": st["current_len"],
            "longest_win_streak": st["longest_win"], "longest_loss_streak": st["longest_loss"],
            "all_play_wins": ap["w"], "all_play_losses": ap["l"],
            "all_play_pct": round(ap["w"] / (ap["w"] + ap["l"]), 3) if (ap["w"] + ap["l"]) else 0.0,
            "expected_wins": exp_wins, "luck": round(wins + 0.5 * ties - exp_wins, 2),
            "last3_ppg": round(sum(pts[-3:]) / len(pts[-3:]), 2) if pts else 0.0,
            "results": [g["result"] for g in gs],
        })
    rows.sort(key=lambda r: (-(r["wins"] + 0.5 * r["ties"]), -r["points_for"]))
    leader = rows[0] if rows else None
    for i, r in enumerate(rows, 1):
        r["rank"] = i
        r["games_back"] = round(((leader["wins"] - r["wins"]) + (r["losses"] - leader["losses"])) / 2, 1) if leader else 0.0
    return rows


def playoff_picture(rows: list[dict], playoff_teams: int, regular_season_weeks: int, weeks_complete: int) -> None:
    """Annotate standings rows in place with playoff status: clinched / in / bubble / out / eliminated."""
    remaining = max(regular_season_weeks - weeks_complete, 0)
    if not rows or playoff_teams <= 0:
        return
    cut_in = rows[playoff_teams - 1]["wins"] if len(rows) >= playoff_teams else 0
    cut_out = rows[playoff_teams]["wins"] if len(rows) > playoff_teams else 0
    for r in rows:
        max_possible = r["wins"] + remaining
        if r["rank"] <= playoff_teams and r["wins"] > cut_out + remaining:
            r["playoff"] = "clinched"
        elif max_possible < cut_in:
            r["playoff"] = "eliminated"
        elif r["rank"] <= playoff_teams:
            r["playoff"] = "in"
        elif max_possible >= cut_in and (cut_in - r["wins"]) <= max(remaining // 2, 1):
            r["playoff"] = "bubble"
        else:
            r["playoff"] = "out"


def weekly_highs(games: list[dict]) -> dict[int, dict]:
    """week -> {high: game, low: game}. Ties broken by first seen (stable)."""
    out = {}
    by_week: dict[int, list[dict]] = defaultdict(list)
    for g in games:
        by_week[g["week"]].append(g)
    for wk, gs in by_week.items():
        out[wk] = {"high": max(gs, key=lambda g: g["points"]), "low": min(gs, key=lambda g: g["points"])}
    return out


def top_n(items: list[dict], key: str, n: int = 5, reverse: bool = True) -> list[dict]:
    return sorted(items, key=lambda x: x[key], reverse=reverse)[:n]


def record_book(games: list[dict], extras: dict[tuple[int, int], dict] | None = None, n: int = 5) -> dict:
    """Record-book lists for one pool of games (a league, or all leagues merged).

    extras: (league_code, team_id, week) -> {bench_points, optimal_points, left_on_table, top_player}
    Each game row may carry a 'league_code' and 'label' for display; they are passed through.
    """
    extras = extras or {}
    wins = [g for g in games if g["result"] == "W"]
    losses = [g for g in games if g["result"] == "L"]
    margins = []
    seen = set()
    for g in wins:
        k = (g["week"], g.get("league_code"), min(g["team_id"], g["opp_id"]))
        if k in seen:
            continue
        seen.add(k)
        margins.append({**g, "margin": round(g["points"] - g["opp_points"], 2)})
    enriched = []
    for g in games:
        e = extras.get((g.get("league_code"), g["team_id"], g["week"]), {})
        enriched.append({**g, **{k: e.get(k) for k in ("bench_points", "optimal_points", "left_on_table")},
                         "top_player": e.get("top_player")})
    with_bench = [g for g in enriched if g.get("bench_points") is not None]
    return {
        "highest_score": top_n(games, "points", n),
        "lowest_score": top_n(games, "points", n, reverse=False),
        "biggest_blowout": top_n(margins, "margin", n),
        "closest_game": top_n(margins, "margin", n, reverse=False),
        "most_points_in_loss": top_n(losses, "points", n),
        "fewest_points_in_win": top_n(wins, "points", n, reverse=False),
        "most_bench_points": top_n(with_bench, "bench_points", n),
        "most_left_on_table": top_n(with_bench, "left_on_table", n),
        "best_player_week": best_player_weeks(enriched, n),
    }


def best_player_weeks(enriched: list[dict], n: int) -> list[dict]:
    rows = []
    for g in enriched:
        tp = g.get("top_player")
        if tp:
            rows.append({**g, "player": tp["name"], "position": tp["position"], "player_points": tp["points"],
                         "player_started": tp.get("started", True)})
    return top_n(rows, "player_points", n)


def power_rank(rows: list[dict]) -> list[dict]:
    """Cross-league ranking. rows: standings rows with league_code attached (all leagues merged).
    score = 0.6·norm(ppg) + 0.25·all-play % + 0.15·norm(last-3 ppg)."""
    if not rows:
        return []

    def norm(key):
        vals = [r[key] for r in rows]
        lo, hi = min(vals), max(vals)
        return {id(r): ((r[key] - lo) / (hi - lo) if hi > lo else 0.5) for r in rows}

    n_ppg, n_l3 = norm("ppg"), norm("last3_ppg")
    out = []
    for r in rows:
        score = 0.6 * n_ppg[id(r)] + 0.25 * r["all_play_pct"] + 0.15 * n_l3[id(r)]
        out.append({**r, "power_score": round(100 * score, 1)})
    out.sort(key=lambda r: (-r["power_score"], -r["ppg"]))
    for i, r in enumerate(out, 1):
        r["power_rank"] = i
    return out
