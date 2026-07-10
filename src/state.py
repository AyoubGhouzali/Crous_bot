"""Persist the set of already-seen accommodation IDs (and heartbeat
timestamp) between runs."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger(__name__)


def _empty_state() -> dict:
    return {"ids": set(), "last_heartbeat": None}


def load_state(path: str | Path) -> dict:
    """Read state: {"ids": set[int], "last_heartbeat": datetime|None}.

    Missing or corrupt file -> empty state (warned).
    """
    path = Path(path)
    if not path.exists():
        return _empty_state()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        state = {"ids": {int(x) for x in data["ids"]}, "last_heartbeat": None}
        if raw := data.get("last_heartbeat"):
            heartbeat = datetime.fromisoformat(raw)
            if heartbeat.tzinfo is None:
                heartbeat = heartbeat.replace(tzinfo=timezone.utc)
            state["last_heartbeat"] = heartbeat
        return state
    except (ValueError, KeyError, TypeError) as exc:
        log.warning("State file %s is corrupt (%s); treating as empty", path, exc)
        return _empty_state()


def save_state(path: str | Path, ids: set[int], last_heartbeat: datetime | None = None) -> None:
    """Atomically write the state (tmp file + rename)."""
    path = Path(path)
    payload: dict = {"ids": sorted(ids)}
    if last_heartbeat is not None:
        payload["last_heartbeat"] = last_heartbeat.isoformat()
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def diff_new(items: list[dict], previous_ids: set[int]) -> list[dict]:
    """Return the items whose IDs were not seen in the previous run."""
    return [item for item in items if int(item["id"]) not in previous_ids]
