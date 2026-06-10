"""
market_data.py — Fetches live price candles from a crypto exchange (no API key
needed for public data) and computes the same indicators you backtested in Pine
Script: a trend EMA, RSI, and ATR.

The output is a small dictionary ("technical summary") that gets handed to the
AI brain so it can reason about the trend alongside the news.
"""

import ccxt
import pandas as pd


def get_exchange(name: str) -> ccxt.Exchange:
    """Create a ccxt exchange object for public (read-only) market data."""
    if not hasattr(ccxt, name):
        raise SystemExit(f"Unknown exchange '{name}'. Try 'binance', 'bybit', 'kraken', etc.")
    return getattr(ccxt, name)({"enableRateLimit": True})


def fetch_ohlcv(exchange: ccxt.Exchange, symbol: str, timeframe: str, limit: int = 300) -> pd.DataFrame:
    """Download recent candles. Each row = [time, open, high, low, close, volume]."""
    raw = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(raw, columns=["time", "open", "high", "low", "close", "volume"])
    df["time"] = pd.to_datetime(df["time"], unit="ms", utc=True)
    return df


# --- Indicator math (plain, readable implementations) -----------------------

def _ema(series: pd.Series, length: int) -> pd.Series:
    return series.ewm(span=length, adjust=False).mean()


def _rsi(series: pd.Series, length: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / length, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / length, adjust=False).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def _atr(df: pd.DataFrame, length: int = 14) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    true_range = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return true_range.ewm(alpha=1 / length, adjust=False).mean()


def analyze(df: pd.DataFrame) -> dict:
    """Turn raw candles into a compact summary of the current technical picture."""
    close = df["close"]
    price = float(close.iloc[-1])

    ema200 = float(_ema(close, 200).iloc[-1])
    ema50 = float(_ema(close, 50).iloc[-1])
    rsi14 = float(_rsi(close, 14).iloc[-1])
    atr14 = float(_atr(df, 14).iloc[-1])

    # Percent change over the last ~24 candles, for quick momentum context.
    lookback = min(24, len(close) - 1)
    pct_change = (price / float(close.iloc[-1 - lookback]) - 1) * 100 if lookback > 0 else 0.0

    return {
        "price": round(price, 2),
        "trend": "uptrend" if price > ema200 else "downtrend",
        "ema50": round(ema50, 2),
        "ema200": round(ema200, 2),
        "rsi14": round(rsi14, 1),
        "atr14": round(atr14, 2),
        "recent_change_pct": round(pct_change, 2),
    }


def get_market_snapshot(symbol: str, exchange_name: str, timeframe: str) -> dict:
    """Convenience wrapper: fetch + analyze in one call."""
    exchange = get_exchange(exchange_name)
    df = fetch_ohlcv(exchange, symbol, timeframe)
    summary = analyze(df)
    summary["symbol"] = symbol
    summary["timeframe"] = timeframe
    return summary
