# Keystone Fantasy Football 2026 — Site Plan

Status: APPROVED 2026-09-21. ESPN layer: raw requests. Cron: 11:00 UTC Mon/Tue/Fri.

## 1. Decisions so far

| Topic | Decision |
|---|---|
| Leagues | 7 ESPN leagues, 12 teams each, 84 slots, 81 people + 3 commissioner seats |
| Privacy | All 7 private → every request carries `espn_s2` + `SWID` cookies |
| ESPN account | One account (yours) is in all 7 leagues |
| League IDs | EMP=225405520, GOT=321048737, BEA=57393498, HAR=420658602, ALC=1464805408, ALL=313712614, C2C=1314750435 |
| Rename | C2C is now the **Freedom League** (code stays `C2C`, Slot IDs unchanged, display name changes everywhere) |
| Scoring tracked | Total points, bench points, optimal lineup, individual player highs |
| Hosting | Static site + JSON, rebuilt on a schedule, **GitHub Pages** |
| Framework | **Astro** (static output, near-zero client JS) |
| Domain | Default `https://<github-user>.github.io/keystone-fantasy/` for now |
| Refresh | **Tue, Fri, Mon mornings ET** + manual trigger, on **GitHub Actions cron** |
| Pages | Home, 7 League, 84 Person/Slot, Weekly High Scores, Record Book, Power Ranking |
| Groupings | Office / NFL-team / college standings: **not now**, data model keeps the door open |
| Design | Clean, minimal, light theme, mobile-first, no logo (text wordmark) |
| Access | Public. **Emails never reach the built site.** |

## 2. Architecture (one picture)

```
master CSV (you edit)          leagues.json (checked in)         .env / GitHub Secrets
   Starter Files/…master.csv     code→ESPN league id, season       ESPN_S2, ESPN_SWID
          │                              │                                │
          ▼                              ▼                                ▼
   scripts/import_master.py     scripts/fetch_espn.py  ──── ESPN v3 read API (cookies)
          │                              │  caches every raw response in data/raw/
          ▼                              ▼
   data/master.json             data/espn/{code}/{week}.json  (normalized: teams, scores, lineups)
          └──────────────┬───────────────┘
                         ▼
                scripts/compute.py   →  data/site/*.json  (standings, weekly highs, records,
                                        power ranking, per-person series; EMAILS STRIPPED)
                         ▼
                site/ (Astro)  →  build  →  GitHub Pages
                         ▲
        .github/workflows/refresh.yml  (cron Mon/Tue/Fri + manual button)
```

Python (3.12) for import/fetch/compute because that's the data-heavy part and easy to unit-test.
Astro + Node 22 for the site. No database, no server.

## 3. Repository

New standalone repo at `Keystone Fantasy/` (this folder), pushed to GitHub as `keystone-fantasy`.
It currently sits untracked inside your `Python-Projects` repo; that's fine, git treats a nested
repo as an opaque folder.

```
keystone-fantasy/
├── CLAUDE.md                 architecture, how to run, decisions (kept current)
├── PLAN.md                   this file
├── README.md                 your operator guide (cookies, CSV edits, manual refresh, new season)
├── .env.example              ESPN_S2= / ESPN_SWID=   (.env itself is git-ignored)
├── leagues.json              season + 7 codes → ESPN league ids + display names
├── Starter Files/            master CSV/JSON/XLSX — the CSV is the editable source of truth
├── scripts/
│   ├── espn_client.py        thin cookie-auth client, retries, raw caching
│   ├── espn_probe.py         Phase 2: prints league name, teams, owners, current week
│   ├── import_master.py      CSV → data/master.json (validates, applies rename map)
│   ├── map_teams.py          Phase 3: proposes slot↔ESPN team matches, writes IDs back to CSV
│   ├── fetch_espn.py         Phase 4: all leagues, all completed weeks → data/espn/
│   ├── compute.py            Phase 4: derived JSON → data/site/
│   └── lib/                  records.py, standings.py, lineups.py (pure functions, tested)
├── tests/                    pytest fixtures: small synthetic league, known answers
├── data/
│   ├── raw/                  verbatim ESPN responses (debug; git-ignored, kept as CI artifact)
│   ├── espn/                 normalized per league per week (committed)
│   ├── site/                 what Astro reads (committed, no emails)
│   └── meta.json             last_success_utc, season, weeks_completed, git sha
├── site/                     Astro project
└── .github/workflows/refresh.yml
```

## 4. Data model

### 4.1 Master roster (source of truth = the CSV)
`import_master.py` reads the CSV, never writes it except for the three ESPN join columns
(Phase 3, with your confirmation). Rules:
- Key = `Slot ID`. Everything else can change and re-import safely.
- Blank profile fields → omitted on the site (no "College: —" rows).
- `Seat Type = League Manager` rows render as "Commissioner" with no profile block.
- `Manager Seat = Yes` on a Member row → that person's team; shown as theirs, not yours.
- League display names come from `leagues.json` (so C2C → "Freedom League" without
  rewriting 12 CSV rows; I will also update the CSV/JSON/XLSX `League` column once, so all
  documents agree).
- Emails are loaded into `data/master.json` only for matching; `compute.py` strips them
  before writing `data/site/`. A test asserts no `@` appears in `data/site/`.

### 4.2 leagues.json (checked in, not secret)
```json
{ "season": 2026,
  "leagues": [
    {"code": "EMP", "name": "Empire League",   "espn_league_id": 225405520,  "managed_by": "member"},
    {"code": "GOT", "name": "Gotham League",   "espn_league_id": 321048737,  "managed_by": "league_manager"},
    {"code": "BEA", "name": "Beantown League", "espn_league_id": 57393498,   "managed_by": "member"},
    {"code": "HAR", "name": "Harbor League",   "espn_league_id": 420658602,  "managed_by": "member"},
    {"code": "ALC", "name": "Alumni Classic",  "espn_league_id": 1464805408, "managed_by": "league_manager"},
    {"code": "ALL", "name": "Alumni Legends",  "espn_league_id": 313712614,  "managed_by": "league_manager"},
    {"code": "C2C", "name": "Freedom League",  "espn_league_id": 1314750435, "managed_by": "member"}
  ]}
```

### 4.3 Normalized ESPN data (`data/espn/{code}/…`)
- `league.json`: name, scoring type (PPR/half/standard), reg-season weeks, playoff team count,
  divisions, current scoring period, teams [{espn_team_id, name, abbrev, owner display names}].
- `week_{n}.json`: matchups [{home_team_id, away_team_id, home_pts, away_pts, winner,
  is_playoff}], and per team: starters + bench [{player_id, name, pos, lineup_slot,
  eligible_slots, points}], bench_points, optimal_points.

### 4.4 Site data (`data/site/`) — what pages read
- `leagues.json`, `people.json` (slot → profile + team + season series)
- `standings.json` (per league: W-L-T, PF, PA, streak, division, playoff seed / in-hunt)
- `weekly.json` (every league × week × team score, opponent, result, bench, optimal)
- `highs.json` (weekly high per league + overall, leaderboard of "most weekly highs")
- `records.json` (record book, see §6)
- `power.json` (cross-league ranking)
- `meta.json` (last successful refresh, weeks completed, stale flag)

## 5. ESPN fetch

Base URL (verified 2026-09-21, unchanged since April 2024):
```
https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/{season}/segments/0/leagues/{leagueId}
```
Views pulled:
| View | Used for |
|---|---|
| `mSettings` | league name, scoring format, reg-season length, playoff count, divisions |
| `mTeam` | teams, owners (display name, first/last), records, points for/against |
| `mMatchupScore` | every matchup for every scoring period in one call |
| `mBoxscore` + `mRoster` with `scoringPeriodId=N` | per-week lineups: starters, bench, points per player, eligible slots (for bench / optimal / player highs) |

Auth: cookies `espn_s2` and `SWID` from `.env` locally, GitHub Secrets in CI. Note: the API
returns owner **display names and first/last names**, never emails, so Phase 3 matching is
name-based and I'll ask you to confirm anything ambiguous.

Library choice — raw `requests` vs `espn-api`:
- `espn-api` (0.46.0, Mar 2026, actively maintained) parses everything for you, including
  box scores with slot positions. Downsides: it hides the raw JSON (harder to cache and
  debug), makes its own extra calls, and a breaking release can take the job down.
- Raw requests: ~100 lines, full control, every response cached verbatim to `data/raw/`,
  retries and 401/403 detection are ours. We copy `espn-api`'s lineup-slot id map.
- **Recommendation: raw requests**, with `espn-api` installed only as a cross-check in the
  probe. Easy to flip if you prefer.

Idempotent: re-running fetches only weeks that are complete and not yet cached, unless
`--force`. Completed week = scoring period < current, or all matchups final.

## 6. Compute layer (all pure functions, unit-tested against a fixture league)

Standings: W-L-T, PF, PA, streak, from matchups (not ESPN's cached record, so it stays
consistent with our weekly data). Playoff picture: seeds from `mSettings` playoff count and
division rules; "in / bubble / out" by games back with weeks remaining.

Weekly highs: per league per week, overall per week, leaderboard of most weekly-high wins.

Record book (season-to-date, per league and overall):
highest single-week score · lowest · biggest blowout · closest game · longest win streak ·
longest losing streak · most points in a loss · fewest points in a win · most bench points ·
largest gap actual vs optimal lineup · best single-player week (overall and per position) ·
best luck / worst luck.

Luck / expected wins: "all-play" method. Each week a team's expected win share =
(teams it outscored in its league) / 11. Expected wins = sum over weeks.
Luck = actual wins − expected wins (positive = lucky).

Power ranking (cross-league): leagues may use different scoring formats, so raw points are
not comparable. Score = 0.5 × within-league z-score of PPG + 0.3 × expected win % +
0.2 × last-3-weeks z-score. Shown alongside raw PPG and record. If the probe shows all 7
use the identical scoring format, I'll simplify to raw points and tell you.

## 7. Pages (Astro, mobile-first, light theme, stable URLs)

| URL | Content |
|---|---|
| `/` | 7 league cards (leader, this week's high), overall top score this week, last-refresh time + stale warning, links |
| `/leagues/{code}/` | standings table, this week's matchups & scores, weekly high scorer, playoff picture, week-by-week high scorers |
| `/people/{slot-id}/` | name, league, team name, record, weekly scores bar chart (inline SVG), best/worst week, bench/optimal stats, profile fields that exist (group, NFL team, city, college, company). Commissioner seats: minimal page |
| `/weekly-highs/` | week selector, per-league and overall highs, leaderboard |
| `/records/` | record book tables, per league tabs + overall |
| `/power/` | all 84 teams ranked, filterable by league |

Tables collapse to cards under 640px. No analytics, no cookies, no client JS except a tiny
week-selector.

## 8. Schedule

GitHub Actions cron: `0 11 * * 1,2,5` (Mon/Tue/Fri at 11:00 UTC = 7:00am EDT now,
6:00am EST after clocks change on 1 Nov 2026). GitHub cron cannot follow DST, so I pick a
single UTC time that lands at a sane hour year-round. Plus `workflow_dispatch` (manual
button in the Actions tab).

Job steps: checkout → import master → fetch (fails on 401/403 or any league missing) →
compute → run tests → build Astro → commit `data/` back to main → deploy to Pages.
If fetch fails the job stops before deploy: site keeps the last good data, GitHub emails you,
and the home page shows "last successful refresh" so staleness is visible.

## 9. Phase plan and commits

- Phase 2: repo init, `.gitignore`, `.env.example`, `leagues.json`, `espn_client.py`,
  `espn_probe.py`; you run the probe. Commit.
- Phase 3: `map_teams.py`, confirm matches with you, write IDs into CSV. Commit.
- Phase 4: fetch → compute + tests → Astro site → workflow → README. One commit per step.
- Phase 5: deploy, hand-check one league + one week against the ESPN app, list open items.

## 10. Assumptions to verify in the probe
- Every league has exactly 12 teams and the same regular-season length.
- Scoring formats (may differ across leagues; affects power ranking).
- Current week and whether Week 1/2 are already complete (season is underway on 2026-09-21).
