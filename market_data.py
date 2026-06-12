"""
market_data.py — Fetches USD/JPY 30-minute candles from Yahoo Finance (free, no
account needed) and computes the indicators the QRE strategy uses:

  - Rolling Z-Score  (how many std-devs the price is from its 20-bar mean)
  - 200 EMA          (macro trend filter)
  - ATR              (volatility, for stop / take-profit sizing)
  - UTC session gate (trade all hours except 21:00-22:59 UTC)

Yahoo's ticker for USD/JPY is "USDJPY=X". Intraday (30m) data is available for
roughly the last 60 days, which is plenty for a 200-bar EMA.
"""

from datetime import datetime, timezone

import pandas as pd
import yfinance as yf


def fetch(symbol: str, interval: str, period: str) -> pd.DataFrame:
    """Download recent candles as a DataFrame with open/high/low/close columns."""
    df = yf.download(symbol, period=period, interval=interval,
                     progress=False, auto_adjust=True)
    if df is None or df.empty:
        raise RuntimeError(f"Yahoo returned no data for {symbol} ({interval}, {period})")
    # Single-ticker downloads sometimes come back with a MultiIndex column — flatten it.
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.rename(columns=str.lower)
    return df[["open", "high", "low", "close"]].dropna()


def _atr(df: pd.DataFrame, length: int) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    true_range = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    # Wilder's smoothing (RMA), matching Pine's ta.atr.
    return true_range.ewm(alpha=1 / length, adjust=False).mean()


def get_snapshot(s) -> dict:
    """Fetch data and return the current technical picture as a dict."""
    df = fetch(s.symbol, s.interval, s.data_period)
    close = df["close"]

    # Rolling Z-Score: (price - mean) / std over the last z_length bars.
    # ddof=0 = population std, matching Pine's ta.stdev.
    mean = close.rolling(s.z_length).mean()
    std = close.rolling(s.z_length).std(ddof=0)
    zscore = float(((close.iloc[-1] - mean.iloc[-1]) / std.iloc[-1])) if std.iloc[-1] > 0 else 0.0

    ema = close.ewm(span=s.ema_length, adjust=False).mean()
    ema200 = float(ema.iloc[-1])
    atr = float(_atr(df, s.atr_length).iloc[-1])
    price = float(close.iloc[-1])

    # Hardcoded UTC temporal gate: valid except 21:00-22:59 UTC.
    hour_utc = datetime.now(timezone.utc).hour
    in_session = hour_utc >= 23 or hour_utc < 21

    return {
        "symbol": s.symbol,
        "interval": s.interval,
        "price": round(price, 3),
        "ema200": round(ema200, 3),
        "zscore": round(zscore, 2),
        "atr": round(atr, 4),
        "trend": "uptrend" if price > ema200 else "downtrend",
        "macro_bullish": price > ema200,
        "hour_utc": hour_utc,
        "in_session": in_session,
    }
