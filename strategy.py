"""
strategy.py — The Quant Regime Engine (QRE) entry logic, ported 1:1 from the
Pine Script v6.1. It is a LONG-ONLY mean-reversion strategy:

  Enter LONG when ALL of these are true:
    1. Z-Score <= -2.0      → price is statistically "cheap" (stretched below mean)
    2. price  >  200 EMA    → but the macro trend is still UP (buy the dip, not the crash)
    3. inside the UTC session window (all hours except 21:00-22:59 UTC)

There is no short side and no AI — it's deterministic, so the exact same inputs
always produce the exact same decision (this is why it can be backtested honestly).
"""


def evaluate(snap: dict, s) -> dict:
    """Return {'enter': bool, 'reason': str} for the current snapshot."""
    z_ok = snap["zscore"] <= s.z_entry        # statistically oversold
    macro_ok = snap["macro_bullish"]          # price above 200 EMA
    session_ok = snap["in_session"]           # inside trading window

    enter = z_ok and macro_ok and session_ok

    reason = (
        f"z {snap['zscore']:.2f} {'<=' if z_ok else '>'} {s.z_entry} "
        f"({'oversold OK' if z_ok else 'not oversold'}) | "
        f"macro {'UP OK' if macro_ok else 'DOWN (blocked)'} | "
        f"session {'OPEN' if session_ok else 'CLOSED (blocked)'}"
    )
    return {"enter": enter, "reason": reason}
