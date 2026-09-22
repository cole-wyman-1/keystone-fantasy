"""Integration checks on generated data/site (skipped if compute.py hasn't run)."""
import json
import re
from pathlib import Path

import pytest

SITE = Path(__file__).resolve().parent.parent / "data" / "site"
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")

pytestmark = pytest.mark.skipif(not (SITE / "meta.json").exists(), reason="run scripts/compute.py first")


def test_no_emails_in_site_data():
    for p in SITE.glob("*.json"):
        assert not EMAIL.search(p.read_text()), f"email address found in {p.name}"


def test_every_slot_has_a_team_and_league():
    people = json.loads((SITE / "people.json").read_text())
    assert len(people) == 84
    assert all(p["team"] for p in people.values())


def test_standings_match_espn_records():
    """Our standings (from matchups) must agree with ESPN's own W-L and PF for completed weeks."""
    root = SITE.parent / "espn"
    standings = json.loads((SITE / "standings.json").read_text())
    for code, rows in standings.items():
        league = json.loads((root / code / "league.json").read_text())
        espn = {t["espn_team_id"]: t["espn_record"] for t in league["teams"]}
        for r in rows:
            e = espn[r["team_id"]]
            assert (r["wins"], r["losses"], r["ties"]) == (e["wins"], e["losses"], e["ties"]), (code, r["owner"])
            assert abs(r["points_for"] - e["points_for"]) < 0.02, (code, r["owner"])
