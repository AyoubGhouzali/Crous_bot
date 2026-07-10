"""End-of-job summary ("bilan") message.

The GitHub Actions job runs many 5-minute monitor cycles back to back;
when RUN_STATS_FILE is set, each cycle appends one JSON line to it. At the
end of the job `python -m src.bilan` turns those lines into a single
Telegram summary — the hourly "still alive" signal with observability.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime
from pathlib import Path

from .config import load_config
from .notifier import send

log = logging.getLogger(__name__)


def append_stats(path: str | Path, record: dict) -> None:
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    except OSError as exc:
        log.warning("Could not append run stats to %s: %s", path, exc)


def load_stats(path: str | Path) -> list[dict]:
    path = Path(path)
    if not path.exists():
        return []
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except ValueError:
            log.warning("Skipping bad stats line: %r", line[:100])
    return records


def _fmt_time(iso: str) -> str:
    dt = datetime.fromisoformat(iso)
    try:
        from zoneinfo import ZoneInfo

        return dt.astimezone(ZoneInfo("Europe/Paris")).strftime("%H:%M")
    except Exception:
        return dt.strftime("%H:%M UTC")


def compose_bilan(records: list[dict]) -> str:
    if not records:
        return (
            "📊 Bilan — monitor actif, mais aucun cycle enregistré. "
            "Vérifiez les logs dans l'onglet Actions."
        )
    ok_records = [r for r in records if r.get("ok")]
    failures = len(records) - len(ok_records)
    new_total = sum(r.get("new", 0) for r in records)

    lines = [
        "📊 Bilan horaire — monitor actif (message de routine, PAS une alerte)",
        f"Période : {_fmt_time(records[0]['ts'])} → {_fmt_time(records[-1]['ts'])} (heure de Paris)",
    ]
    if failures:
        lines.append(f"Cycles : {len(records)} dont ⚠️ {failures} en échec")
    else:
        lines.append(f"Cycles : {len(records)} ✅")
    if ok_records:
        last = ok_records[-1]
        lines.append(
            f"Logements en ligne : {last.get('fetched', '?')} · "
            f"à Clermont-Fd/Aubière : {last.get('matched', '?')}"
        )
    if new_total:
        lines.append(f"🚨 {new_total} alerte(s) logement envoyée(s) pendant ce run !")
    else:
        lines.append("Nouvelles alertes : 0")
    lines.append("Prochain bilan dans ~1 h — s'il cesse d'arriver, vérifiez l'onglet Actions.")
    return "\n".join(lines)


def main() -> int:
    logging.basicConfig(level=logging.INFO)
    cfg = load_config()
    if not cfg.run_stats_file:
        log.error("RUN_STATS_FILE is not set; nothing to summarize")
        return 1
    records = load_stats(cfg.run_stats_file)
    text = compose_bilan(records)
    sent = send(text, cfg)
    Path(cfg.run_stats_file).unlink(missing_ok=True)
    return 0 if sent else 1


if __name__ == "__main__":
    sys.exit(main())
