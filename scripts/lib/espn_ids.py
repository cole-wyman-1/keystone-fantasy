"""ESPN Fantasy Football id tables (copied from the espn-api project's constants)."""

POSITION_MAP = {1: "QB", 2: "RB", 3: "WR", 4: "TE", 5: "K", 16: "D/ST", 7: "P", 9: "DT", 10: "DE",
                11: "LB", 12: "CB", 13: "S", 14: "HC", 0: "QB"}

LINEUP_SLOT_MAP = {0: "QB", 1: "TQB", 2: "RB", 3: "RB/WR", 4: "WR", 5: "WR/TE", 6: "TE", 7: "OP",
                   8: "DT", 9: "DE", 10: "LB", 11: "DL", 12: "CB", 13: "S", 14: "DB", 15: "DP",
                   16: "D/ST", 17: "K", 18: "P", 19: "HC", 20: "BE", 21: "IR", 22: "", 23: "FLEX",
                   24: "EDR", 25: "RB/WR/TE"}

NON_STARTING_SLOTS = {20, 21}  # bench, IR


def slot_name(slot_id: int) -> str:
    return LINEUP_SLOT_MAP.get(slot_id, str(slot_id))


def position_name(pos_id: int) -> str:
    return POSITION_MAP.get(pos_id, str(pos_id))
