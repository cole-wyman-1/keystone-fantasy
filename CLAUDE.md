# Keystone Fantasy Football 2026 — project notes for Claude

Read PLAN.md first; it is the approved design. This file is the running state.

## What this is
Static site (Astro, GitHub Pages) for 7 private ESPN fantasy leagues (84 slots, 81 people +
3 commissioner seats). Python scripts pull ESPN scores on a GitHub Actions cron
(Mon/Tue/Fri 11:00 UTC), compute standings/records, and rebuild the site.

## Layout
- `Starter Files/keystone_ff_2026_master.csv` — editable source of truth for people/slots.
  Key = `Slot ID`. The JSON/XLSX beside it are copies of the same data.
- `leagues.json` — season + league codes → ESPN league ids + display names. Not secret.
- `scripts/espn_client.py` — cookie-auth client, retries, raw caching to `data/raw/`.
- `scripts/espn_probe.py` — prints league name/teams/owners/current week per league.
- `data/raw/` (git-ignored) verbatim ESPN JSON; `data/espn/` normalized; `data/site/` for Astro.
- `site/` — Astro project (Phase 4).
- `.github/workflows/refresh.yml` — scheduled fetch → compute → build → deploy (Phase 4).

## How to run
```
.venv/bin/pip install -r requirements.txt      # once
cp .env.example .env                           # then paste ESPN_S2 / ESPN_SWID
.venv/bin/python scripts/espn_probe.py         # sanity-check auth + list teams
```

## Decisions (keep in sync with PLAN.md)
- All leagues private; single ESPN account; cookies from `.env` locally, GitHub Secrets in CI.
- Raw `requests` against `lm-api-reads.fantasy.espn.com/apis/v3/games/ffl` (verified 2026-09-21),
  not the `espn-api` package.
- C2C league renamed to **Freedom League**; code `C2C` and Slot IDs unchanged.
- Emails live only in the master CSV / `data/master.json`; never in `data/site/` or HTML.
- Tracks total, bench, optimal-lineup, and single-player points.
- Luck = actual wins − all-play expected wins. Power ranking uses within-league z-scores.
- Cron 11:00 UTC (7am EDT / 6am EST) Mon, Tue, Fri + manual dispatch. Fetch failure = no deploy.

## Phase status
- [x] Phase 0/1: plan approved 2026-09-21
- [ ] Phase 2: cookies + probe (in progress)
- [ ] Phase 3: map slots ↔ ESPN teams
- [ ] Phase 4: fetch, compute, site, workflow, README
- [ ] Phase 5: verify vs ESPN app
