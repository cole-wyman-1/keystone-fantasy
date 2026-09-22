"""Pull every league for every week from ESPN and write normalized JSON under data/espn/.

  data/espn/<CODE>/league.json      settings, status, teams, full schedule totals
  data/espn/<CODE>/weeks/<N>.json   matchups + per-team lineups for scoring period N

Idempotent: a week that is already stored as complete is not re-fetched unless --force.
The current (in-progress) week is always re-fetched and stored with complete=false so the
site can show live-ish scores without those numbers entering the record book.
Fails loudly (non-zero exit) on any auth or league error.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from espn_client import AuthError, ESPNError, client_from_env  # noqa: E402
from lib.espn_ids import NON_STARTING_SLOTS, position_name, slot_name  # noqa: E402
from lib.trades import PRO_TEAMS, normalize_trades  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "espn"


def team_name(t: dict) -> str:
    return (t.get("name") or f"{t.get('location', '')} {t.get('nickname', '')}").strip() or f"Team {t['id']}"


def norm_league(data: dict, league: dict) -> dict:
    s, st = data["settings"], data["status"]
    members = {m["id"]: m for m in data.get("members", [])}
    teams = []
    for t in sorted(data["teams"], key=lambda t: t["id"]):
        rec = t.get("record", {}).get("overall", {})
        teams.append({
            "espn_team_id": t["id"], "name": team_name(t), "abbrev": t.get("abbrev", ""),
            "logo": t.get("logo") or "", "division_id": t.get("divisionId"),
            "owners": [{"display": members.get(o, {}).get("displayName", ""),
                        "first": members.get(o, {}).get("firstName", ""),
                        "last": members.get(o, {}).get("lastName", "")} for o in t.get("owners", [])],
            "espn_record": {"wins": rec.get("wins", 0), "losses": rec.get("losses", 0), "ties": rec.get("ties", 0),
                             "points_for": rec.get("pointsFor", 0.0), "points_against": rec.get("pointsAgainst", 0.0)},
            "espn_playoff_seed": t.get("playoffSeed"),
        })
    ss = s.get("scheduleSettings", {})
    items = s.get("scoringSettings", {}).get("scoringItems", [])
    rec_pts = next((i.get("points", 0) for i in items if i.get("statId") == 53), 0)
    return {
        "code": league["code"], "name": league["name"], "espn_league_id": data["id"], "season": data["seasonId"],
        "espn_name": s.get("name"), "size": s.get("size"),
        "regular_season_weeks": ss.get("matchupPeriodCount"), "playoff_teams": ss.get("playoffTeamCount"),
        "matchup_periods": {int(k): v for k, v in ss.get("matchupPeriods", {}).items()},
        "lineup_slot_counts": {int(k): v for k, v in s.get("rosterSettings", {}).get("lineupSlotCounts", {}).items() if v},
        "scoring_format": {0: "Standard", 0.5: "Half PPR", 1: "Full PPR"}.get(rec_pts, f"{rec_pts} PPR"),
        "status": {"current_matchup_period": st.get("currentMatchupPeriod"),
                   "latest_scoring_period": st.get("latestScoringPeriod"),
                   "final_scoring_period": st.get("finalScoringPeriod"), "is_active": st.get("isActive")},
        "teams": teams,
        "schedule": [norm_matchup(m) for m in sorted(data.get("schedule", []), key=lambda m: (m["matchupPeriodId"], m["id"]))],
    }


def side_points(side: dict, decided: bool) -> float:
    """Final totals live in totalPoints; while a matchup is in progress ESPN leaves that at 0
    and reports totalPointsLive / pointsByScoringPeriod instead."""
    if decided or side.get("totalPoints"):
        return round(side.get("totalPoints", 0.0), 2)
    live = side.get("totalPointsLive")
    if live is None:
        live = sum(side.get("pointsByScoringPeriod", {}).values())
    return round(live or 0.0, 2)


def norm_matchup(m: dict) -> dict:
    home, away = m.get("home", {}), m.get("away")  # away is absent on a bye
    decided = m.get("winner", "UNDECIDED") != "UNDECIDED"
    return {
        "matchup_id": m["id"], "matchup_period": m["matchupPeriodId"],
        "home_team_id": home.get("teamId"), "away_team_id": away.get("teamId") if away else None,
        "home_points": side_points(home, decided),
        "away_points": side_points(away, decided) if away else None,
        "winner": m.get("winner", "UNDECIDED"), "playoff_tier": m.get("playoffTierType", "NONE"),
        "is_bye": away is None,
    }


def norm_lineup(entries: list[dict]) -> list[dict]:
    out = []
    for e in entries:
        p = e["playerPoolEntry"]["player"]
        out.append({
            "player_id": e["playerId"], "name": p.get("fullName", ""),
            "position": position_name(p.get("defaultPositionId")),
            "lineup_slot_id": e["lineupSlotId"], "lineup_slot": slot_name(e["lineupSlotId"]),
            "started": e["lineupSlotId"] not in NON_STARTING_SLOTS,
            "eligible_slots": p.get("eligibleSlots", []),
            "points": round(e["playerPoolEntry"].get("appliedStatTotal", 0.0), 2),
        })
    return out


def week_from_scoring_period(data: dict, scoring_period: int, matchup_period: int) -> dict:
    matchups, lineups = [], {}
    for m in data.get("schedule", []):
        if m["matchupPeriodId"] != matchup_period:
            continue
        nm = norm_matchup(m)
        matchups.append(nm)
        for side in ("home", "away"):
            s = m.get(side)
            if not s:
                continue
            roster = s.get("rosterForCurrentScoringPeriod", {}).get("entries", [])
            lu = norm_lineup(roster)
            lineups[str(s["teamId"])] = {
                "points": round(s.get("pointsByScoringPeriod", {}).get(str(scoring_period), s.get("totalPoints", 0.0)), 2),
                "players": lu,
            }
    complete = bool(matchups) and all(m["winner"] != "UNDECIDED" for m in matchups)
    return {"scoring_period": scoring_period, "matchup_period": matchup_period, "complete": complete,
            "fetched_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "matchups": matchups, "lineups": lineups}


PLAYERS_CACHE = OUT / "players.json"


def fetch_trades(client, league: dict, latest: int) -> list[dict]:
    """All trade proposals in every scoring period so far (cheap; statuses can change, so always refetch)."""
    txs = []
    for sp in range(1, latest + 1):
        data = client.league(league["espn_league_id"], ["mTransactions2"], scoring_period=sp, cache_name=f"transactions_sp{sp}")
        txs.extend(data.get("transactions", []))
    return normalize_trades(txs)


def resolve_players(client, league_id: int, player_ids: set[int]) -> dict:
    """Look up names/positions for player ids not already in data/espn/players.json."""
    cache = json.loads(PLAYERS_CACHE.read_text()) if PLAYERS_CACHE.exists() else {}
    missing = sorted(pid for pid in player_ids if str(pid) not in cache)
    for i in range(0, len(missing), 50):
        batch = missing[i:i + 50]
        data = client.league_filtered(league_id, "kona_player_info", {"players": {"filterIds": {"value": batch}}})
        for p in data.get("players", []):
            pl = p.get("player", {})
            cache[str(pl.get("id", p.get("id")))] = {"name": pl.get("fullName", ""), "position": position_name(pl.get("defaultPositionId")),
                                                    "pro_team": PRO_TEAMS.get(pl.get("proTeamId"), "")}
        for pid in batch:  # avoid re-querying ids ESPN doesn't know
            cache.setdefault(str(pid), {"name": f"Player {pid}", "position": "", "pro_team": ""})
    PLAYERS_CACHE.write_text(json.dumps(cache, indent=0, ensure_ascii=False))
    return cache


def fetch_league(client, league: dict, force: bool, max_period: int | None) -> dict:
    code = league["code"]
    ldir = OUT / code
    (ldir / "weeks").mkdir(parents=True, exist_ok=True)
    data = client.league(league["espn_league_id"], ["mTeam", "mSettings", "mMatchupScore"], cache_name="league")
    lg = norm_league(data, league)
    (ldir / "league.json").write_text(json.dumps(lg, indent=1, ensure_ascii=False))
    latest = lg["status"]["latest_scoring_period"] or 1
    final = lg["status"]["final_scoring_period"] or 17
    period_of = {sp: mp for mp, sps in lg["matchup_periods"].items() for sp in sps} or {i: i for i in range(1, final + 1)}
    summary = {"code": code, "weeks_fetched": [], "weeks_skipped": [], "weeks_complete": [], "trades": 0}
    trades = fetch_trades(client, league, latest)
    resolve_players(client, league["espn_league_id"], {m["player_id"] for t in trades for m in t["moves"]})
    (ldir / "trades.json").write_text(json.dumps(trades, indent=1))
    summary["trades"] = sum(1 for t in trades if t["status"] == "EXECUTED")
    for sp in range(1, min(latest, max_period or latest) + 1):
        path = ldir / "weeks" / f"{sp}.json"
        if path.exists() and not force:
            existing = json.loads(path.read_text())
            if existing.get("complete"):
                summary["weeks_skipped"].append(sp)
                summary["weeks_complete"].append(sp)
                continue
        wdata = client.league(league["espn_league_id"], ["mMatchupScore", "mBoxscore", "mRoster"],
                              scoring_period=sp, cache_name=f"week_{sp}")
        week = week_from_scoring_period(wdata, sp, period_of.get(sp, sp))
        path.write_text(json.dumps(week, indent=1, ensure_ascii=False))
        summary["weeks_fetched"].append(sp)
        if week["complete"]:
            summary["weeks_complete"].append(sp)
    return summary


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--code", help="only this league")
    ap.add_argument("--force", action="store_true", help="re-fetch weeks already stored as complete")
    ap.add_argument("--max-period", type=int, help="stop at this scoring period (debug)")
    args = ap.parse_args()
    cfg = json.loads((ROOT / "leagues.json").read_text())
    leagues = [l for l in cfg["leagues"] if not args.code or l["code"] == args.code.upper()]
    try:
        client = client_from_env(cfg["season"])
    except AuthError as exc:
        print(f"CONFIG ERROR: {exc}")
        return 2
    failures, summaries = [], []
    for league in leagues:
        try:
            s = fetch_league(client, league, args.force, args.max_period)
        except (AuthError, ESPNError) as exc:
            print(f"{league['code']}: FAILED: {exc}")
            failures.append(league["code"])
            continue
        summaries.append(s)
        print(f"{s['code']}: fetched weeks {s['weeks_fetched'] or '-'}, skipped (already complete) {s['weeks_skipped'] or '-'}, "
              f"complete through week {max(s['weeks_complete']) if s['weeks_complete'] else 0}, completed trades {s['trades']}")
    meta_path = OUT / "fetch_meta.json"
    meta = {"season": cfg["season"], "fetched_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "leagues": summaries, "failures": failures}
    meta_path.write_text(json.dumps(meta, indent=1))
    if failures:
        print(f"FAILED leagues: {failures} — not all data refreshed; aborting so nothing stale is published.")
        return 1
    print("Fetch OK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
