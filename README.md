# Quant Regime Engine (QRE) — USD/JPY 30M Paper Trader

A deterministic, **long-only mean-reversion** strategy ported from Pine Script,
running on **simulated (fake) money**. It buys USD/JPY when price is statistically
stretched below its mean *but still in a macro uptrend*, with an ATR-based stop
and a 2:1 reward-to-risk target.

```
  ┌──────────────┐   ┌────────────────────┐   ┌──────────┐   ┌──────────┐
  │ USD/JPY 30m  │ → │  Z-Score + 200 EMA │ → │ Entry/   │ → │  Paper   │
  │ (Yahoo Fin.) │   │  + ATR + session   │   │ exit rule│   │  trade   │
  └──────────────┘   └────────────────────┘   └──────────┘   └──────────┘
                                                                   │
                                                     logs + P&L ───┘
```

## The strategy (entry rules — all must be true)

1. **Z-Score ≤ −2.0** — price is ~2 std-devs below its 20-bar (10-hour) mean → "cheap"
2. **Price > 200 EMA** — macro trend is still up → buy the dip, not the crash
3. **Inside the UTC session** — every hour except 21:00–22:59 UTC

**Exit:** stop-loss at `entry − ATR×2.2`, take-profit at `entry + ATR×4.4` (2:1 R:R).
**Sizing:** each trade risks **1.5% of equity** (loss at the stop = 1.5% exactly).

No AI, no API keys — it's pure math, so the same inputs always give the same
decision (which is why it can be backtested honestly).

---

## ⚠️ Honest expectations

- **Fake money only.** Nothing here touches a real account.
- **Not guaranteed to make money.** Run it, gather ~30+ trades, then judge it by
  **profit factor** and **net P&L after costs** — never by one trade or win-rate alone.
- Best practice: **backtest this in TradingView first** (it's a Pine strategy) to
  see its historical numbers before trusting the live paper run.

---

## Setup

Needs **Python 3.10+**. No accounts, no keys.

```bash
cd trading_tool
python -m venv venv
venv\Scripts\activate            # Windows  (source venv/bin/activate on Mac/Linux)
pip install -r requirements.txt
```

## Running it

```bash
python main.py --once     # one cycle — start here
python main.py --status   # show the paper account, no trading
python main.py --loop     # run continuously (every INTERVAL_MINUTES)
python main.py --reset    # wipe the account and start fresh
```

State (positions + P&L) is saved to `account_state.json` and resumes automatically.

---

## Files

| File | Role |
|------|------|
| `main.py` | Command-line entry point |
| `config.py` | Strategy parameters (override via env vars) |
| `market_data.py` | Fetches USD/JPY 30m data + computes Z-Score / EMA / ATR / session |
| `strategy.py` | The QRE entry rules (deterministic) |
| `paper_broker.py` | Simulated account: risk-based sizing, stop/TP, P&L, profit factor |
| `trader.py` | Runs one decision cycle and prints the report |

## Tuning (edit `config.py` defaults, or set env vars in the workflow)

`Z_ENTRY`, `Z_LENGTH`, `EMA_LENGTH`, `SL_ATR_MULT`, `TP_ATR_MULT`, `RISK_PER_TRADE`,
`SYMBOL`, `INTERVAL`. Change **one at a time** and keep a results log.

---

## Cloud automation (GitHub Actions)

`.github/workflows/trade.yml` runs `python main.py --once` in a loop (every 15 min
for ~5.5h, restarting every 6h), committing `account_state.json` back each time so
P&L persists — all with your PC off. No secrets required.
