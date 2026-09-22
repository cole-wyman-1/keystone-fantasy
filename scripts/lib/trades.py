"""Normalize ESPN transactions into trades. Pure functions (tested with a fixture)."""
from __future__ import annotations

from datetime import datetime, timezone

PRO_TEAMS = {1: "ATL", 2: "BUF", 3: "CHI", 4: "CIN", 5: "CLE", 6: "DAL", 7: "DEN", 8: "DET", 9: "GB", 10: "TEN",
             11: "IND", 12: "KC", 13: "LV", 14: "LAR", 15: "MIA", 16: "MIN", 17: "NE", 18: "NO", 19: "NYG", 20: "NYJ",
             21: "PHI", 22: "ARI", 23: "PIT", 24: "LAC", 25: "SF", 26: "SEA", 27: "TB", 28: "WSH", 29: "CAR", 30: "JAX",
             33: "BAL", 34: "HOU", 0: "FA"}

TRADE_TYPES = {"TRADE_PROPOSAL", "TRADE_ACCEPT"}
STATUS_LABEL = {"EXECUTED": "completed", "PENDING": "pending", "CANCELED": "canceled", "DECLINED": "declined",
                "VETOED": "vetoed", "EXPIRED": "expired"}


def _ts(ms) -> str | None:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat(timespec="seconds") if ms else None


def normalize_trades(transactions: list[dict]) -> list[dict]:
    """Keep trade proposals (any status); dedupe by id; one record per trade with its moves."""
    out, seen = [], set()
    for t in transactions:
        if t.get("type") not in TRADE_TYPES or t.get("id") in seen:
            continue
        moves = [{"player_id": i["playerId"], "from_team_id": i["fromTeamId"], "to_team_id": i["toTeamId"]}
                 for i in t.get("items", []) if i.get("type") == "TRADE" and i.get("fromTeamId") != i.get("toTeamId")]
        if not moves:
            continue
        seen.add(t["id"])
        teams = sorted({m["from_team_id"] for m in moves} | {m["to_team_id"] for m in moves})
        out.append({
            "id": t["id"], "status": t.get("status", ""), "status_label": STATUS_LABEL.get(t.get("status", ""), t.get("status", "").lower()),
            "proposed_utc": _ts(t.get("proposedDate")), "processed_utc": _ts(t.get("processDate")),
            "scoring_period": t.get("scoringPeriodId"), "proposer_team_id": t.get("teamId"),
            "team_ids": teams, "moves": moves,
        })
    out.sort(key=lambda x: (x["processed_utc"] or x["proposed_utc"] or ""), reverse=True)
    return out


def sides(trade: dict, label: dict, players: dict) -> list[dict]:
    """Per team: what it gave and what it received, with player names resolved."""
    res = []
    for tid in trade["team_ids"]:
        gives = [players.get(str(m["player_id"]), {"name": f"Player {m['player_id']}"}) for m in trade["moves"] if m["from_team_id"] == tid]
        gets = [players.get(str(m["player_id"]), {"name": f"Player {m['player_id']}"}) for m in trade["moves"] if m["to_team_id"] == tid]
        res.append({"team_id": tid, **label.get(tid, {"slot_id": None, "owner": "Unknown", "team_name": f"Team {tid}"}),
                    "gives": gives, "receives": gets})
    return res
