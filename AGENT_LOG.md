# Agent log — append a dated entry at the end of every session

## 2026-09-21 → 2026-09-22 — Claude Code (Fable 5.1), initial build and launch

**Phase 0–1.** Read the 84-row master file (7×12; 81 members + 3 League Manager seats; ESPN join keys blank; 8 manual-add rows with empty profiles).
Cole's answers: all leagues private; one ESPN account in all 7; track total/bench/optimal/player points; static Astro site on GitHub Pages;
Mon/Tue/Fri refresh on GitHub Actions cron; all pages; groupings deferred; light minimal theme; public, no emails. C2C renamed "Freedom League".
Wrote PLAN.md; approved. Verified ESPN v3 base URL unchanged; chose raw requests over `espn-api`.

**Phase 2.** Repo scaffold, `espn_client.py`, `espn_probe.py`. Cole pasted cookies into `.env` via TextEdit. Probe OK for all 7 leagues:
Half PPR, 14 weeks, 6 playoff teams, week 1 complete at the time.

**Phase 3.** `map_teams.py` (name/email/display-name scoring; fixed a bug where an owner's real-name display matched every slot). 84/84 matched;
Cole confirmed 3 surname mismatches; Manager Seat flags moved to the ESPN co-owners; 7 first-name-only people got surnames from ESPN.

**Phase 4.** `fetch_espn.py` (live totals for in-progress weeks), `lib/records.py`, `lib/lineup.py`, `compute.py`, 15 tests (fixture answers were
hand-miscomputed at first — team 3 lost week 2 — fixed). Astro site, 95 pages. Workflow (cron 11:00 UTC Mon/Tue/Fri, dispatch, push), README.
Emails: Cole chose a public repo with a sanitized CSV → moved email-bearing files to `Starter Files/private/`, rewrote git history with
filter-branch (also replaced an early `data/master.json` that had emails), verified zero addresses in history. Created repo, set secrets via `gh`,
enabled Pages, first run green.

**Phase 5.** Cole verified Gotham standings + week 2 scores vs the ESPN app: match.

**Post-launch iterations (same day), all shipped:**
1. Team-first naming (TeamCell), Luck removed from standings tables, emoji icons for city/college/NFL.
2. Real NFL + college logos (`fetch_logos.py`, ESPN combiner at 96px; favicon fallback for Brandeis/Vassar/WPI/Alberta), tooltips (`ProfileBadges`).
   Investigated a suspected mobile overflow → was headless Chrome's minimum window width; verified via CDP device emulation (scrollWidth == innerWidth).
3. Company logos for alumni working outside Keystone (16 employers; Twee Capital at twee.capital; skip Keystone/city values; no duplicate crest).
4. Standings: bye + playoff dotted lines, x/e marks, Playoffs column removed.
5. **Incident:** Cole saw "massive logos, weird links" on some league pages → cached HTML referencing a deleted hashed CSS file (5 deploys in 2 h,
   Pages max-age=600). Fix: `inlineStylesheets: 'always'`. The fix itself broke the *remaining* cached pages once; hard refresh cleared it.
6. Home page: power top 10 instead of weekly-highs leaderboard.
7. Message board: Supabase (Cole created project, ran `scripts/board_schema.sql`, gave URL + publishable key). Board hidden until `board.json` filled;
   added `board.json` to workflow push paths; switched board styles to `is:global` (runtime-rendered posts were unstyled). Welcome post = insert test.
8. Trade center: `mTransactions2` per scoring period, `lib/trades.py`, `kona_player_info` name cache, `/trades/` + person-page trades, 3 tests.
   Then per Cole: pending/canceled proposals removed from the page AND from published data.
9. Pre-launch check: all URLs 200, no emails, noindex, secrets set, 20 tests. Cole declined two optional polish items and shipped.

**Tools/patterns worth reusing:** CDP screenshot script (`scratchpad/shot.mjs`: launch Chrome `--headless=new --remote-debugging-port=9222`,
`Emulation.setDeviceMetricsOverride`, `Page.captureScreenshot`); `gh run watch <id> --exit-status`; `git filter-branch --index-filter` for history scrubs.

## 2026-09-29 — Claude Code (Fable 5.1), rosters and matchup box scores

Cole asked: clicking a team shows its roster; clicking a matchup shows the players in it.
- `fetch_espn.py`: lineup players now carry `pro_team`. Ran `fetch_espn.py --force` once locally so weeks 1–3 have it too (scores unchanged).
- `lib/lineup.py::display_lineup` + `compute.py::public_lineup` → new `data/site/lineups.json` (code → week → team id → starters/bench/ir, ~0.6 MB at week 4).
  Matchups got a `key`, person week records a `matchup_key`, people a `roster_week`.
- Site: `Roster.astro`, `PlayerCell.astro`, `pages/matchups/[key].astro` (168 new pages, 264 total); matchup cards clickable; game log links to lineups.
- Tests 20 → 22 (display order/empty slots; every matchup's starters sum to its score — 336/336 team-weeks match).
- Verified with CDP screenshots at 1100px and 375px (no horizontal overflow). Fixed totals wrapping in the narrow points column.

**Monday Night Sweats (same session).** Cole: 5 closest matchups across leagues heading into Monday, by ESPN win probability, skip matchups where the
trailing team has nobody left, score-bug visual with lead + remaining players.
- Found `winProbability` + `totalProjectedPointsLive` on each side of the *current* matchup period in mMatchupScore/mBoxscore (absent for past periods),
  per-player projections in `stats[statSourceId=1]`, kickoffs in the public season view `proTeamSchedules_wl`.
- `espn_client.season_view`, `fetch_espn.norm_pro_schedule` / `projected_points`; `lib/sweats.py` (+4 tests); `compute.sweat_candidates`;
  `MondaySweats.astro` on the home page. Snapshot semantics documented in CLAUDE.md.
- Verified visually with a *simulated* week-3 snapshot (MNF players zeroed, projection := actual) — deleted before commit; the real one arrives Mon Oct 5.
- Cole: verify live on Sunday night 2026-10-04; until then the home page shows a 'Coming Monday morning' skeleton card. Shipped 2026-09-29.
- Then: Sweats moved to its own tab (`/sweats/`, nav after Trades); home page leads with the top-10 scores of the last completed week.

## 2026-10-05 — Claude Code (Fable 5.1), first real Monday Night Sweats snapshot

Cole: dashboard had not refreshed to create the sweats. Nothing was broken — the Mon 11:00 UTC cron had not fired yet at 13:36 UTC.
- GitHub starts this schedule 4.5–7.5 h late every time (last four runs: 15:43, 18:23, 16:46, 16:28 UTC). Triggered `workflow_dispatch` by hand
  (run 37318197652, success) → `data/site/sweats.json` created: week 4, as of 13:37 UTC, 5 picks from 42 undecided matchups, `/sweats/` live.
- ESPN `winProbability` IS live (not pregame): it tracks our `est_win_prob` within ~5 points on all 5 picks (e.g. 0.30 vs 0.342, 0.91 vs 0.908). Keep `win_prob` = ESPN.
- Open: cron lateness. The late run still lands in the window (MNF kicks off ~00:15 UTC Tue) but Cole sees an empty tab Monday morning.
  Fixed same session: cron moved to `17 9 * * 1,2,5` (early + off the hour).
- Sweats card tweaks (Cole): remaining players show name + projection only (no position / NFL team / opponent / kickoff); the lead moved out of
  the dark score rows into the "left to play" list as a "Current lead +x.x pts" line on the leader's side.

## 2026-10-06 — Claude Code (Fable 5.1), manager profile links + headshots

Cole: manager names link to keystone.com (current) or LinkedIn (alumni); team page shows a small headshot. He uploaded
`Starter Files/private/names and linkedin .xlsx` (19 alumni: Name, Link, pasted photo).
- keystone.com/our-people is a Webflow list: 299 cards, each `/our-people/<slug>` + headshot with a `-p-500` srcset rendition. Scraped with regex.
- Name matching: exact → nickname table + exact last name → difflib ≥0.88. Took keystone.com matches from 41 (plain slug) to 48; caught
  Chris/Christopher, Zach/Zachary, Michael H. Gary, "Karthik Hemmanur" (site) vs "Karthick Hemmanuer" (CSV), "Iakdawala"/"lakdawala" (spreadsheet typo).
- Spreadsheet pictures: openpyxl loads none without Pillow and anchor handling is flaky, so pictures come straight from `xl/media` via
  `xl/drawings/drawing1.xml` anchors; a `from` rowOff past ~half a row means the picture sits in the NEXT row (Excel writes it that way).
  18 photos → 18 rows, no collisions. Cuau Trevino has a link but no photo.
- Result: 48 Keystone + 18 LinkedIn = 66 of 81 members linked; 65 headshots (504 KB total). 15 members with neither — list sent to Cole.
  Justin Metz is in the spreadsheet AND on keystone.com → Keystone wins (per Cole's rule 3).
- Site: `Owner.astro` replaces every `{x.owner}`; `.mu .team a` z-index already lifts it above the stretched matchup `.box-link`.
  Person page header is now photo + h1 + "Managed by <link>". Test added: links only keystone.com/linkedin.com, every photo file exists.
