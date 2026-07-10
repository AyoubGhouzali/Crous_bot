"""Configuration: secrets from .env, filtering/fetching constants in code."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

# Target-area constants. These are business rules, not deployment config,
# so they live in code rather than in .env.
TARGET_CITY_KEYWORDS = frozenset({"clermont-ferrand", "clermont ferrand", "aubiere"})
TARGET_ZIP_CODES = frozenset({"63000", "63170"})

BASE_URL = "https://trouverunlogement.lescrous.fr"

# France-wide bounding box, as sent by the site's own frontend.
FRANCE_BOUNDS = [
    {"lon": -9.9079, "lat": 51.7087},
    {"lon": 14.3224, "lat": 40.5721},
]


class ConfigError(Exception):
    """A required environment variable is missing or invalid."""


@dataclass
class Config:
    id_tool: str
    notifier: str = "telegram"  # "telegram", "discord" or "both"
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    discord_webhook_url: str = ""
    page_size: int = 24
    max_pages: int = 20
    page_pause: float = 1.0
    request_timeout: float = 30.0
    retry_delays: tuple[float, ...] = (5.0, 10.0, 20.0)
    heartbeat_hours: float = 1.0  # 0 disables the periodic "still alive" message
    run_stats_file: str = ""  # when set, each run appends a JSONL stats record (for src.bilan)
    state_file: str = "state.json"
    log_file: str = "monitor.log"

    @property
    def api_url(self) -> str:
        return f"{BASE_URL}/api/fr/search/{self.id_tool}"

    def accommodation_url(self, item_id: int) -> str:
        return f"{BASE_URL}/tools/{self.id_tool}/accommodations/{item_id}"


def _require(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ConfigError(
            f"Missing required environment variable: {name}. "
            f"Copy .env.example to .env and fill it in."
        )
    return value


def load_config() -> Config:
    """Load and validate configuration. Raises ConfigError with a clear message."""
    load_dotenv()

    id_tool = _require("ID_TOOL")
    notifier = os.environ.get("NOTIFIER", "telegram").strip().lower()
    if notifier not in ("telegram", "discord", "both"):
        raise ConfigError(
            f"Invalid NOTIFIER value {notifier!r}: must be 'telegram', 'discord' or 'both'."
        )

    cfg = Config(id_tool=id_tool, notifier=notifier)

    if notifier in ("telegram", "both"):
        cfg.telegram_bot_token = _require("TELEGRAM_BOT_TOKEN")
        cfg.telegram_chat_id = _require("TELEGRAM_CHAT_ID")
    if notifier in ("discord", "both"):
        cfg.discord_webhook_url = _require("DISCORD_WEBHOOK_URL")

    if page_size := os.environ.get("PAGE_SIZE"):
        cfg.page_size = int(page_size)
    if heartbeat := os.environ.get("HEARTBEAT_HOURS"):
        try:
            cfg.heartbeat_hours = float(heartbeat)
        except ValueError:
            raise ConfigError(f"Invalid HEARTBEAT_HOURS value {heartbeat!r}: must be a number.")
    if state_file := os.environ.get("STATE_FILE"):
        cfg.state_file = state_file
    cfg.run_stats_file = os.environ.get("RUN_STATS_FILE", "").strip()

    return cfg
