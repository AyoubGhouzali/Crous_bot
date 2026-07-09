"""Paginated client for the CROUS accommodation search API."""

from __future__ import annotations

import logging
import time

import requests

from .config import FRANCE_BOUNDS, BASE_URL, Config

log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "application/ld+json, application/json",
    "Content-Type": "application/json",
    "Origin": BASE_URL,
}


class FetchError(Exception):
    """All retries exhausted, or the API answered with a non-retryable error."""


def _build_payload(cfg: Config, page: int) -> dict:
    # Mirrors the payload sent by the site's own frontend (captured 2026-07-09).
    return {
        "idTool": int(cfg.id_tool),
        "need_aggregation": False,
        "page": page,
        "pageSize": cfg.page_size,
        "sector": None,
        "occupationModes": [],
        "location": FRANCE_BOUNDS,
        "residence": None,
        "precision": 3,
        "equipment": [],
        "adaptedPmr": False,
        "price": {"max": 10000000},
        "area": {"min": 0},
        "toolMechanism": "residual",
    }


def _post_page(cfg: Config, page: int) -> dict:
    """POST one page, retrying on transient failures. Raises FetchError."""
    referer = f"{BASE_URL}/tools/{cfg.id_tool}/search"
    headers = {**HEADERS, "Referer": referer}
    attempts = len(cfg.retry_delays)
    last_error: str = ""

    for attempt in range(attempts):
        try:
            response = requests.post(
                cfg.api_url,
                json=_build_payload(cfg, page),
                headers=headers,
                timeout=cfg.request_timeout,
            )
            if response.status_code >= 500:
                last_error = f"HTTP {response.status_code}"
            elif response.status_code >= 400:
                raise FetchError(
                    f"API rejected request (HTTP {response.status_code}) for page {page}; "
                    f"check that ID_TOOL={cfg.id_tool} is the current tour d'affectation."
                )
            else:
                try:
                    return response.json()
                except ValueError:
                    last_error = "malformed JSON in response"
        except (requests.Timeout, requests.ConnectionError) as exc:
            last_error = f"{type(exc).__name__}: {exc}"

        if attempt < attempts - 1:
            delay = cfg.retry_delays[attempt]
            log.warning(
                "Fetch page %d failed (%s), retrying in %.0fs (attempt %d/%d)",
                page, last_error, delay, attempt + 1, attempts,
            )
            time.sleep(delay)

    raise FetchError(f"Failed to fetch page {page} after {attempts} attempts: {last_error}")


def fetch_all(cfg: Config) -> list[dict]:
    """Fetch every accommodation, page by page. Raises FetchError on failure."""
    items: list[dict] = []
    for page in range(1, cfg.max_pages + 1):
        data = _post_page(cfg, page)
        page_items = data.get("results", {}).get("items", [])
        items.extend(page_items)
        log.debug("Page %d: %d items", page, len(page_items))
        if len(page_items) < cfg.page_size:
            return items
        time.sleep(cfg.page_pause)

    log.warning("Stopped at MAX_PAGES=%d; results may be truncated", cfg.max_pages)
    return items
