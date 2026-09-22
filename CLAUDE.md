# Keystone Fantasy Football 2026 — notes for Claude Code

Live site: https://cole-wyman-1.github.io/keystone-fantasy/
Repo: https://github.com/cole-wyman-1/keystone-fantasy (public, GitHub Pages via Actions)
Owner: Cole Wyman (commissioner of all 7 leagues). Shipped 2026-09-22. `PLAN.md` = original approved design,
`AGENT_LOG.md` = session-by-session history (append to it at the end of every session), `README.md` = operator guide for Cole.

## What this is
Static Astro site for 7 private ESPN fantasy leagues (84 team slots = 81 people + 3 commissioner seats).
Python scripts pull ESPN on a GitHub Actions cron (Mon/Tue/Fri 11:00 UTC), compute standings / weekly highs /
record book / power ranking / trades, rebuild the site, deploy. No server, no database except the message board.

## Pipeline (run in this order; the workflow does exactly this)
```
.venv/bin/python scripts/import_master.py   # Starter Files/keystone_ff_2026_master.csv -> data/master.json (validates; no emails)
.venv/bin/python scripts/fetch_espn.py      # ESPN -> data/espn/<CODE>/{league.json, weeks/N.json, trades.json}, data/espn/players.json
.venv/bin/python scripts/compute.py         # -> data/site/*.json (meta, leagues, people, standings, weekly, highs, records, power, trades)
.venv/bin/python -m pytest -q               # 20 tests
cd site && npm run build                    # -> site/dist (96 pages)
```
Local preview: `cd site && npm run dev` → http://localhost:4321/keystone-fantasy/ . Python venv at `.venv/` (3.14), Node 24, Astro 5.
`fetch_espn.py` needs `ESPN_S2` / `ESPN_SWID` in `.env` (git-ignored). Idempotent: completed weeks are skipped unless `--force`;
the in-progress week is always refetched; trades are refetched for every period (statuses change).

## Repo map
- `leagues.json` — season, 7 codes (EMP GOT BEA HAR ALC ALL C2C) → ESPN league ids + display names. C2C displays as **Freedom League**.
- `board.json` — Supabase URL + publishable key for the message board (public by design; blank = board hidden).
- `Starter Files/keystone_ff_2026_master.csv` — **editable source of truth** for people (key `Slot ID`). Committed WITHOUT email columns.
- `Starter Files/private/` (git-ignored) — full CSV with emails + JSON/XLSX copies. `map_teams.py` matches from it when present and writes both CSVs.
- `scripts/espn_client.py` — cookie-auth client (`league()`, `league_filtered()` with x-fantasy-filter), retries, loud AuthError on 401/403, raw cache to `data/raw/` (git-ignored).
- `scripts/espn_probe.py` — auth sanity check; prints teams/owners per league.
- `scripts/map_teams.py propose|apply` — slot ↔ ESPN team matching (done; re-run only for a new season or roster change).
- `scripts/fetch_espn.py` — league settings/teams/schedule, per-week matchups + lineups (bench/optimal), trades, player-name cache.
- `scripts/compute.py` — all derived data; strips emails (asserts none); attaches logos/icons; writes `data/site/`.
- `scripts/lib/records.py` — pure functions: standings, streaks, all-play luck, weekly highs, record book, playoff picture, power rank.
- `scripts/lib/lineup.py` — optimal lineup solver (+ brute-force reference for tests). `lib/trades.py` — transaction → trade normalization.
- `scripts/lib/icons.py` — emoji maps (hometown, fallbacks). `scripts/fetch_logos.py` — NFL/college/company PNGs → `site/public/logos/`, `data/logos.json`.
- `scripts/board_schema.sql` — Supabase table, one-level-reply trigger, rate limits, RLS (read + insert only).
- `site/src/lib/data.ts` — loads `data/site/*.json` at build; `u()` prefixes the `/keystone-fantasy` base path; formatters.
- `site/src/components/` — Layout (nav + ALL global CSS), TeamCell (team bold link + manager subtext + badges), ProfileBadges (college/NFL/company logos, hometown emoji, tooltips), StandingsTable, Matchups, RecordTable, ScoreChart (inline SVG), TradeCard, MessageBoard (client JS → Supabase REST).
- `site/src/pages/` — index, leagues/[code], people/[slug] (slug = slot id lowercased), weekly-highs, records, power, trades.
- `.github/workflows/refresh.yml` — cron + workflow_dispatch + push (paths-filtered). Fetch fails → no deploy. Bot commits `data/` with `[skip ci]`.
- `tests/` — fixture league with hand-computed answers; lineup vs brute force; icons; trades; site-data checks (no emails, standings == ESPN records).

## Data facts you must not re-derive wrong
- All 7 leagues: 12 teams, Half PPR, 4-pt pass TD, 14-week regular season, 6 playoff teams (top 2 byes). Identical scoring → raw points comparable.
- Commissioner ESPN account "Key Stone" (displayName `ESPNFAN1712906171`) holds team 1 in every league. GOT/ALC/ALL: commissioner's own team
  (slots GOT-12/ALC-12/ALL-12, Seat Type = League Manager, shown as "League Manager"). EMP/BEA/HAR/C2C: co-owned; the co-owner IS the owner
  (Cole EMP-08, Charlie Fairfax BEA-12, Ranmit Pantle HAR-08, Aseem Mahajan C2C-12) and `Manager Seat = Yes` only marks that.
- Name mismatches confirmed by Cole: ESPN "Jason Holtzman" = Sloane Winters Holtzman (GOT-08); "Ranmit Singh" = Ranmit Pantle (HAR-08); "Catherine Poirier" = Catherine Goel (ALC-03).
- ESPN API: base `https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/{season}/segments/0/leagues/{id}`. Views used: mSettings, mTeam,
  mMatchupScore, mBoxscore+mRoster (per scoringPeriodId), mTransactions2 (per scoringPeriodId — it only returns that period), kona_player_info (x-fantasy-filter filterIds).
  In-progress matchups have totalPoints=0; live score is `totalPointsLive`. Completed = all matchups in the period have winner != UNDECIDED.
- Trades: `TRADE_PROPOSAL` transactions with `TRADE` items (fromTeamId→toTeamId). Only status EXECUTED is published (Cole's call; pending/canceled never reach data/site).
- Luck = actual wins − all-play expected wins (each week: teams outscored / 11). Power = 0.6·norm(PPG) + 0.25·all-play% + 0.15·norm(last-3 PPG), ×100.
- Playoff picture (`playoff_picture` in records.py): clinched / in / bubble / out / eliminated; standings show only `x` (clinched) and `e` (eliminated).

## UI decisions (Cole's explicit choices — keep)
- TEAM NAME is the bold link everywhere; manager name + badges are subtext. Person page h1 = team name, "Managed by …" below.
- Standings tables: NO Luck column, NO Playoffs column. Gold dotted line under bye spots, blue dotted line under playoff cut, x/e marks by name.
- Home page: 7 league cards, stat tiles, cross-league power TOP 10 (not the weekly-highs leaderboard), then the message board.
- Badges: college logo (ESPN CDN; 4 schools via favicon), hometown emoji (country flag for international), NFL logo, company logo for alumni
  jobs outside Keystone (favicon; skipped when it equals home city or contains "Keystone"; skipped if it would duplicate the college crest).
  Hover/tap tooltip names each. Add a new school/company in `fetch_logos.py` maps, run it, commit the PNG.
- Light theme, minimal, mobile-first (tables scroll inside `.tbl-wrap`; `.hide-sm` hides low-priority columns under 640px).
- Deferred by Cole: office / NFL-team / college grouping pages ("maybe later"); commissioner seats keep the name "League Manager".

## Hard-won gotchas
- **CSS is inlined** (`inlineStylesheets: 'always'` in astro.config). External hashed CSS + frequent deploys + GitHub Pages 10-min cache → cached pages
  lost their stylesheet (2026-09-22). Do not change this.
- **Astro scoped styles don't apply to HTML injected at runtime.** MessageBoard uses `<style is:global>`; keep it that way for any client-rendered markup.
- Workflow `push` trigger is paths-filtered (`site/**`, `scripts/**`, `data/site/**`, `leagues.json`, `board.json`, the workflow). Editing only docs/CSV won't rebuild;
  run `import_master.py` + `compute.py` and commit `data/` or trigger the workflow manually.
- zsh globs `[code].astro` — quote those paths in shell commands.
- Headless Chrome on macOS won't go below ~500px wide; use CDP `Emulation.setDeviceMetricsOverride` for real mobile screenshots (script pattern in AGENT_LOG 2026-09-22).
- Emails: history was rewritten before the first push; nothing under `data/` or `site/` may ever contain an address (test enforces). Never commit `Starter Files/private/`.
- Supabase new-style key (`sb_publishable_…`) works in both `apikey` and `Authorization: Bearer` headers. DELETE via anon returns 204 but affects 0 rows (RLS) — expected.

## Operations
- Cookie expiry (`espn_s2`, weeks–months): workflow fails on 401/403 before deploy, GitHub emails Cole, site keeps last good data + shows footer timestamp
  (yellow banner after 8 days). Fix = README "Refreshing ESPN cookies" (update `.env` and the two repo secrets), re-run workflow.
- Manual refresh: Actions → "Refresh ESPN data and deploy site" → Run workflow. Or locally: fetch → compute → commit `data/` → push.
- Roster/profile edit: edit the private CSV (or committed one), `map_teams.py apply` if names changed, `import_master.py`, `compute.py`, commit, push.
- Message board moderation: Supabase project `nzafwnydzzzhckoerzad` → Table Editor → posts. First post ("Keystone Fantasy" welcome) was a test.
- New season: see README "Adding a new season later" (leagues.json season + ids, re-run probe/map_teams, clear data/espn + data/site).

## Status / open items (2026-09-22)
- Shipped. First unattended cron run is Fri 2026-09-25 11:00 UTC — worth checking Actions once.
- Week-3 "in progress" cards show 0.00 until Thursday night; Cole declined hiding them.
- ~60 members have blank profile fields (site hides them). Two rows have "Boston"/"BOS" as company (hidden by rule).
- Playoff bracket rendering (weeks 15–17) not yet built; matchups will appear as normal weeks with `playoff_tier != NONE`.
