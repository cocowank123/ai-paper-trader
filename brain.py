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


SYSTEM_PROMPT = """You are a disciplined crypto trading analyst feeding signals to an \
automated PAPER-trading system. You are NOT a hype machine. Your job is to judge whether \
there is a genuine, well-supported edge right now — and to say 'flat' (no trade) whenever \
the picture is mixed, unclear, or just noise. Most of the time, the honest answer is 'flat'.

Weigh BOTH the technical trend and the news sentiment. A trade signal should only have high \
confidence when the technicals and the news point the same way. Conflicting signals = low \
confidence or flat. Never invent certainty you don't have."""


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

Decide: long, short, or flat? Give a confidence 0-100 and a brief reason. \
Remember: only high confidence when technicals AND news agree. When in doubt, choose flat."""


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
