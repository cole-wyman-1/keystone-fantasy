"""Phase 2 probe: confirm the cookies work and show what ESPN knows about each league.

Usage:  .venv/bin/python scripts/espn_probe.py [--code EMP]

For each league in leagues.json it fetches mTeam + mSettings and prints the ESPN league
name, current week, scoring format, and the teams (id, name, owner display names).
Exits non-zero if any league fails, so the failure is impossible to miss.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from espn_client import AuthError, ESPNError, client_from_env  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def team_display_name(team: dict) -> str:
    name = (team.get("name") or "").strip()
    if not name:
        name = f"{team.get('location', '')} {team.get('nickname', '')}".strip()
    return name or f"Team {team.get('id')}"


def scoring_format(settings: dict) -> str:
    items = settings.get("scoringSettings", {}).get("scoringItems", [])
    rec = next((i.get("points", 0) for i in items if i.get("statId") == 53), 0)
    label = {0: "Standard (0 PPR)", 0.5: "Half PPR", 1: "Full PPR"}.get(rec, f"{rec} per reception")
    pass_td = next((i.get("points") for i in items if i.get("statId") == 4), None)
    return f"{label}, {pass_td if pass_td is not None else '?'} pt pass TD"


def probe_league(client, league: dict) -> dict:
    data = client.league(league["espn_league_id"], ["mTeam", "mSettings"], cache_name="probe_mTeam_mSettings")
    settings = data.get("settings", {})
    status = data.get("status", {})
    members = {m["id"]: m for m in data.get("members", [])}
    teams = []
    for t in sorted(data.get("teams", []), key=lambda t: t["id"]):
        owners = []
        for swid in t.get("owners", []):
            m = members.get(swid, {})
            full = f"{m.get('firstName', '')} {m.get('lastName', '')}".strip()
            owners.append(m.get("displayName", swid) + (f" ({full})" if full else ""))
        teams.append({"id": t["id"], "abbrev": t.get("abbrev", ""), "name": team_display_name(t),
                      "owners": owners})
    sched = settings.get("scheduleSettings", {})
    return {
        "code": league["code"],
        "espn_league_id": league["espn_league_id"],
        "espn_name": settings.get("name"),
        "size": settings.get("size"),
        "current_matchup_period": status.get("currentMatchupPeriod"),
        "scoring_period": data.get("scoringPeriodId"),
        "latest_scoring_period": status.get("latestScoringPeriod"),
        "final_scoring_period": status.get("finalScoringPeriod"),
        "regular_season_weeks": sched.get("matchupPeriodCount"),
        "playoff_teams": sched.get("playoffTeamCount"),
        "divisions": [d.get("name") for d in sched.get("divisions", [])],
        "scoring": scoring_format(settings),
        "teams": teams,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--code", help="only probe this league code")
    args = ap.parse_args()

    cfg = json.loads((ROOT / "leagues.json").read_text())
    leagues = [l for l in cfg["leagues"] if not args.code or l["code"] == args.code.upper()]
    try:
        client = client_from_env(cfg["season"])
    except AuthError as exc:
        print(f"CONFIG ERROR: {exc}")
        return 2

    results, failures = [], []
    for league in leagues:
        print(f"\n=== {league['code']}  {league['name']}  (ESPN id {league['espn_league_id']}) ===")
        try:
            r = probe_league(client, league)
        except (AuthError, ESPNError) as exc:
            print(f"  FAILED: {exc}")
            failures.append(league["code"])
            continue
        results.append(r)
        print(f"  ESPN name: {r['espn_name']}   size: {r['size']}   scoring: {r['scoring']}")
        print(f"  current matchup period: {r['current_matchup_period']}   scoring period: {r['scoring_period']}"
              f"   latest: {r['latest_scoring_period']}   final: {r['final_scoring_period']}")
        print(f"  regular season weeks: {r['regular_season_weeks']}   playoff teams: {r['playoff_teams']}"
              f"   divisions: {r['divisions'] or 'none'}")
        for t in r["teams"]:
            print(f"    team {t['id']:>2}  {t['abbrev']:<5} {t['name']:<32} owner: {', '.join(t['owners']) or '(none)'}")
        if r["size"] != 12 or len(r["teams"]) != 12:
            print(f"  WARNING: expected 12 teams, ESPN reports size={r['size']} teams={len(r['teams'])}")

    out = ROOT / "data" / "espn" / "probe.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2))
    print(f"\nWrote {out.relative_to(ROOT)}")
    if failures:
        print(f"FAILED leagues: {failures}")
        return 1
    print("All leagues OK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
