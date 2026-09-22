"""Download small NFL and college logos once and self-host them under site/public/logos/.

Sources: ESPN's public logo CDN (resized to 96px by its combiner endpoint). Four schools ESPN
doesn't list fall back to the school's own favicon via Google's favicon service.
Idempotent: existing files are kept unless --force. Writes data/logos.json (name -> site path).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "site" / "public" / "logos"
OUT_JSON = ROOT / "data" / "logos.json"
COMBINER = "https://a.espncdn.com/combiner/i?img=/i/teamlogos/{league}/500/{key}.png&h=96&w=96"
FAVICON = "https://www.google.com/s2/favicons?domain={domain}&sz=128"

NFL_ABBR = {
    "Arizona Cardinals": "ari", "Atlanta Falcons": "atl", "Baltimore Ravens": "bal", "Buffalo Bills": "buf",
    "Carolina Panthers": "car", "Chicago Bears": "chi", "Cincinnati Bengals": "cin", "Cleveland Browns": "cle",
    "Dallas Cowboys": "dal", "Denver Broncos": "den", "Detroit Lions": "det", "Green Bay Packers": "gb",
    "Houston Texans": "hou", "Indianapolis Colts": "ind", "Jacksonville Jaguars": "jax", "Kansas City Chiefs": "kc",
    "Las Vegas Raiders": "lv", "Los Angeles Chargers": "lac", "Los Angeles Rams": "lar", "Miami Dolphins": "mia",
    "Minnesota Vikings": "min", "New England Patriots": "ne", "New Orleans Saints": "no", "New York Giants": "nyg",
    "New York Jets": "nyj", "Philadelphia Eagles": "phi", "Pittsburgh Steelers": "pit", "San Francisco 49ers": "sf",
    "Seattle Seahawks": "sea", "Tampa Bay Buccaneers": "tb", "Tennessee Titans": "ten", "Washington Commanders": "wsh",
}

# master-file college name -> ESPN NCAA team id (hand-checked against ESPN's team list)
COLLEGE_ESPN = {
    "Boston College": 103, "Boston University": 104, "Brown University": 225, "Columbia University": 171,
    "Cornell University": 172, "Dartmouth College": 159, "Duke University": 150, "Georgetown University": 46,
    "Georgia Institute of Technology": 59, "Harvard University": 108, "Indiana University": 84,
    "Lehigh University": 2329, "Massachusetts Institute of Technology": 109, "Northeastern University": 111,
    "Northwestern University": 77, "Pomona College": 2923, "Stanford University": 24, "Syracuse University": 183,
    "Trinity College": 2977, "Tufts University": 112, "Tulane University": 2655, "University at Albany, SUNY": 399,
    "University of California, Berkeley": 25, "University of California, Los Angeles": 26,
    "University of California, San Diego": 28, "University of Florida": 57,
    "University of Massachusetts Amherst": 113, "University of Miami": 2390, "University of Michigan": 130,
    "University of Notre Dame": 87, "University of Pennsylvania": 219, "University of Rhode Island": 227,
    "University of Washington": 264, "University of Wisconsin-Madison": 275, "Utah State University": 328,
    "Vanderbilt University": 238, "Yale University": 43,
}
# schools ESPN doesn't carry -> their website favicon
COLLEGE_DOMAIN = {
    "Brandeis University": "brandeis.edu", "University of Alberta": "ualberta.ca",
    "Vassar College": "vassar.edu", "Worcester Polytechnic Institute": "wpi.edu",
}


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def download(url: str, dest: Path, force: bool) -> bool:
    if dest.exists() and not force:
        return True
    r = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    if r.status_code != 200 or not r.content or "image" not in r.headers.get("content-type", ""):
        print(f"  FAILED {url} -> HTTP {r.status_code} {r.headers.get('content-type')}")
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(r.content)
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    master = json.loads((ROOT / "data" / "master.json").read_text())
    teams_used = sorted({s["favorite_team"] for s in master["slots"] if s.get("favorite_team")})
    colleges_used = sorted({s["college"] for s in master["slots"] if s.get("college")})
    out = {"nfl": {}, "college": {}}
    missing = []
    for t in teams_used:
        abbr = NFL_ABBR.get(t)
        if not abbr:
            missing.append(f"NFL: {t}")
            continue
        dest = OUT_DIR / "nfl" / f"{abbr}.png"
        if download(COMBINER.format(league="nfl", key=abbr), dest, args.force):
            out["nfl"][t] = f"logos/nfl/{abbr}.png"
    for c in colleges_used:
        if c in COLLEGE_ESPN:
            dest = OUT_DIR / "college" / f"{COLLEGE_ESPN[c]}.png"
            ok = download(COMBINER.format(league="ncaa", key=COLLEGE_ESPN[c]), dest, args.force)
        elif c in COLLEGE_DOMAIN:
            dest = OUT_DIR / "college" / f"{slug(c)}.png"
            ok = download(FAVICON.format(domain=COLLEGE_DOMAIN[c]), dest, args.force)
        else:
            missing.append(f"college: {c}")
            continue
        if ok:
            out["college"][c] = f"logos/college/{dest.name}"
    OUT_JSON.write_text(json.dumps(out, indent=1, ensure_ascii=False))
    total = sum(p.stat().st_size for p in OUT_DIR.rglob("*.png"))
    print(f"NFL logos: {len(out['nfl'])}/{len(teams_used)}  college logos: {len(out['college'])}/{len(colleges_used)}  "
          f"({total/1024:.0f} KB on disk) -> {OUT_JSON.relative_to(ROOT)}")
    if missing:
        print("No logo source for: " + "; ".join(missing))
    return 0


if __name__ == "__main__":
    sys.exit(main())
