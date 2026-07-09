# CROUS Housing Monitor — Implementation Plan

Goal: a 24/7 bot that polls the internal API of trouverunlogement.lescrous.fr,
filters for Clermont-Ferrand / Aubière (city names, accent-insensitive, or zip
codes 63000/63170), diffs against previous state, and sends a Telegram alert
for every new accommodation. Runs via cron every 5 minutes.

## Repo structure

```
crous-monitor/
├── CLAUDE.md                  # context for Claude Code
├── PLAN.md                    # this file
├── .env.example               # template for secrets
├── .gitignore                 # .env, state.json, *.log, __pycache__
├── requirements.txt           # requests, python-dotenv
├── requirements-dev.txt       # + pytest
├── src/
│   ├── __init__.py
│   ├── config.py              # loads .env + constants (zips, keywords, timeouts)
│   ├── fetcher.py             # paginated API client, retries/backoff
│   ├── filters.py             # normalize(), matches_target()
│   ├── state.py               # load/save/diff state.json (atomic writes)
│   ├── notifier.py            # Telegram + Discord senders
│   └── main.py                # orchestration, entry point
├── tests/
│   ├── fixtures/
│   │   └── sample_response.json   # real captured API response
│   ├── test_filters.py
│   ├── test_state.py
│   └── test_fetcher.py        # mocked requests
└── deploy/
    ├── crontab.txt            # the exact cron line
    └── setup_vps.sh           # idempotent VPS bootstrap script
```

## Phases

- [x] Phase 0 — Discovery: capture POST /api/fr/search/<idTool>, save fixture,
      document field mapping in CLAUDE.md. idTool goes in .env, not code.
- [x] Phase 1 — Config & secrets: .env via python-dotenv, fail fast on missing
      vars, target keywords/zips as code constants.
- [x] Phase 2 — Fetcher: France-wide bbox payload, pagination (MAX_PAGES=20,
      1 s pause), 3 retries with 5s→10s→20s backoff, browser-like headers,
      single FetchError after exhausting retries.
- [x] Phase 3 — Filtering: normalize() strips accents+lowercases;
      matches_target() checks keywords OR zips on address/label fields only;
      no bare "clermont".
- [x] Phase 4 — State & diffing: atomic writes, corrupt file → empty with
      warning, first run seeds silently.
- [x] Phase 5 — Notifications: Telegram/Discord, price converted from cents,
      direct booking link, failures logged never raised,
      `python -m src.notifier "test"` manual test.
- [x] Phase 6 — Orchestration & logging: exit 0/1, monitor.log + stdout,
      run start/end markers, fetched/matched/new counts.
- [ ] Phase 7 — Deployment: deploy/setup_vps.sh + deploy/crontab.txt
      (`*/5 * * * * cd /opt/crous-monitor && ./venv/bin/python -m src.main >> monitor.log 2>&1`).

## Constraints

- Poll frequency: 5 min minimum. Never hammer the API; 1 s between pages.
- Notifier only — NO auto-booking. Booking stays manual.
- Secrets never committed. idTool treated as config (changes each phase).
- Python 3.10+, only deps: requests, python-dotenv, pytest (dev).
