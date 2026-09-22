from lib.icons import city_icon, college_icon, nfl_icon, profile_icons


def test_known_values():
    assert nfl_icon("New England Patriots") == "🇺🇸"
    assert nfl_icon("San Francisco 49ers") == "⛏️"
    assert city_icon("BOS") == "🦞" and city_icon("NYC") == "🗽" and city_icon("Washington, DC") == "🏛️"
    assert college_icon("University of Wisconsin-Madison") == "🦡"


def test_fallbacks_and_blanks():
    assert nfl_icon("") == "" and city_icon("") == "" and college_icon("") == ""
    assert nfl_icon("Some Team") == "🏈" and city_icon("Nowhere") == "🏙️" and college_icon("Unknown U") == "🎓"
    assert profile_icons({}) == {}
    assert profile_icons({"college": "Duke University"}) == {"college": "😈"}
