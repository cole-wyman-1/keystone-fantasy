"""Thin, cookie-authenticated client for ESPN's unofficial Fantasy Football v3 read API.

Every response is cached verbatim under data/raw/<season>/<league_id>/ so we can debug
without re-hitting ESPN. Auth failures (401/403) raise AuthError with a plain-language
message so the scheduled job fails loudly instead of publishing stale data.
"""
from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

import requests
from dotenv import load_dotenv

BASE_URL = "https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl"
ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0 Safari/537.36"
)


class AuthError(RuntimeError):
    """ESPN rejected the cookies (expired espn_s2, wrong SWID, or no access to the league)."""


class ESPNError(RuntimeError):
    """Any other non-success response from ESPN."""


def load_credentials() -> tuple[str, str]:
    """Read ESPN_S2 / ESPN_SWID from the environment (.env locally, secrets in CI)."""
    load_dotenv(ROOT / ".env")
    s2 = os.environ.get("ESPN_S2", "").strip()
    swid = os.environ.get("ESPN_SWID", "").strip()
    problems = []
    if not s2:
        problems.append("ESPN_S2 is empty")
    if not swid:
        problems.append("ESPN_SWID is empty")
    elif not re.fullmatch(r"\{[0-9A-Fa-f-]{36}\}", swid):
        problems.append("ESPN_SWID must look like {XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX} including the braces")
    if problems:
        raise AuthError("; ".join(problems) + ". See README.md 'Refreshing ESPN cookies'.")
    return s2, swid


@dataclass
class ESPNClient:
    season: int
    espn_s2: str
    swid: str
    raw_dir: Path = RAW_DIR
    timeout: float = 30.0
    retries: int = 3
    session: requests.Session = field(default_factory=requests.Session, repr=False)

    def __post_init__(self) -> None:
        self.session.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})
        self.session.cookies.set("espn_s2", self.espn_s2, domain=".espn.com")
        self.session.cookies.set("SWID", self.swid, domain=".espn.com")

    # -- public -----------------------------------------------------------------

    def league(self, league_id: int, views: list[str], scoring_period: int | None = None,
               cache_name: str | None = None) -> dict:
        """GET one league with the given views. Returns parsed JSON and caches it raw."""
        url = f"{BASE_URL}/seasons/{self.season}/segments/0/leagues/{league_id}"
        params: list[tuple[str, str]] = [("view", v) for v in views]
        if scoring_period is not None:
            params.append(("scoringPeriodId", str(scoring_period)))
        data = self._get(url, params, league_id)
        name = cache_name or ("_".join(views) + (f"_sp{scoring_period}" if scoring_period else ""))
        self._cache(league_id, name, data)
        return data

    # -- internals ----------------------------------------------------------------

    def _get(self, url: str, params: list[tuple[str, str]], league_id: int) -> dict:
        last_exc: Exception | None = None
        for attempt in range(1, self.retries + 1):
            try:
                resp = self.session.get(url, params=params, timeout=self.timeout)
            except requests.RequestException as exc:  # network blip: retry
                last_exc = exc
                time.sleep(2 * attempt)
                continue
            if resp.status_code in (401, 403):
                raise AuthError(
                    f"ESPN returned HTTP {resp.status_code} for league {league_id}. "
                    "Your espn_s2 cookie has probably expired, or this account cannot view the league. "
                    "Refresh the cookies (README.md) and re-run."
                )
            if resp.status_code == 404:
                raise ESPNError(f"League {league_id} not found for season {self.season} (HTTP 404). Check leagues.json.")
            if resp.status_code >= 500:
                last_exc = ESPNError(f"ESPN HTTP {resp.status_code} for league {league_id}")
                time.sleep(2 * attempt)
                continue
            if resp.status_code != 200:
                raise ESPNError(f"ESPN HTTP {resp.status_code} for league {league_id}: {resp.text[:300]}")
            try:
                data = resp.json()
            except ValueError as exc:
                raise ESPNError(f"ESPN returned non-JSON for league {league_id}: {resp.text[:300]}") from exc
            # Private league without valid cookies sometimes comes back 200 with a message list.
            if isinstance(data, dict) and data.get("messages") and "id" not in data:
                raise AuthError(f"ESPN refused league {league_id}: {data['messages']}")
            if isinstance(data, list):  # leagueHistory-style shape; normalise to a dict
                data = data[0]
            return data
        raise ESPNError(f"Giving up on league {league_id} after {self.retries} attempts: {last_exc}")

    def _cache(self, league_id: int, name: str, data: dict) -> None:
        path = self.raw_dir / str(self.season) / str(league_id) / f"{name}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=1))


def client_from_env(season: int) -> ESPNClient:
    s2, swid = load_credentials()
    return ESPNClient(season=season, espn_s2=s2, swid=swid)
