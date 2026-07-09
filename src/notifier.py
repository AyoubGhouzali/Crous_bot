"""Telegram / Discord notification senders.

Manual test: python -m src.notifier "hello"
"""

from __future__ import annotations

import logging
import sys

import requests

from .config import Config, load_config

log = logging.getLogger(__name__)

SEND_TIMEOUT = 15


def _min_rent_cents(item: dict) -> int | None:
    rents = [
        mode["rent"]["min"]
        for mode in item.get("occupationModes", [])
        if mode.get("rent", {}).get("min") is not None
    ]
    return min(rents) if rents else None


def _format_area(item: dict) -> str:
    area = item.get("area") or {}
    lo, hi = area.get("min"), area.get("max")
    if lo is None:
        return "surface inconnue"
    if hi is None or hi == lo:
        return f"{lo:g} m²"
    return f"{lo:g}–{hi:g} m²"


def format_message(item: dict, cfg: Config) -> str:
    residence = item.get("residence") or {}
    name = f"{residence.get('label', '?')} — {item.get('label', '?')}"
    address = residence.get("address", "adresse inconnue")
    rent_cents = _min_rent_cents(item)
    rent = f"{rent_cents / 100:.2f} €/mois" if rent_cents is not None else "loyer inconnu"
    link = cfg.accommodation_url(item["id"])
    return (
        f"🏠 Nouveau logement CROUS !\n"
        f"{name}\n"
        f"📍 {address}\n"
        f"💶 {rent} — 📐 {_format_area(item)}\n"
        f"👉 {link}"
    )


def send_telegram(text: str, cfg: Config) -> bool:
    url = f"https://api.telegram.org/bot{cfg.telegram_bot_token}/sendMessage"
    try:
        response = requests.post(
            url,
            json={"chat_id": cfg.telegram_chat_id, "text": text},
            timeout=SEND_TIMEOUT,
        )
        if response.status_code != 200:
            log.error("Telegram send failed: HTTP %d %s", response.status_code, response.text[:200])
            return False
        return True
    except requests.RequestException as exc:
        log.error("Telegram send failed: %s", exc)
        return False


def send_discord(text: str, cfg: Config) -> bool:
    try:
        response = requests.post(
            cfg.discord_webhook_url,
            json={"content": text},
            timeout=SEND_TIMEOUT,
        )
        if response.status_code >= 300:
            log.error("Discord send failed: HTTP %d %s", response.status_code, response.text[:200])
            return False
        return True
    except requests.RequestException as exc:
        log.error("Discord send failed: %s", exc)
        return False


def send(text: str, cfg: Config) -> bool:
    """Dispatch to the configured notifier(s). Logs failures, never raises."""
    ok = True
    if cfg.notifier in ("telegram", "both"):
        ok = send_telegram(text, cfg) and ok
    if cfg.notifier in ("discord", "both"):
        ok = send_discord(text, cfg) and ok
    return ok


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    message = sys.argv[1] if len(sys.argv) > 1 else "Test message from CROUS monitor"
    config = load_config()
    sys.exit(0 if send(message, config) else 1)
