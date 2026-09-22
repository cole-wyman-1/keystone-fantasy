"""Emoji icons for profile fields. Free-text values are matched by keyword, with generic
fallbacks, so blanks and odd spellings never break anything."""
from __future__ import annotations

NFL = {
    "falcons": "🪶", "ravens": "🐦‍⬛", "bills": "🦬", "bears": "🐻", "bengals": "🐯", "cowboys": "⭐", "lions": "🦁",
    "packers": "🧀", "texans": "🐂", "rams": "🐏", "vikings": "⚔️", "patriots": "🇺🇸", "giants": "🗽", "jets": "✈️",
    "eagles": "🦅", "steelers": "🔩", "49ers": "⛏️", "seahawks": "🌊", "buccaneers": "🏴‍☠️", "commanders": "🎖️",
    "chiefs": "🏹", "dolphins": "🐬", "broncos": "🐴", "raiders": "☠️", "chargers": "⚡", "cardinals": "🐦",
    "saints": "⚜️", "panthers": "🐈‍⬛", "titans": "🔥", "colts": "🐎", "jaguars": "🐆", "browns": "🐶",
}

CITY = [
    (("boston", "bos", "cambridge", "chelmsford", ", ma"), "🦞"),
    (("nyc", "new york", "manhattan", "long island", "valley cottage", "trumansburg"), "🗽"),
    (("annandale", "mountain lakes", "princeton", "new jersey", ", nj"), "🌳"),
    (("washington", " dc", "d.c."), "🏛️"),
    (("san francisco", "mountain view", ", ca"), "🌉"),
    (("newport beach",), "🏄"),
    (("seattle",), "🌲"),
    (("chicago",), "🌭"),
    (("detroit",), "🚗"),
    (("cincinnati",), "🌶️"),
    (("houston", "austin", "texas"), "🤠"),
    (("madison",), "🧀"),
    (("monterrey", "mexico"), "🇲🇽"),
    (("edmonton", "toronto", "canada"), "🇨🇦"),
    (("london",), "🇬🇧"),
    (("athens",), "🍑"),
    (("st. louis", "st louis"), "🎸"),
]

COLLEGE = [
    (("michigan",), "〽️"), (("wisconsin",), "🦡"), (("cornell",), "🐻"), (("dartmouth",), "🌲"),
    (("duke",), "😈"), (("notre dame",), "☘️"), (("georgetown",), "🐶"), (("boston college",), "🦅"),
    (("boston university",), "🐕"), (("yale",), "🐶"), (("stanford",), "🌳"), (("berkeley",), "🐻"),
    (("los angeles",), "🐻"), (("san diego",), "🔱"), (("miami",), "🌴"), (("northwestern",), "🐈"),
    (("vanderbilt",), "⚓"), (("tulane",), "🌊"), (("syracuse",), "🍊"), (("pennsylvania",), "🔔"),
    (("columbia",), "🦁"), (("brown",), "🐻"), (("massachusetts institute", "mit"), "🦫"), (("brandeis",), "🦉"),
    (("northeastern",), "🐺"), (("university of washington",), "🐺"), (("lehigh",), "🦅"), (("indiana",), "🏀"),
    (("georgia institute", "georgia tech"), "🐝"), (("pomona",), "🐔"), (("trinity",), "🐓"), (("tufts",), "🐘"),
    (("albany",), "🐕"), (("alberta",), "🐻"), (("florida",), "🐊"), (("amherst",), "🎖️"), (("rhode island",), "🐏"),
    (("utah state",), "🐂"), (("vassar",), "🌹"), (("worcester",), "🐐"), (("harvard",), "📚"),
]

GROUP = {"boston": "🦞", "new york": "🗽", "dc": "🏛️", "sf": "🌉", "seattle": "🌲", "london": "🇬🇧",
         "australia": "🇦🇺", "alumni": "🎓"}


def _match(value: str, table, fallback: str) -> str:
    v = (value or "").lower()
    if not v:
        return ""
    for keys, icon in table:
        if any(k in v for k in keys):
            return icon
    return fallback


def nfl_icon(team: str) -> str:
    v = (team or "").lower()
    if not v:
        return ""
    return next((icon for k, icon in NFL.items() if k in v), "🏈")


def city_icon(city: str) -> str:
    return _match(city, CITY, "🏙️")


def college_icon(college: str) -> str:
    return _match(college, COLLEGE, "🎓")


def group_icon(group: str) -> str:
    v = (group or "").lower()
    if not v:
        return ""
    return next((icon for k, icon in GROUP.items() if k in v), "🏢")


def profile_icons(profile: dict) -> dict:
    """{field: icon} for the fields that are present."""
    out = {}
    if profile.get("favorite_team"):
        out["favorite_team"] = nfl_icon(profile["favorite_team"])
    if profile.get("home_city"):
        out["home_city"] = city_icon(profile["home_city"])
    if profile.get("college"):
        out["college"] = college_icon(profile["college"])
    if profile.get("keystone_group"):
        out["keystone_group"] = group_icon(profile["keystone_group"])
    return out
