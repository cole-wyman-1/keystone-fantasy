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
