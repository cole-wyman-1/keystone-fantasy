"""Master CSV -> data/master.json. Validates the roster and the ESPN join keys.

The CSV is the source of truth; this is a pure read except for the JSON it writes.
Emails ARE included here (data/master.json is for matching only) and are stripped by compute.py
before anything reaches data/site/.
"""
from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MASTER_CSV = ROOT / "Starter Files" / "keystone_ff_2026_master.csv"
LEAGUES = ROOT / "leagues.json"
OUT = ROOT / "data" / "master.json"

COLS = {
    "Slot ID": "slot_id", "League Code": "league_code", "Slot #": "slot", "Display Name": "display_name",
    "First Name": "first_name", "Last Name": "last_name", "Seat Type": "seat_type", "Manager Seat": "manager_seat",
    "Email (Communications)": "email_comm", "Email (ESPN Login)": "email_espn", "Keystone Group": "keystone_group",
    "Favorite NFL Team": "favorite_team", "Home City": "home_city", "College": "college",
    "Current Company": "company", "ESPN League ID": "espn_league_id", "ESPN Team ID": "espn_team_id",
    "ESPN Team Name": "espn_team_name", "Notes": "notes",
}


def load() -> dict:
    cfg = json.loads(LEAGUES.read_text())
    codes = {l["code"]: l for l in cfg["leagues"]}
    rows = list(csv.DictReader(MASTER_CSV.open(newline="")))
    slots, problems = [], []
    for r in rows:
        s = {v: (r.get(k) or "").strip() for k, v in COLS.items()}
        s["slot"] = int(s["slot"]) if s["slot"] else None
        s["is_commissioner"] = s["seat_type"] == "League Manager"
        s["manager_seat"] = s["manager_seat"].lower() == "yes"
        s["espn_team_id"] = int(s["espn_team_id"]) if s["espn_team_id"] else None
        s["espn_league_id"] = int(s["espn_league_id"]) if s["espn_league_id"] else None
        if s["league_code"] not in codes:
            problems.append(f"{s['slot_id']}: unknown league code {s['league_code']}")
        elif s["espn_league_id"] and s["espn_league_id"] != codes[s["league_code"]]["espn_league_id"]:
            problems.append(f"{s['slot_id']}: ESPN League ID {s['espn_league_id']} != leagues.json")
        if s["espn_team_id"] is None:
            problems.append(f"{s['slot_id']}: no ESPN Team ID (run map_teams.py)")
        if not s["display_name"]:
            problems.append(f"{s['slot_id']}: blank Display Name")
        s["league_name"] = codes.get(s["league_code"], {}).get("name", "")
        slots.append(s)
    dup_slots = [k for k, c in Counter(s["slot_id"] for s in slots).items() if c > 1]
    dup_teams = [k for k, c in Counter((s["league_code"], s["espn_team_id"]) for s in slots if s["espn_team_id"]).items() if c > 1]
    if dup_slots:
        problems.append(f"duplicate Slot IDs: {dup_slots}")
    if dup_teams:
        problems.append(f"same ESPN team on two slots: {dup_teams}")
    per_league = Counter(s["league_code"] for s in slots)
    return {"season": cfg["season"], "leagues": cfg["leagues"], "slots": slots,
            "per_league": dict(per_league), "problems": problems}


def main() -> int:
    m = load()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({k: m[k] for k in ("season", "leagues", "slots")}, indent=1, ensure_ascii=False))
    print(f"Imported {len(m['slots'])} slots across {len(m['per_league'])} leagues -> {OUT.relative_to(ROOT)}")
    if m["problems"]:
        print("PROBLEMS:\n  " + "\n  ".join(m["problems"]))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
