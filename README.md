# AI Crypto Paper-Trading Tool

An automated tool that reads the market and the news, asks an AI (Claude) for a
trade signal, and trades it on **simulated (fake) money** — logging every
decision and your running profit & loss so you can judge whether it has an edge
**before risking anything real.**

```
   ┌─────────────┐   ┌──────────┐   ┌───────────┐   ┌──────────┐   ┌──────────┐
   │ Market data │ + │   News   │ → │ AI brain  │ → │ Decision │ → │  Paper   │
   │ (price+TA)  │   │  (RSS)   │   │ (Claude)  │   │ + risk   │   │  trade   │
   └─────────────┘   └──────────┘   └───────────┘   └──────────┘   └──────────┘
                                                                        │
                                                          logs + P&L ───┘
```

---

## ⚠️ Read this first (honest expectations)

- This trades **fake money only.** Nothing here touches a real account.
- It is **not guaranteed to make money.** No tool is. The whole point is to run
  it on paper and *measure* whether the AI's signals actually have an edge.
- Judge it by the numbers it prints (return %, win rate, P&L over many trades),
  not by any single good or bad trade.
- Only consider real money after weeks of paper results show a genuine edge —
  and even then, start tiny.

---

## Setup (one time)

You need **Python 3.10+** and an **Anthropic API key** (from
<https://console.anthropic.com>). No exchange account is required — market data
and news are public.

```bash
# 1. Go into the project folder
cd trading_tool

# 2. (Recommended) create a virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create your config file and add your API key
copy .env.example .env       # Windows   (cp on Mac/Linux)
#   then open .env and paste your real ANTHROPIC_API_KEY
```

---

## Running it

```bash
python main.py --once     # run ONE analysis cycle — start here
python main.py --status   # show your paper account, no trading
python main.py --loop     # run continuously (every INTERVAL_MINUTES from .env)
python main.py --reset    # wipe the paper account and start fresh
```

Start with `--once` a few times to watch how it thinks. When you're happy, leave
`--loop` running. Your account (positions + P&L) is saved to
`account_state.json` and resumes automatically.

---

## What each file does

| File | Role |
|------|------|
| `main.py` | Command-line entry point |
| `config.py` | Loads your settings from `.env` |
| `market_data.py` | Fetches price candles + computes EMA / RSI / ATR |
| `news_feed.py` | Pulls recent crypto headlines from free RSS feeds |
| `brain.py` | Sends technicals + news to Claude, gets a structured signal |
| `paper_broker.py` | Simulated account: positions, stop-loss / take-profit, P&L |
| `trader.py` | Runs one full decision cycle and prints the report |

---

## Tuning it (edit `.env`)

- `MIN_CONFIDENCE` — how sure the AI must be before trading (higher = fewer, more
  selective trades). Start at 60.
- `POSITION_FRACTION`, `ATR_MULT`, `REWARD_RISK` — risk settings, same idea as the
  Pine Script backtest.
- `SYMBOL` / `EXCHANGE` / `TIMEFRAME` — what and where to trade.
- `MODEL` — `claude-haiku-4-5` (cheapest, recommended). Costs roughly a few
  dollars/month at hourly cycles.

---

## Where this can go next

- **Forex:** point it at a forex data source (your earlier goal).
- **Real exchange testnet:** swap `paper_broker.py` for orders sent to a Bybit or
  Binance testnet via `ccxt` — still fake money, but exercises real order plumbing.
- **Smarter brain:** feed it more context (order book, multiple timeframes) or
  compare Haiku vs Sonnet to see if a stronger model improves results.

Keep a results log as you tune — and change **one thing at a time**.
