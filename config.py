"""
config.py — Settings for the Quant Regime Engine (QRE) strategy.

All values can be overridden by environment variables (handy for the GitHub
Actions workflow), but the defaults below match the Pine Script v6.1 exactly.
No API keys needed — this strategy is pure math.
"""

import os
from dataclasses import dataclass


def _get(name: str, default: str) -> str:
    value = os.getenv(name)
    return value if value not in (None, "") else default


@dataclass
class Settings:
    # --- Market / data (Yahoo Finance ticker for USD/JPY) ---
    symbol: str = _get("SYMBOL", "USDJPY=X")
    interval: str = _get("INTERVAL", "30m")      # 30-minute candles
    data_period: str = _get("DATA_PERIOD", "1mo")  # how much history to pull

    # --- Statistical Z-Score engine ---
    z_length: int = int(_get("Z_LENGTH", "20"))          # 20 x 30m = 10-hour lookback
    z_entry: float = float(_get("Z_ENTRY", "-2.0"))      # long when z-score <= this

    # --- Macro filter ---
    ema_length: int = int(_get("EMA_LENGTH", "200"))     # 200 EMA macro trend filter

    # --- Volatility bracket (ATR stop / take-profit) ---
    atr_length: int = int(_get("ATR_LENGTH", "14"))
    sl_atr_mult: float = float(_get("SL_ATR_MULT", "2.2"))   # stop  = entry - ATR*2.2
    tp_atr_mult: float = float(_get("TP_ATR_MULT", "4.4"))   # target = entry + ATR*4.4 (2:1 R:R)

    # --- Risk engine ---
    risk_per_trade: float = float(_get("RISK_PER_TRADE", "1.5"))  # % of equity risked per trade
    starting_equity: float = float(_get("STARTING_EQUITY", "10000"))

    # --- Loop ---
    interval_minutes: int = int(_get("INTERVAL_MINUTES", "15"))

    # Where the simulated account is saved (so P&L survives restarts).
    state_file: str = "account_state.json"


# A single shared instance the whole app imports: `from config import settings`
settings = Settings()
