# Keystone Fantasy Football 2026

Site + record book for the 7 Keystone ESPN fantasy leagues. See PLAN.md for design.

## Refreshing ESPN cookies (needed on first setup and whenever the job fails with 401/403)
1. In Chrome, log in at https://fantasy.espn.com and open any of the leagues.
2. Open DevTools: `Cmd+Option+I` (Mac) or `Ctrl+Shift+I` (Windows).
3. Click the **Application** tab (if hidden, click the `»` overflow arrow to find it).
4. Left sidebar → **Storage → Cookies → https://fantasy.espn.com** (or https://www.espn.com).
5. In the filter box type `espn_s2`. Double-click the **Value** cell, copy it (long string, ~300+ chars).
6. Clear the filter, type `SWID`. Copy its value. It must keep the curly braces: `{XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX}`.
7. Locally: copy `.env.example` to `.env` and paste both values after the `=` (no quotes).
8. For the scheduled job: GitHub repo → **Settings → Secrets and variables → Actions → New repository secret**.
   Create `ESPN_S2` and `ESPN_SWID` with the same values.

`espn_s2` expires every few weeks to months. When the GitHub Action starts failing (you get an
email), repeat steps 1–8. The site keeps showing the last good data with its timestamp until then.

## Local commands
```
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/espn_probe.py      # check auth, list teams per league
```
