"""A tiny 4-team league, 3 completed weeks + 1 in-progress, with hand-computed answers."""


def matchup(mid, wk, h, a, hp, ap, decided=True):
    winner = "UNDECIDED" if not decided else ("TIE" if hp == ap else ("HOME" if hp > ap else "AWAY"))
    return {"matchup_id": mid, "matchup_period": wk, "home_team_id": h, "away_team_id": a,
            "home_points": hp, "away_points": ap, "winner": winner, "playoff_tier": "NONE", "is_bye": False}


TEAM_IDS = [1, 2, 3, 4]

# week 1: 1 beats 2 (120-100), 3 beats 4 (90-80)
# week 2: 1 beats 3 (110-105), 4 beats 2 (95-70)
# week 3: 2 beats 1 (130-60), 3 beats 4 (100-99)
# week 4 in progress: ignored everywhere
WEEKS = [
    {"scoring_period": 1, "matchup_period": 1, "complete": True, "lineups": {},
     "matchups": [matchup(1, 1, 1, 2, 120, 100), matchup(2, 1, 3, 4, 90, 80)]},
    {"scoring_period": 2, "matchup_period": 2, "complete": True, "lineups": {},
     "matchups": [matchup(3, 2, 1, 3, 110, 105), matchup(4, 2, 4, 2, 95, 70)]},
    {"scoring_period": 3, "matchup_period": 3, "complete": True, "lineups": {},
     "matchups": [matchup(5, 3, 2, 1, 130, 60), matchup(6, 3, 3, 4, 100, 99)]},
    {"scoring_period": 4, "matchup_period": 4, "complete": False, "lineups": {},
     "matchups": [matchup(7, 4, 1, 4, 50, 40, decided=False), matchup(8, 4, 2, 3, 10, 20, decided=False)]},
]

# Hand-computed expectations
# Team 1: W W L  -> 2-1, PF 290, PA 335, streak L1, longest W 2
# Team 2: L L W  -> 1-2, PF 300, PA 275, streak W1, longest L 2
# Team 3: W L W  -> 2-1, PF 295, PA 289, streak W1
# Team 4: L W L  -> 1-2, PF 274, PA 260, streak L1
# All-play (3 opponents per week):
#  wk1 pts 120,100,90,80 -> t1 3, t2 2, t3 1, t4 0
#  wk2 pts 110,105,95,70 -> t1 3, t3 2, t4 1, t2 0
#  wk3 pts 130,100,99,60 -> t2 3, t3 2, t4 1, t1 0
#  totals: t1 6/9 = 2.0 exp wins, luck 0; t2 5/9=1.67, luck -0.67; t3 5/9=1.67, luck +0.33; t4 2/9=0.67, luck +0.33
