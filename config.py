"""
config.py — Loads all settings from your .env file (or environment variables)
and exposes them as a single `Settings` object the rest of the app imports.

Why this exists: keeping configuration (and especially your API key) in one
place, separate from the code, is good practice — you can change behaviour
without editing logic, and your secret key never gets hard-coded.
"""

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

# Read the .env file in this folder and load it into the environment.
load_dotenv()


def _get(name: str, default: str) -> str:
    """Read an env var, falling back to a default if it's missing/blank."""
    value = os.getenv(name)
    return value if value not in (None, "") else default


# Free, no-key-required crypto news feeds (RSS). Add or remove as you like.
DEFAULT_NEWS_FEEDS = [
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://cointelegraph.com/rss",
    "https://www.newsbtc.com/feed/",
]


@dataclass
class Settings:
    # --- AI ---
    anthropic_api_key: str = _get("ANTHROPIC_API_KEY", "")
    model: str = _get("MODEL", "claude-haiku-4-5")
    min_confidence: int = int(_get("MIN_CONFIDENCE", "60"))

    # --- Market ---
    symbol: str = _get("SYMBOL", "BTC/USDT")
    exchange: str = _get("EXCHANGE", "binance")
    timeframe: str = _get("TIMEFRAME", "1h")

    # --- Risk / sizing ---
    position_fraction: float = float(_get("POSITION_FRACTION", "0.20"))
    atr_mult: float = float(_get("ATR_MULT", "2.0"))
    reward_risk: float = float(_get("REWARD_RISK", "1.5"))
    starting_equity: float = float(_get("STARTING_EQUITY", "10000"))

    # --- Loop / news ---
    interval_minutes: int = int(_get("INTERVAL_MINUTES", "60"))
    news_lookback_hours: int = int(_get("NEWS_LOOKBACK_HOURS", "12"))
    news_max_items: int = int(_get("NEWS_MAX_ITEMS", "25"))
    news_feeds: list = field(default_factory=lambda: list(DEFAULT_NEWS_FEEDS))

    # Where the simulated account is saved (so P&L survives restarts).
    state_file: str = "account_state.json"

    def require_api_key(self) -> None:
        """Fail early with a clear message if the key is missing."""
        if not self.anthropic_api_key or self.anthropic_api_key.startswith("sk-ant-paste"):
            raise SystemExit(
                "\nNo Anthropic API key found.\n"
                "  1. Copy .env.example to .env\n"
                "  2. Put your real key from https://console.anthropic.com in it\n"
            )


# A single shared instance the whole app imports: `from config import settings`
settings = Settings()
