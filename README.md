# Keystone Fantasy Football 2026

Standings, weekly high scores, a record book and a cross-league power ranking for the seven
Keystone ESPN fantasy leagues. Static site on GitHub Pages, refreshed from ESPN by a
GitHub Actions job three mornings a week (Mon / Tue / Fri, 11:00 UTC).

Design and decisions: `PLAN.md`. Notes for future Claude sessions: `CLAUDE.md`.

## How it fits together

```
Starter Files/keystone_ff_2026_master.csv   <- you edit this (people, profiles, ESPN team ids)
leagues.json                                <- league codes -> ESPN league ids (not secret)
.env / GitHub Secrets                       <- ESPN_S2, ESPN_SWID cookies (secret)

scripts/import_master.py   CSV -> data/master.json       (emails dropped)
scripts/fetch_espn.py      ESPN -> data/espn/<CODE>/...  (raw copies in data/raw/, git-ignored)
scripts/compute.py         -> data/site/*.json           (what the pages read)
site/  (Astro)             -> site/dist                  (deployed to GitHub Pages)
```

## One-time setup (already done locally)

```
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env            # then paste the two cookies, see below
cd site && npm install
```

## Refreshing ESPN cookies

Needed on first setup and again whenever the scheduled job fails with HTTP 401/403 (GitHub
emails you when a run fails). `espn_s2` expires every few weeks to months.

1. In Chrome, log in at https://fantasy.espn.com and open any of the leagues.
2. Open DevTools: `Cmd+Option+I` (Mac) or `Ctrl+Shift+I` (Windows).
3. Click the **Application** tab (behind the `»` arrow if it's hidden).
4. Left sidebar: **Storage → Cookies → https://fantasy.espn.com**.
5. Filter for `espn_s2`, double-click its **Value**, select all, copy. It is a few hundred characters long.
6. Filter for `SWID`, copy its value **including the curly braces**: `{XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX}`.
7. **Locally:** open `.env` and set `ESPN_S2=` and `ESPN_SWID=` (no quotes). Check with
   `.venv/bin/python scripts/espn_probe.py` — it should end with "All leagues OK."
8. **For the scheduled job:** GitHub repo → **Settings → Secrets and variables → Actions**.
   Click the existing `ESPN_S2` secret → **Update** → paste → Save. Same for `ESPN_SWID`.
   (First time: **New repository secret** for each.) The workflow reads them as
   `${{ secrets.ESPN_S2 }}` and `${{ secrets.ESPN_SWID }}`; nothing else needs to change.
9. Re-run the job: **Actions → Refresh ESPN data and deploy site → Run workflow**.

The site keeps the last good data and shows its timestamp in the footer (with a yellow
banner if it is more than 8 days old), so a broken cookie never publishes wrong numbers.

## Everyday tasks

**Manual refresh right now:** GitHub → **Actions** tab → "Refresh ESPN data and deploy site"
→ **Run workflow** → green button. Takes about 2 minutes. Or locally:

```
.venv/bin/python scripts/fetch_espn.py && .venv/bin/python scripts/compute.py
cd site && npm run dev        # preview at http://localhost:4321/keystone-fantasy/
```

**Fix a name / profile / team assignment:** edit `Starter Files/keystone_ff_2026_master.csv`
in Excel or Numbers (keep the header row and Slot IDs), save as CSV, then:

```
.venv/bin/python scripts/import_master.py     # validates; prints any problem rows
.venv/bin/python scripts/compute.py
git add -A && git commit -m "roster: fix ..." && git push
```

The push rebuilds the site from the committed data (no ESPN call needed). If you change an
`ESPN Team ID`, the next scheduled run re-attributes that team's scores.

**Someone new joins mid-season:** add a row with the next free Slot ID for that league,
fill Display Name / First / Last / Seat Type = Member, and the `ESPN Team ID` from
`.venv/bin/python scripts/espn_probe.py` (it lists every team id and owner per league).

**Rename a league:** change `name` in `leagues.json` (the code and Slot IDs stay the same).

**Force a full re-fetch** (e.g. after ESPN stat corrections): `scripts/fetch_espn.py --force`.

## Adding a new season later

1. Copy the master CSV to a new file for the season, clear the three `ESPN ...` columns,
   update rosters. Point `MASTER_CSV` in `scripts/import_master.py` / `map_teams.py` at it
   (or keep the same filename and archive the old one).
2. Set `"season"` and the new ESPN league ids in `leagues.json`.
3. Run `espn_probe.py`, then `map_teams.py propose`, review `data/team_mapping.json`,
   then `map_teams.py apply`.
4. Delete `data/espn/` and `data/site/`, run `fetch_espn.py` + `compute.py`, commit, push.
5. Update the year in `site/src/components/Layout.astro` and `README.md`.

## Tests

```
.venv/bin/python -m pytest -q
```

Covers standings, streaks, all-play luck, record book, playoff flags, the optimal-lineup
solver (against brute force), that no email address reaches `data/site/`, and that our
computed standings agree with ESPN's own W-L and points for every team.
