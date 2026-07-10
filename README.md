# CROUS Monitor

Telegram bot that watches [trouverunlogement.lescrous.fr](https://trouverunlogement.lescrous.fr)
and alerts when a CROUS accommodation becomes available in **Clermont-Ferrand
or Aubière** (city names, accent-insensitive, or zip codes 63000/63170).

Notifications only — booking stays manual.

## How it works

Every run: fetch all accommodations (paginated POST to the internal search
API) → filter to the target area → diff against the IDs seen last run
(`state.json`) → send one Telegram/Discord message per new accommodation →
save the current ID set.

- The very first run seeds `state.json` silently (no alert flood).
- A room that gets booked (disappears) and later frees up (reappears)
  alerts again, because state stores the *current* matched set.
- Filters only scan `residence.address`, `residence.label` and `item.label` —
  never the whole JSON. Rents are stored in cents (363000 would false-positive
  on zip 63000) and descriptions mention "Clermont" for residences that are
  actually in Montluçon.

## Deployment (GitHub Actions — already set up)

`.github/workflows/monitor.yml` runs every 5 minutes (GitHub's scheduler
drifts to 5–15 min in practice). `state.json` is persisted between runs with
`actions/cache`.

Repository → Settings → Secrets and variables → Actions:

| Name                 | Type            | Value                                    |
|----------------------|-----------------|------------------------------------------|
| `TELEGRAM_BOT_TOKEN` | Secret          | from @BotFather                          |
| `TELEGRAM_CHAT_ID`   | Secret          | your numeric user id (see below)         |
| `ID_TOOL`            | Secret or Variable | current tour d'affectation (e.g. `47`) |

Trigger a manual run from the Actions tab ("Run workflow") to test.

> **Note:** GitHub disables scheduled workflows after 60 days without repo
> activity — it emails a warning; any push or one click re-enables it.

## Maintenance: new CROUS phase = new ID_TOOL

Each "tour d'affectation" has its own `ID_TOOL`. When a phase ends, alerts
stop (the API returns 4xx and the log says to check ID_TOOL). Find the new
value in the site URL — `https://trouverunlogement.lescrous.fr/tools/<ID_TOOL>/search` —
and update the `ID_TOOL` secret/variable. Nothing else changes.

## Telegram credentials

1. **Token**: talk to [@BotFather](https://t.me/BotFather) → `/newbot` →
   copy the HTTP API token.
2. **Chat ID**: send your new bot a message first (bots can't initiate),
   then open `https://api.telegram.org/bot<TOKEN>/getUpdates` and read
   `"chat":{"id":…}`. Shortcut: message [@userinfobot](https://t.me/userinfobot),
   it replies with your id (same number for a private chat with your bot).
3. Verify: `https://api.telegram.org/bot<TOKEN>/sendMessage?chat_id=<ID>&text=test`
   must deliver a message.

## Running locally

```bash
pip install -r requirements.txt
cp .env.example .env       # fill in ID_TOOL + Telegram credentials
python -m src.main         # one poll cycle (first run seeds silently)
python -m src.notifier "hello"   # test the Telegram channel
```

Logs go to stdout and `monitor.log`. Exit code 0/1, cron-friendly:

```cron
*/5 * * * * cd /path/to/crous-monitor && python -m src.main >> monitor.log 2>&1
```

## Development

```bash
pip install -r requirements-dev.txt
pytest
```

`tests/fixtures/sample_response.json` is a real captured API response
(2026-07-09, idTool 47); the exact field mapping is documented in
[CLAUDE.md](CLAUDE.md). Item id=581 (Montluçon) is the regression case for
the "Clermont Auvergne" false-positive trap.
