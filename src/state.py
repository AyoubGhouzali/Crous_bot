"""Persist the set of already-seen accommodation IDs between runs."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

log = logging.getLogger(__name__)


def load_ids(path: str | Path) -> set[int]:
    """Read the saved ID set. Missing or corrupt file -> empty set (warned)."""
    path = Path(path)
    if not path.exists():
        return set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return {int(x) for x in data["ids"]}
    except (ValueError, KeyError, TypeError) as exc:
        log.warning("State file %s is corrupt (%s); treating as empty", path, exc)
        return set()


def save_ids(path: str | Path, ids: set[int]) -> None:
    """Atomically write the ID set (tmp file + rename)."""
    path = Path(path)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps({"ids": sorted(ids)}, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def diff_new(items: list[dict], previous_ids: set[int]) -> list[dict]:
    """Return the items whose IDs were not seen in the previous run."""
    return [item for item in items if int(item["id"]) not in previous_ids]
