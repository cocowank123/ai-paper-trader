"""
brain.py — The "AI brain". It sends the current technical picture plus recent
news to Claude (the cheap, fast Haiku model) and gets back a structured trading
signal: a direction, a confidence score, and a short reason.

We use the SDK's structured-output feature (`messages.parse` with a Pydantic
model) so the response is GUARANTEED to match the shape we expect — no fragile
text parsing.
"""

from typing import Literal

import anthropic
from pydantic import BaseModel, Field


class TradeSignal(BaseModel):
    """The exact shape we force the model to return."""
    direction: Literal["long", "short", "flat"] = Field(
        description="'long' = expect price up, 'short' = expect price down, 'flat' = stay out"
    )
    confidence: int = Field(ge=0, le=100, description="How confident, 0-100")
    reasoning: str = Field(description="One or two sentences explaining the call")


SYSTEM_PROMPT = """You are a decisive crypto trading analyst feeding signals to an automated \
PAPER-trading system. Your job is to take a directional stance whenever the TECHNICALS lean \
one way, and to size your confidence honestly.

How to weigh the inputs:
- The TECHNICAL TREND is your PRIMARY driver. If price is in an uptrend, lean long; in a \
downtrend, lean short. The trend decides the DIRECTION.
- NEWS is a SECONDARY, confirm-or-veto layer. Crypto news is almost always a mix of bullish \
and bearish takes — that is normal and is NOT a reason to refuse to trade. Only let news pull \
you to 'flat' if it is decisively, one-sidedly AGAINST the technical direction (e.g. a major \
hack, ban, or crash dominating the headlines).

Confidence scale (use the full range — do not default to the 20s):
- 0-35  → genuinely no directional lean, or news strongly contradicts the trend → usually 'flat'
- 40-60 → a clear technical trend, with news mixed-but-not-contradictory → TRADE in the trend's direction
- 65-85 → a clear technical trend AND news leaning the same way → confident trade
- 85+   → strong trend, strong momentum, and aligned news

A mixed news backdrop with a clear trend should land around 45-55, not 25. Be decisive: a \
mediocre-but-real edge traded consistently beats sitting out forever. Only choose 'flat' when \
the technicals themselves are genuinely directionless or news decisively opposes them."""


def build_user_prompt(tech: dict, headlines_text: str) -> str:
    return f"""Analyze the current situation for {tech['symbol']} on the {tech['timeframe']} timeframe.

TECHNICALS:
- Current price: {tech['price']}
- Overall trend (price vs 200 EMA): {tech['trend']}
- 50 EMA: {tech['ema50']}, 200 EMA: {tech['ema200']}
- RSI(14): {tech['rsi14']}  (below 30 = oversold, above 70 = overbought)
- ATR(14) volatility: {tech['atr14']}
- Recent change: {tech['recent_change_pct']}% over the last ~24 candles

RECENT NEWS HEADLINES:
{headlines_text}

Decide: long, short, or flat? Let the TECHNICAL TREND set your direction, and use the news \
only to confirm or (if decisively opposed) veto it. A clear trend with merely mixed news should \
score around 45-55 confidence and TRADE — don't default to the 20s just because headlines \
conflict. Give a confidence 0-100 and a brief reason."""


def get_signal(client: anthropic.Anthropic, model: str, tech: dict, headlines_text: str) -> TradeSignal:
    """Ask Claude for a structured trade signal. Falls back to 'flat' on any error."""
    try:
        response = client.messages.parse(
            model=model,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": build_user_prompt(tech, headlines_text)}],
            output_format=TradeSignal,
        )
        return response.parsed_output
    except Exception as exc:
        # Network blip, rate limit, refusal, etc. — never trade on an error.
        return TradeSignal(direction="flat", confidence=0, reasoning=f"AI call failed: {exc}")
