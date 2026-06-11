"""
trader.py — Ties everything together into one decision cycle:

    1. Get the market snapshot (price + indicators)
    2. Get recent news headlines
    3. Ask the AI brain for a signal (long / short / flat + confidence)
    4. Enforce stops/take-profit on any open position
    5. Move the paper position to match the signal (if confident enough)
    6. Print a clear report and save state

run_once()  -> one cycle.
run_loop()  -> repeat forever on a timer.
"""

import time

import anthropic

import brain
import market_data
import news_feed
from config import Settings
from paper_broker import PaperBroker


class Trader:
    def __init__(self, settings: Settings):
        self.s = settings
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self.broker = PaperBroker(settings.state_file, settings.starting_equity)

    def run_once(self) -> None:
        s = self.s
        print("\n" + "=" * 64)
        print(f"  CYCLE @ {time.strftime('%Y-%m-%d %H:%M:%S')}  |  {s.symbol} {s.timeframe}")
        print("=" * 64)

        # 1. Market snapshot ---------------------------------------------------
        try:
            tech = market_data.get_market_snapshot(s.symbol, s.exchange, s.timeframe)
        except Exception as exc:
            print(f"  ! Could not fetch market data: {exc}")
            return
        price = tech["price"]
        print(f"  Price {price}  |  {tech['trend']}  |  RSI {tech['rsi14']}  |  "
              f"24-candle move {tech['recent_change_pct']}%")

        # 2. News --------------------------------------------------------------
        headlines = news_feed.fetch_headlines(
            s.news_feeds, s.news_lookback_hours, s.news_max_items
        )
        print(f"  Pulled {len(headlines)} recent headlines")
        headlines_text = news_feed.format_for_prompt(headlines)

        # 3. AI signal ---------------------------------------------------------
        signal = brain.get_signal(self.client, s.model, tech, headlines_text)
        print(f"  AI says: {signal.direction.upper()}  (confidence {signal.confidence}, trades at >= {s.min_confidence})")
        print(f"    \"{signal.reasoning}\"")

        # 4. Enforce stops on any existing position ----------------------------
        stop_event = self.broker.check_stops(price)
        if stop_event:
            print(f"  >> {stop_event['reason'].upper()} hit — closed {stop_event['side']} "
                  f"for P&L {stop_event['pnl']}")

        # 5. Act on the signal -------------------------------------------------
        desired = signal.direction if signal.confidence >= s.min_confidence else "flat"
        current = self.broker.position["side"] if self.broker.position else "flat"

        if desired != current:
            if self.broker.position:  # close whatever we hold first
                ev = self.broker.close_position(price, "signal change")
                print(f"  >> Closed {ev['side']} (signal change) for P&L {ev['pnl']}")
            if desired in ("long", "short"):
                ev = self.broker.open_position(
                    desired, price, tech["atr14"],
                    s.atr_mult, s.reward_risk, s.position_fraction,
                )
                print(f"  >> Opened {desired.upper()} @ {price}  "
                      f"(stop {ev['stop']}, target {ev['take_profit']})")
        else:
            if current == "flat":
                print("  >> No trade (staying out)")
            else:
                print(f"  >> Holding existing {current} position")

        # 6. Report + persist --------------------------------------------------
        self.broker.save()
        self._print_account(price)

    def run_loop(self) -> None:
        interval = self.s.interval_minutes * 60
        print(f"Starting loop — running every {self.s.interval_minutes} min. Press Ctrl+C to stop.")
        try:
            while True:
                self.run_once()
                print(f"\n  ...sleeping {self.s.interval_minutes} min until next cycle...")
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\nStopped. Your account state is saved — run again anytime to resume.")

    def print_status(self) -> None:
        """Show the account without trading (uses the latest price for valuation)."""
        try:
            tech = market_data.get_market_snapshot(self.s.symbol, self.s.exchange, self.s.timeframe)
            price = tech["price"]
        except Exception:
            price = self.broker.position["entry"] if self.broker.position else 0.0
        self._print_account(price)

    def _print_account(self, price: float) -> None:
        a = self.broker.summary(price)
        print("  " + "-" * 60)
        print(f"  ACCOUNT  equity ${a['equity']}  "
              f"(return {a['total_return_pct']:+.2f}%)")
        print(f"           realized ${a['realized_pnl']}  unrealized ${a['unrealized_pnl']}")
        print(f"           closed trades {a['closed_trades']}  win rate {a['win_rate_pct']}%")
        if a["open_position"]:
            p = a["open_position"]
            print(f"           OPEN {p['side']} {round(p['size'], 6)} @ {round(p['entry'], 2)}")
        print("  " + "-" * 60)
