from lib.trades import normalize_trades, sides


def item(pid, frm, to, typ="TRADE"):
    return {"playerId": pid, "fromTeamId": frm, "toTeamId": to, "type": typ, "fromLineupSlotId": 20, "toLineupSlotId": -1}


TX = [
    {"id": "t1", "type": "TRADE_PROPOSAL", "status": "EXECUTED", "teamId": 3, "scoringPeriodId": 2,
     "proposedDate": 1789703433357, "processDate": 1789790000000,
     "items": [item(11, 1, 3), item(12, 1, 3), item(21, 3, 1)]},
    {"id": "t1", "type": "TRADE_PROPOSAL", "status": "EXECUTED", "teamId": 3, "scoringPeriodId": 3,  # same trade seen in a later period
     "proposedDate": 1789703433357, "processDate": 1789790000000, "items": [item(11, 1, 3), item(21, 3, 1)]},
    {"id": "t2", "type": "TRADE_PROPOSAL", "status": "PENDING", "teamId": 5, "scoringPeriodId": 3,
     "proposedDate": 1789800000000, "items": [item(31, 5, 6), item(41, 6, 5)]},
    {"id": "t3", "type": "TRADE_DECLINE", "status": "EXECUTED", "teamId": 1, "scoringPeriodId": 2,
     "proposedDate": 1789747774833, "items": [item(21, 0, 0, typ=None)]},
    {"id": "t4", "type": "ROSTER", "status": "EXECUTED", "teamId": 9, "scoringPeriodId": 3, "proposedDate": 1790055788568,
     "items": [item(99, 0, 0, typ="LINEUP")]},
]


def test_normalize_keeps_trades_dedupes_and_sorts():
    trades = normalize_trades(TX)
    assert [t["id"] for t in trades] == ["t2", "t1"]  # newest first, t1 once, decline/roster ignored
    t1 = trades[1]
    assert t1["status_label"] == "completed" and t1["team_ids"] == [1, 3] and len(t1["moves"]) == 3
    assert t1["processed_utc"].startswith("2026-09-") and trades[0]["processed_utc"] is None


def test_sides_resolve_names_and_direction():
    t1 = normalize_trades(TX)[1]
    label = {1: {"slot_id": "HAR-08", "owner": "Ranmit", "team_name": "Randos"}, 3: {"slot_id": "HAR-02", "owner": "Nhi", "team_name": "Mimi"}}
    players = {"11": {"name": "A", "position": "RB", "pro_team": "SF"}, "12": {"name": "B", "position": "WR", "pro_team": "NE"},
               "21": {"name": "C", "position": "TE", "pro_team": "KC"}}
    s = sides(t1, label, players)
    assert s[0]["owner"] == "Ranmit" and [p["name"] for p in s[0]["gives"]] == ["A", "B"] and [p["name"] for p in s[0]["receives"]] == ["C"]
    assert s[1]["owner"] == "Nhi" and [p["name"] for p in s[1]["gives"]] == ["C"] and [p["name"] for p in s[1]["receives"]] == ["A", "B"]


def test_unknown_player_gets_placeholder():
    t1 = normalize_trades(TX)[1]
    s = sides(t1, {}, {})
    assert s[0]["owner"] == "Unknown" and s[0]["gives"][0]["name"] == "Player 11"
