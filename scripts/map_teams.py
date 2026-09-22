"""Phase 3: map master-file slots to ESPN teams.

  propose:  read data/espn/probe.json + master CSV, auto-match by owner name, write
            data/team_mapping.json and print a per-league table with confidence flags.
  apply:    read data/team_mapping.json (after you confirm/edit it) and write ESPN League ID,
            ESPN Team ID, ESPN Team Name and Manager Seat back into the master CSV + JSON.

The commissioner ESPN account is identified by COMMISSIONER_SWID. A team whose only owner is
the commissioner maps to the League Manager slot; a team co-owned with someone else maps to
that person and marks their row Manager Seat = Yes.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MASTER_CSV = ROOT / "Starter Files" / "keystone_ff_2026_master.csv"            # committed, no emails
PRIVATE_DIR = ROOT / "Starter Files" / "private"                                  # git-ignored
PRIVATE_CSV = PRIVATE_DIR / "keystone_ff_2026_master_with_emails.csv"            # used for matching if present
MASTER_JSON = PRIVATE_DIR / "keystone_ff_2026_master.json"
EMAIL_COLS = ("Email (Communications)", "Email (ESPN Login)")
PROBE = ROOT / "data" / "espn" / "probe.json"
MAPPING = ROOT / "data" / "team_mapping.json"

COMMISSIONER_SWID = "{1712906171}"  # placeholder; real match is by displayName below
COMMISSIONER_DISPLAY = "ESPNFAN1712906171"

NICKNAMES = {
    "matt": "matthew", "ben": "benjamin", "zach": "zachary", "rob": "robert", "bob": "robert",
    "mike": "michael", "doug": "douglas", "chris": "christopher", "sam": "samuel", "jake": "jacob",
    "dan": "daniel", "will": "william", "bill": "william", "jon": "jonathan", "jeff": "jeffrey",
    "alex": "alexander", "nick": "nicholas", "tom": "thomas", "gaby": "gabriela", "andy": "andrew",
    "karthick": "karthik", "hemmanuer": "hemmanur",
}


def norm(s: str) -> str:
    s = re.sub(r"[^a-z ]", "", (s or "").lower()).strip()
    return " ".join(NICKNAMES.get(w, w) for w in s.split())


def sim(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio() if a and b else 0.0


def score(slot: dict, owner: dict) -> tuple[float, str]:
    """Return (0..1 score, reason) for how well a slot matches an ESPN owner."""
    sf, sl = norm(slot["First Name"]), norm(slot["Last Name"])
    of, ol = norm(owner["first"]), norm(owner["last"])
    full_s, full_o = f"{sf} {sl}".strip(), f"{of} {ol}".strip()
    disp = norm(owner["display"])
    email_local = norm((slot.get("Email (ESPN Login)") or "").split("@")[0].replace(".", " "))

    if full_s and full_s == full_o:
        return 1.0, "exact name"
    best, why = sim(full_s, full_o), "fuzzy full name"
    slot_last_token = sl.split()[-1] if sl else ""
    if sl and ol and (sl == ol or slot_last_token == ol):  # surname match, first differs / extra surname
        best, why = max(best, 0.9), "surname"
    if sf and sf == of and not sl:  # slot has first name only
        best, why = max(best, 0.8), "first name only"
    if sf and sf == of and sl and sl != ol and slot_last_token != ol:  # maiden/married name?
        best, why = max(best, 0.7), "first name, surname differs"
    if disp and not disp.startswith("espnfan") and full_s:  # owner display name vs slot name
        d = max(sim(disp, full_s), sim(disp.replace(" ", ""), full_s.replace(" ", "")))
        if d > best:
            best, why = d, "display name"
    if email_local and full_o:  # slot's ESPN login email vs owner's real name
        e = email_local.replace(" ", "")
        if sim(e, full_o.replace(" ", "")) > 0.85 or (ol and ol in e and of and of[0] == e[:1]):
            best, why = max(best, 0.85), "email matches"
    return best, why


def parse_owner(o: str) -> dict:
    # "displayName (First Last)" as printed by the probe
    m = re.match(r"^(.*?)\s*\((.*)\)$", o)
    if m:
        disp, full = m.group(1), m.group(2)
    else:
        disp, full = o, ""
    parts = full.split()
    return {"display": disp, "first": parts[0] if parts else "", "last": " ".join(parts[1:]) if len(parts) > 1 else "",
            "raw": o}


def load_master() -> list[dict]:
    src = PRIVATE_CSV if PRIVATE_CSV.exists() else MASTER_CSV
    return list(csv.DictReader(src.open(newline="")))


def write_master(rows: list[dict]) -> None:
    """Write the private (with emails) CSV if it exists, and always the sanitized committed CSV."""
    fields = list(rows[0].keys())
    if PRIVATE_CSV.exists():
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
        w.writeheader(); w.writerows(rows)
        PRIVATE_CSV.write_text(buf.getvalue())
    pub = [f for f in fields if f not in EMAIL_COLS]
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=pub, lineterminator="\n", extrasaction="ignore")
    w.writeheader(); w.writerows(rows)
    MASTER_CSV.write_text(buf.getvalue())


def assign(slots: list[dict], teams: list[dict]) -> list[dict]:
    """Greedy best-first one-to-one assignment. Returns one row per ESPN team."""
    cands = []
    for t in teams:
        owners = [parse_owner(o) for o in t["owners"]]
        humans = [o for o in owners if o["display"] != COMMISSIONER_DISPLAY]
        commissioner_only = bool(owners) and not humans
        for s in slots:
            if commissioner_only:
                sc, why = (1.0, "commissioner-only team") if s["Seat Type"] == "League Manager" else (0.0, "")
            elif s["Seat Type"] == "League Manager":
                sc, why = 0.0, ""
            else:
                sc, why = max((score(s, o) for o in humans), key=lambda x: x[0], default=(0.0, ""))
            cands.append((sc, t["id"], s["Slot ID"], why, humans))
    cands.sort(key=lambda c: -c[0])
    used_t, used_s, out = set(), set(), {}
    for sc, tid, sid, why, humans in cands:
        if tid in used_t or sid in used_s or sc < 0.45:
            continue
        used_t.add(tid); used_s.add(sid)
        out[tid] = (sid, sc, why, humans)
    rows = []
    for t in teams:
        sid, sc, why, humans = out.get(t["id"], (None, 0.0, "NO MATCH", None))
        if humans is None:
            humans = [o for o in (parse_owner(o) for o in t["owners"]) if o["display"] != COMMISSIONER_DISPLAY]
        co_owned = any(parse_owner(o)["display"] == COMMISSIONER_DISPLAY for o in t["owners"]) and bool(humans)
        rows.append({"espn_team_id": t["id"], "espn_team_name": t["name"], "espn_abbrev": t["abbrev"],
                     "espn_owners": t["owners"], "slot_id": sid, "score": round(sc, 2), "reason": why,
                     "co_owned_with_commissioner": co_owned,
                     "confidence": "high" if sc >= 0.95 else "medium" if sc >= 0.75 else "LOW"})
    return rows


def propose() -> int:
    probe = json.loads(PROBE.read_text())
    master = load_master()
    mapping = {"season": 2026, "leagues": {}}
    for lg in probe:
        code = lg["code"]
        slots = [s for s in master if s["League Code"] == code]
        rows = assign(slots, lg["teams"])
        mapping["leagues"][code] = {"espn_league_id": lg["espn_league_id"], "teams": rows}
        by_slot = {s["Slot ID"]: s for s in slots}
        print(f"\n=== {code} {lg['espn_name']} ===")
        print(f"  {'tid':>3}  {'ESPN team':<32} {'ESPN owner(s)':<40} -> {'slot':<7} {'person':<24} conf")
        for r in rows:
            person = by_slot[r["slot_id"]]["Display Name"] if r["slot_id"] else "(unmatched)"
            owners = "; ".join(parse_owner(o)["first"] + " " + parse_owner(o)["last"] for o in r["espn_owners"]
                               if parse_owner(o)["display"] != COMMISSIONER_DISPLAY) or "(commissioner)"
            flag = "" if r["confidence"] == "high" else f"  <-- {r['confidence']} ({r['reason']})"
            co = " [co-owned w/ commissioner]" if r["co_owned_with_commissioner"] else ""
            print(f"  {r['espn_team_id']:>3}  {r['espn_team_name'][:32]:<32} {owners[:40]:<40} -> {r['slot_id'] or '-':<7} {person[:24]:<24} {r['score']}{flag}{co}")
        matched = {r["slot_id"] for r in rows if r["slot_id"]}
        for s in slots:
            if s["Slot ID"] not in matched:
                print(f"  !! slot {s['Slot ID']} {s['Display Name']} has NO ESPN team")
    MAPPING.write_text(json.dumps(mapping, indent=2))
    print(f"\nWrote {MAPPING.relative_to(ROOT)} — edit slot_id values if needed, then run: map_teams.py apply")
    return 0


def apply() -> int:
    mapping = json.loads(MAPPING.read_text())
    rows = load_master()
    by_slot = {r["Slot ID"]: r for r in rows}
    # reset the three join columns + Manager Seat for Members, then fill from mapping
    for r in rows:
        r["ESPN League ID"] = r["ESPN Team ID"] = r["ESPN Team Name"] = ""
        if r["Seat Type"] == "Member":
            r["Manager Seat"] = "No"
    problems = []
    for code, lg in mapping["leagues"].items():
        seen = set()
        for t in lg["teams"]:
            sid = t.get("slot_id")
            if not sid:
                problems.append(f"{code} team {t['espn_team_id']} {t['espn_team_name']} has no slot_id")
                continue
            if sid in seen:
                problems.append(f"{code}: slot {sid} assigned twice")
            seen.add(sid)
            r = by_slot[sid]
            r["ESPN League ID"] = str(lg["espn_league_id"])
            r["ESPN Team ID"] = str(t["espn_team_id"])
            r["ESPN Team Name"] = t["espn_team_name"]
            if t.get("co_owned_with_commissioner") and r["Seat Type"] == "Member":
                r["Manager Seat"] = "Yes"
                r["Notes"] = "Owns this team; commissioner account is co-owner so the League Manager can see the league"
            elif r["Notes"].startswith("Co-owned with League Manager (default"):
                r["Notes"] = ""
            # fill blank / single-initial last names from ESPN's registered name
            humans = [parse_owner(o) for o in t["espn_owners"]]
            humans = [o for o in humans if o["display"] != COMMISSIONER_DISPLAY and o["last"]]
            if humans and r["Seat Type"] == "Member" and (not r["Last Name"].strip() or len(r["Last Name"].strip()) == 1):
                o = humans[0]
                if not r["Last Name"].strip() or o["last"].lower().startswith(r["Last Name"].strip().lower()):
                    r["Last Name"] = o["last"].title() if o["last"].isupper() or o["last"].islower() else o["last"]
                    r["Display Name"] = f"{r['First Name']} {r['Last Name']}"
                    r["Notes"] = (r["Notes"] + "; " if r["Notes"] else "") + "Last name filled from ESPN"
            if r["Seat Type"] == "League Manager":
                r["Manager Seat"] = "Yes"
    if problems:
        print("NOT APPLIED:\n  " + "\n  ".join(problems))
        return 1
    write_master(rows)
    if not MASTER_JSON.exists():
        print("(no private JSON copy to mirror)")
        return 0
    j = json.loads(MASTER_JSON.read_text())
    for lg in j["leagues"]:
        lg["espn_league_id"] = mapping["leagues"][lg["code"]]["espn_league_id"]
        for s in lg["slots"]:
            r = by_slot[s["slot_id"]]
            s["espn_league_id"] = r["ESPN League ID"]; s["espn_team_id"] = r["ESPN Team ID"]
            s["espn_team_name"] = r["ESPN Team Name"]; s["manager_seat"] = r["Manager Seat"]
            s["last_name"] = r["Last Name"]; s["display_name"] = r["Display Name"]; s["notes"] = r["Notes"]
    MASTER_JSON.write_text(json.dumps(j, indent=2, ensure_ascii=False) + "\n")
    filled = sum(1 for r in rows if r["ESPN Team ID"])
    print(f"Applied: {filled}/{len(rows)} slots now have ESPN Team IDs. Manager Seat = Yes on: "
          + ", ".join(r["Slot ID"] for r in rows if r["Manager Seat"] == "Yes"))
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["propose", "apply"])
    a = ap.parse_args()
    sys.exit(propose() if a.cmd == "propose" else apply())
