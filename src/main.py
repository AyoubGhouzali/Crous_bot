"""Orchestration: fetch -> filter -> diff -> notify -> save state.

Cron-friendly: always exits 0 (success) or 1 (failure), never raises.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from .config import ConfigError, load_config
from .fetcher import FetchError, fetch_all
from .filters import matches_target
from .notifier import format_message, send
from .state import diff_new, load_ids, save_ids

log = logging.getLogger(__name__)


def _setup_logging(log_file: str) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file, encoding="utf-8"),
        ],
    )


def run() -> int:
    try:
        cfg = load_config()
    except ConfigError as exc:
        # Logging isn't set up yet (log file name comes from config).
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 1

    _setup_logging(cfg.log_file)
    log.info("--- run start ---")
    try:
        items = fetch_all(cfg)
        matched = [item for item in items if matches_target(item)]

        state_path = Path(cfg.state_file)
        first_run = not state_path.exists()
        previous_ids = load_ids(state_path)
        new_items = diff_new(matched, previous_ids)

        if first_run:
            log.info("First run: seeding state with %d matched items, no alerts sent", len(matched))
        elif new_items:
            for item in new_items:
                sent = send(format_message(item, cfg), cfg)
                log.info(
                    "New accommodation id=%s (%s) — notification %s",
                    item["id"],
                    (item.get("residence") or {}).get("label", "?"),
                    "sent" if sent else "FAILED",
                )
        else:
            log.info("No new accommodations")

        # Save the *current* matched set (not a union) so an accommodation
        # that disappears (booked) and later reappears (freed) re-alerts.
        save_ids(state_path, {int(item["id"]) for item in matched})
        log.info("Counts: fetched=%d matched=%d new=%d", len(items), len(matched), len(new_items))
        log.info("--- run end (ok) ---")
        return 0
    except FetchError as exc:
        log.error("Fetch failed, state left untouched: %s", exc)
        log.info("--- run end (error) ---")
        return 1
    except Exception:
        log.exception("Unexpected error")
        log.info("--- run end (error) ---")
        return 1


if __name__ == "__main__":
    sys.exit(run())
