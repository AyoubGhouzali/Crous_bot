# CROUS Monitor

Python bot polling the CROUS housing API for Clermont-Ferrand/Aubière.

- Entry point: `python -m src.main`
- Tests: `pytest`
- Manual notification test: `python -m src.notifier "test"`
- Secrets in `.env` (see `.env.example`). **ID_TOOL changes each CROUS phase** —
  find it in the site URL: `https://trouverunlogement.lescrous.fr/tools/<ID_TOOL>/search`

## API field mapping (from tests/fixtures/sample_response.json, captured 2026-07-09)

Endpoint: `POST https://trouverunlogement.lescrous.fr/api/fr/search/<ID_TOOL>`
(request `page` is 1-based; the response echoes a 0-based `results.page` —
pagination stops when a page returns fewer than `pageSize` items).

| Field           | Path                                    | Notes                          |
|-----------------|-----------------------------------------|--------------------------------|
| item id         | `item.id`                               | int, used for state diffing    |
| residence name  | `item.residence.label`                  |                                |
| address         | `item.residence.address`                | city + zip embedded in string  |
| rent            | `item.occupationModes[].rent.min`       | **in cents** (50102 = 501.02 €)|
| surface area    | `item.area.min` / `item.area.max`       | m²                             |
| booking link    | `/tools/<ID_TOOL>/accommodations/<id>`  | built, not in response         |

## Rules

- Never scan the full JSON for zips: rents in cents false-positive on 63000
  (e.g. 363000), and `residence.entity.name` / descriptions mention
  "Clermont Auvergne" for accommodations in Montluçon (see fixture item id=581).
  Only scan `residence.address`, `residence.label`, `item.label`.
- Never match bare "clermont" (Clermont-l'Hérault 34800 and Clermont 60600 exist).
- Matching is text (keywords incl. "clermont-fd", zips 63000/63100/63170/63178)
  OR geo: `residence.location` within TARGET_RADIUS_KM (default 10) of ISIMA
  (45.7590, 3.1110) — the geo net catches address spelling variants.
- First run seeds `state.json` silently — no alerts.
- State stores the *current* matched ID set each run, so a booked room that
  frees up again re-alerts.
- No auto-booking, notifications only. Poll every 5 min minimum, 1 s pause
  between pages.
