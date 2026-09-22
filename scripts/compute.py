"""Derive everything the site needs from data/master.json + data/espn/ and write data/site/.

Outputs (all JSON, no emails anywhere):
  meta.json, leagues.json, people.json, standings.json, weekly.json, highs.json,
  records.json, power.json
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.icons import profile_icons  # noqa: E402
from lib.lineup import optimal_lineup  # noqa: E402
from lib.records import (games_from_weeks, playoff_picture, power_rank, record_book, standings,  # noqa: E402
                         weekly_highs)

ROOT = Path(__file__).resolve().parent.parent
MASTER = ROOT / "data" / "master.json"
ESPN = ROOT / "data" / "espn"
SITE = ROOT / "data" / "site"
PROFILE_FIELDS = ["keystone_group", "favorite_team", "home_city", "college", "company"]
RECORD_N_OVERALL, RECORD_N_LEAGUE = 10, 5
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


def load_league(code: str) -> tuple[dict, list[dict]]:
    ldir = ESPN / code
    league = json.loads((ldir / "league.json").read_text())
    weeks = []
    for p in sorted((ldir / "weeks").glob("*.json"), key=lambda p: int(p.stem)):
        weeks.append(json.loads(p.read_text()))
    return league, weeks


def lineup_extras(week: dict, slot_counts: dict) -> dict[int, dict]:
    """team_id -> bench/optimal/top player for one week."""
    out = {}
    for tid, lu in week["lineups"].items():
        players = lu["players"]
        starters = [p for p in players if p["started"]]
        bench = [p for p in players if not p["started"] and p["lineup_slot_id"] != 21]
        actual = round(sum(p["points"] for p in starters), 2)
        optimal, _ = optimal_lineup(players, slot_counts)
        top = max(players, key=lambda p: p["points"]) if players else None
        out[int(tid)] = {
            "bench_points": round(sum(p["points"] for p in bench), 2),
            "optimal_points": optimal,
            "left_on_table": round(max(optimal - actual, 0.0), 2),
            "top_player": {"name": top["name"], "position": top["position"], "points": top["points"],
                           "started": top["started"]} if top else None,
        }
    return out


def public_person(slot: dict) -> dict:
    """Strip emails and blanks; what the site is allowed to know about a person."""
    profile = {k: slot[k] for k in PROFILE_FIELDS if slot.get(k)}
    return {
        "slot_id": slot["slot_id"], "slug": slot["slot_id"].lower(), "display_name": slot["display_name"],
        "first_name": slot["first_name"], "last_name": slot["last_name"],
        "league_code": slot["league_code"], "league_name": slot["league_name"],
        "is_commissioner": slot["is_commissioner"], "manager_seat": slot["manager_seat"],
        "profile": profile,
        "icons": profile_icons(profile),
        # compact "🗽 🦡 🏈" string for table subtext: city, college, favorite team
        "icon_row": " ".join(i for i in (profile_icons(profile).get(k, "") for k in ("home_city", "college", "favorite_team")) if i),
    }


def main() -> int:
    master = json.loads(MASTER.read_text())
    season = master["season"]
    slots_by_key = {(s["league_code"], s["espn_team_id"]): s for s in master["slots"]}
    SITE.mkdir(parents=True, exist_ok=True)

    leagues_out, standings_out, weekly_out = [], {}, {}
    people = {s["slot_id"]: {**public_person(s), "team": None, "weeks": [], "in_progress": None} for s in master["slots"]}
    all_games, all_extras, all_rows = [], {}, []
    league_records = {}
    weeks_complete_by_league = {}
    highs_by_week: dict[int, dict] = defaultdict(dict)
    high_counts: Counter = Counter()
    fetch_meta = json.loads((ESPN / "fetch_meta.json").read_text()) if (ESPN / "fetch_meta.json").exists() else {}

    for lg in master["leagues"]:
        code = lg["code"]
        league, weeks = load_league(code)
        team_ids = [t["espn_team_id"] for t in league["teams"]]
        label = {}  # team_id -> (slot_id, owner display, team name)
        for t in league["teams"]:
            s = slots_by_key.get((code, t["espn_team_id"]))
            owner = s["display_name"] if s else ", ".join(o["display"] for o in t["owners"]) or "Unknown"
            label[t["espn_team_id"]] = {"slot_id": s["slot_id"] if s else None, "owner": owner, "team_name": t["name"],
                                        "abbrev": t["abbrev"], "logo": t.get("logo", "")}
            if s:
                people[s["slot_id"]]["team"] = {"team_id": t["espn_team_id"], "name": t["name"], "abbrev": t["abbrev"],
                                                "logo": t.get("logo", "")}

        def tag(g: dict) -> dict:
            l = label[g["team_id"]]
            o = label[g["opp_id"]]
            return {**g, "league_code": code, "league_name": lg["name"], "slot_id": l["slot_id"], "owner": l["owner"],
                    "team_name": l["team_name"], "opp_slot_id": o["slot_id"], "opp_owner": o["owner"], "opp_team_name": o["team_name"]}

        games = [tag(g) for g in games_from_weeks(weeks)]
        complete_weeks = [w for w in weeks if w["complete"]]
        n_complete = max((w["matchup_period"] for w in complete_weeks), default=0)
        weeks_complete_by_league[code] = n_complete
        extras = {}
        for w in weeks:
            for tid, e in lineup_extras(w, league["lineup_slot_counts"]).items():
                extras[(code, tid, w["matchup_period"])] = e
        all_extras.update(extras)
        all_games.extend(games)

        rows = standings(games, team_ids, league["regular_season_weeks"])
        playoff_picture(rows, league["playoff_teams"] or 0, league["regular_season_weeks"] or 14, n_complete)
        for r in rows:
            r.update({"league_code": code, "league_name": lg["name"], **label[r["team_id"]]})
        all_rows.extend(rows)
        standings_out[code] = rows

        highs = weekly_highs(games)
        for wk, h in highs.items():
            highs_by_week[wk][code] = {k: h["high"][k] for k in ("slot_id", "owner", "team_name", "points", "team_id")}
            high_counts[h["high"]["slot_id"]] += 1

        # weekly matchups (complete + in-progress) for league pages and person pages
        weekly_out[code] = {}
        for w in weeks:
            wk = w["matchup_period"]
            ms = []
            for m in w["matchups"]:
                if m["away_team_id"] is None:
                    continue
                h, a = label[m["home_team_id"]], label[m["away_team_id"]]
                eh, ea = extras.get((code, m["home_team_id"], wk), {}), extras.get((code, m["away_team_id"], wk), {})
                ms.append({"home": {"team_id": m["home_team_id"], **h, "points": m["home_points"], **{k: eh.get(k) for k in ("bench_points", "optimal_points")}},
                           "away": {"team_id": m["away_team_id"], **a, "points": m["away_points"], **{k: ea.get(k) for k in ("bench_points", "optimal_points")}},
                           "winner": m["winner"], "margin": round(abs(m["home_points"] - m["away_points"]), 2),
                           "playoff_tier": m["playoff_tier"]})
            entry = {"week": wk, "complete": w["complete"], "matchups": ms}
            if w["complete"] and wk in highs:
                entry["high"] = highs_by_week[wk][code]
                entry["low"] = {k: highs[wk]["low"][k] for k in ("slot_id", "owner", "team_name", "points")}
            weekly_out[code][str(wk)] = entry
            # person series
            for m in ms:
                for side, opp in (("home", "away"), ("away", "home")):
                    sid = m[side]["slot_id"]
                    if not sid:
                        continue
                    rec = {"week": wk, "points": m[side]["points"], "opp_slot_id": m[opp]["slot_id"], "opp_owner": m[opp]["owner"],
                           "opp_team_name": m[opp]["team_name"], "opp_points": m[opp]["points"],
                           "bench_points": m[side]["bench_points"], "optimal_points": m[side]["optimal_points"]}
                    if w["complete"]:
                        rec["result"] = "T" if m["home"]["points"] == m["away"]["points"] else ("W" if m[side]["points"] > m[opp]["points"] else "L")
                        rec["league_high"] = highs_by_week[wk][code]["slot_id"] == sid
                        wk_pts = sorted((x["points"] for mm in ms for x in (mm["home"], mm["away"])), reverse=True)
                        rec["rank_in_league"] = wk_pts.index(m[side]["points"]) + 1
                        people[sid]["weeks"].append(rec)
                    else:
                        people[sid]["in_progress"] = rec

        league_records[code] = record_book(games, extras, RECORD_N_LEAGUE)
        leagues_out.append({
            "code": code, "name": lg["name"], "slug": code.lower(), "espn_name": league["espn_name"],
            "espn_league_id": league["espn_league_id"], "managed_by": lg["managed_by"],
            "regular_season_weeks": league["regular_season_weeks"], "playoff_teams": league["playoff_teams"],
            "scoring_format": league["scoring_format"], "weeks_complete": n_complete,
            "current_week": league["status"]["current_matchup_period"],
            "teams": [{"team_id": t["espn_team_id"], **label[t["espn_team_id"]]} for t in league["teams"]],
        })

    # overall highs per week
    highs_out = {"weeks": [], "leaderboard": []}
    for wk in sorted(highs_by_week):
        per = highs_by_week[wk]
        best_code = max(per, key=lambda c: per[c]["points"])
        highs_out["weeks"].append({"week": wk, "per_league": per, "overall": {"league_code": best_code, **per[best_code]}})
    highs_out["leaderboard"] = [{"slot_id": sid, "owner": people[sid]["display_name"], "league_code": people[sid]["league_code"],
                                 "team_name": people[sid]["team"]["name"] if people[sid]["team"] else "", "count": c}
                                for sid, c in high_counts.most_common()]

    # power ranking across all leagues
    power = power_rank(all_rows)
    for r in power:
        if r["slot_id"]:
            people[r["slot_id"]]["power_rank"] = r["power_rank"]
    keep = ("power_rank", "power_score", "slot_id", "owner", "team_name", "league_code", "league_name", "wins", "losses", "ties",
            "ppg", "points_for", "all_play_pct", "last3_ppg", "luck", "high", "rank")
    power_out = [{k: r[k] for k in keep} for r in power]

    # per-person summary
    for r in all_rows:
        sid = r["slot_id"]
        if not sid:
            continue
        p = people[sid]
        p["record"] = {k: r[k] for k in ("wins", "losses", "ties", "points_for", "points_against", "ppg", "streak", "rank",
                                        "expected_wins", "luck", "all_play_wins", "all_play_losses", "playoff", "games_back",
                                        "longest_win_streak", "longest_loss_streak")}
        if p["weeks"]:
            p["best_week"] = max(p["weeks"], key=lambda w: w["points"])
            p["worst_week"] = min(p["weeks"], key=lambda w: w["points"])
            p["weekly_high_count"] = high_counts.get(sid, 0)
            p["bench_total"] = round(sum(w["bench_points"] or 0 for w in p["weeks"]), 2)
            p["left_on_table_total"] = round(sum(max((w["optimal_points"] or 0) - w["points"], 0) for w in p["weeks"]), 2)

    records_out = {"overall": record_book(all_games, all_extras, RECORD_N_OVERALL), "per_league": league_records,
                   "luck": {"luckiest": sorted([{k: r[k] for k in ("slot_id", "owner", "team_name", "league_code", "wins", "losses", "expected_wins", "luck")} for r in all_rows], key=lambda r: -r["luck"])[:RECORD_N_OVERALL],
                            "unluckiest": sorted([{k: r[k] for k in ("slot_id", "owner", "team_name", "league_code", "wins", "losses", "expected_wins", "luck")} for r in all_rows], key=lambda r: r["luck"])[:RECORD_N_OVERALL]},
                   "streaks": {"longest_win": sorted([{k: r[k] for k in ("slot_id", "owner", "team_name", "league_code", "longest_win_streak", "streak")} for r in all_rows], key=lambda r: -r["longest_win_streak"])[:RECORD_N_OVERALL],
                               "longest_loss": sorted([{k: r[k] for k in ("slot_id", "owner", "team_name", "league_code", "longest_loss_streak", "streak")} for r in all_rows], key=lambda r: -r["longest_loss_streak"])[:RECORD_N_OVERALL]}}

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    weeks_complete = min(weeks_complete_by_league.values()) if weeks_complete_by_league else 0
    meta = {"season": season, "generated_utc": now, "last_successful_fetch_utc": fetch_meta.get("fetched_utc", now),
            "weeks_complete": weeks_complete, "weeks_complete_by_league": weeks_complete_by_league,
            "current_week": max((l["current_week"] or 0) for l in leagues_out) if leagues_out else None,
            "n_people": sum(1 for p in people.values() if not p["is_commissioner"]), "n_leagues": len(leagues_out)}

    for name, obj in {"meta": meta, "leagues": leagues_out, "people": people, "standings": standings_out, "weekly": weekly_out,
                      "highs": highs_out, "records": records_out, "power": power_out}.items():
        text = json.dumps(obj, indent=0, ensure_ascii=False, separators=(",", ":"))
        assert not EMAIL_RE.search(text), f"{name}.json would contain an email address"
        (SITE / f"{name}.json").write_text(text)
    print(f"Wrote data/site/*.json: {len(leagues_out)} leagues, {len(people)} people, weeks complete = {weeks_complete}, "
          f"power #1 = {power_out[0]['owner']} ({power_out[0]['league_code']}) {power_out[0]['ppg']} ppg" if power_out else "no games yet")
    return 0


if __name__ == "__main__":
    sys.exit(main())
