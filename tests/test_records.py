from fixture_league import TEAM_IDS, WEEKS
from lib.records import games_from_weeks, playoff_picture, power_rank, record_book, standings, streaks, weekly_highs


def test_games_from_weeks_skips_in_progress():
    games = games_from_weeks(WEEKS)
    assert len(games) == 12  # 3 weeks x 2 matchups x 2 sides
    assert {g["week"] for g in games} == {1, 2, 3}


def test_standings_records_points_and_order():
    rows = {r["team_id"]: r for r in standings(games_from_weeks(WEEKS), TEAM_IDS)}
    assert (rows[1]["wins"], rows[1]["losses"], rows[1]["points_for"], rows[1]["points_against"]) == (2, 1, 290, 335)
    assert (rows[2]["wins"], rows[2]["losses"], rows[2]["points_for"]) == (1, 2, 300)
    assert (rows[3]["wins"], rows[3]["losses"], rows[3]["points_against"]) == (2, 1, 289)
    assert (rows[4]["wins"], rows[4]["losses"], rows[4]["points_for"]) == (1, 2, 274)
    # order: wins desc then PF desc -> 3, 1, 2, 4
    assert [r["team_id"] for r in sorted(rows.values(), key=lambda r: r["rank"])] == [3, 1, 2, 4]
    assert rows[4]["games_back"] == 1.0


def test_streaks():
    rows = {r["team_id"]: r for r in standings(games_from_weeks(WEEKS), TEAM_IDS)}
    assert rows[1]["streak"] == "L1" and rows[1]["longest_win_streak"] == 2
    assert rows[2]["streak"] == "W1" and rows[2]["longest_loss_streak"] == 2
    assert rows[3]["streak"] == "W1" and rows[3]["longest_win_streak"] == 1
    assert streaks([]) == {"current": "-", "current_type": "", "current_len": 0, "longest_win": 0,
                           "longest_win_end_idx": None, "longest_loss": 0, "longest_loss_end_idx": None}
    assert streaks(["W", "T", "W", "W"])["current"] == "W2"


def test_all_play_and_luck():
    rows = {r["team_id"]: r for r in standings(games_from_weeks(WEEKS), TEAM_IDS)}
    assert rows[1]["all_play_wins"] == 6 and rows[1]["expected_wins"] == 2.0 and rows[1]["luck"] == 0.0
    assert rows[2]["expected_wins"] == 1.67 and rows[2]["luck"] == -0.67
    assert rows[3]["expected_wins"] == 1.67 and rows[3]["luck"] == 0.33
    assert rows[4]["expected_wins"] == 0.67 and rows[4]["luck"] == 0.33


def test_weekly_highs():
    highs = weekly_highs(games_from_weeks(WEEKS))
    assert highs[1]["high"]["team_id"] == 1 and highs[1]["high"]["points"] == 120
    assert highs[3]["high"]["team_id"] == 2 and highs[3]["low"]["team_id"] == 1


def test_record_book():
    games = [{**g, "league_code": "T"} for g in games_from_weeks(WEEKS)]
    rb = record_book(games, {}, n=3)
    assert rb["highest_score"][0]["points"] == 130 and rb["highest_score"][0]["team_id"] == 2
    assert rb["lowest_score"][0]["points"] == 60
    assert rb["biggest_blowout"][0]["margin"] == 70 and rb["biggest_blowout"][0]["team_id"] == 2
    assert rb["closest_game"][0]["margin"] == 1 and rb["closest_game"][0]["team_id"] == 3
    assert rb["most_points_in_loss"][0]["points"] == 105  # team 3, week 2
    assert rb["fewest_points_in_win"][0]["points"] == 90  # team 3, week 1
    # blowouts are deduplicated per matchup
    assert len(rb["biggest_blowout"]) == 3 and len({(r["week"], r["team_id"]) for r in rb["biggest_blowout"]}) == 3


def test_record_book_with_extras():
    games = [{**g, "league_code": "T"} for g in games_from_weeks(WEEKS)]
    extras = {("T", 1, 1): {"bench_points": 40, "optimal_points": 150, "left_on_table": 30,
                            "top_player": {"name": "QB Guy", "position": "QB", "points": 35, "started": True}},
              ("T", 2, 3): {"bench_points": 10, "optimal_points": 130, "left_on_table": 0,
                            "top_player": {"name": "RB Guy", "position": "RB", "points": 44, "started": True}}}
    rb = record_book(games, extras, n=3)
    assert rb["most_bench_points"][0]["bench_points"] == 40
    assert rb["most_left_on_table"][0]["left_on_table"] == 30
    assert rb["best_player_week"][0]["player"] == "RB Guy" and rb["best_player_week"][0]["player_points"] == 44


def test_playoff_picture_flags():
    rows = standings(games_from_weeks(WEEKS), TEAM_IDS)
    playoff_picture(rows, playoff_teams=2, regular_season_weeks=3, weeks_complete=3)  # season over
    by = {r["team_id"]: r["playoff"] for r in rows}
    assert by[3] == "clinched" and by[1] == "clinched"
    assert by[2] == "eliminated" and by[4] == "eliminated"
    rows = standings(games_from_weeks(WEEKS), TEAM_IDS)
    playoff_picture(rows, playoff_teams=2, regular_season_weeks=6, weeks_complete=3)  # 3 weeks left
    by = {r["team_id"]: r["playoff"] for r in rows}
    assert by[3] == "in" and by[1] == "in" and by[2] in ("bubble", "out") and by[4] in ("bubble", "out")


def test_power_rank_orders_by_points_and_all_play():
    rows = standings(games_from_weeks(WEEKS), TEAM_IDS)
    for r in rows:
        r["league_code"] = "T"
    pr = power_rank(rows)
    assert [r["team_id"] for r in pr][0] in (1, 2, 3)  # 4 is clearly last
    assert pr[-1]["team_id"] == 4
    assert pr[0]["power_rank"] == 1 and pr[0]["power_score"] >= pr[1]["power_score"]
