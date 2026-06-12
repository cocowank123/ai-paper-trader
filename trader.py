"""
trader.py — One decision cycle of the Quant Regime Engine:

    1. Fetch USD/JPY 30m data + indicators (z-score, 200 EMA, ATR, session)
    2. Enforce stop / take-profit on any open position
    3. If flat, check the QRE entry rules and open a LONG if they all pass
    4. Print a clear report and save state

run_once()  -> one cycle.
run_loop()  -> repeat forever on a timer.
"""

import time

import market_data
import strategy
from config import Settings
from paper_broker import PaperBroker


class Trader:
    def __init__(self, settings: Settings):
        self.s = settings
        self.broker = PaperBroker(settings.state_file, settings.starting_equity)

    def run_once(self) -> None:
        s = self.s
        print("\n" + "=" * 64)
        print(f"  CYCLE @ {time.strftime('%Y-%m-%d %H:%M:%S')}  |  {s.symbol} {s.interval}")
        print("=" * 64)

        # 1. Market snapshot ---------------------------------------------------
        try:
            snap = market_data.get_snapshot(s)
        except Exception as exc:
            print(f"  ! Could not fetch market data: {exc}")
            return
        price = snap["price"]
        print(f"  Price {price}  |  {snap['trend']}  |  z-score {snap['zscore']}  |  ATR {snap['atr']}")
        print(f"  EMA200 {snap['ema200']}  |  session {'OPEN' if snap['in_session'] else 'CLOSED'} "
              f"(hour {snap['hour_utc']} UTC)")

        # 2. Manage any open position -----------------------------------------
        ev = self.broker.check_stops(price)
        if ev:
            print(f"  >> {ev['reason'].upper()} hit — closed long for P&L {ev['pnl']}")

        # 3. Entry (long only, only when flat) --------------------------------
        if self.broker.position is None:
            decision = strategy.evaluate(snap, s)
            print(f"  Signal: {decision['reason']}")
            if decision["enter"]:
                stop = price - snap["atr"] * s.sl_atr_mult
                take_profit = price + snap["atr"] * s.tp_atr_mult
                ev = self.broker.open_long(price, stop, take_profit, s.risk_per_trade)
                print(f"  >> Opened LONG @ {price}  (stop {ev['stop']}, target {ev['take_profit']}, "
                      f"size {ev['size']})")
            else:
                print("  >> No entry (conditions not all met)")
        else:
            p = self.broker.position
            print(f"  >> Holding LONG @ {round(p['entry'], 3)} "
                  f"(stop {round(p['stop'], 3)}, target {round(p['take_profit'], 3)})")

        # 4. Report + persist --------------------------------------------------
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
        try:
            snap = market_data.get_snapshot(self.s)
            price = snap["price"]
        except Exception:
            price = self.broker.position["entry"] if self.broker.position else 0.0
        self._print_account(price)

    def _print_account(self, price: float) -> None:
        a = self.broker.summary(price)
        print("  " + "-" * 60)
        print(f"  ACCOUNT  equity ${a['equity']}  (return {a['total_return_pct']:+.2f}%)")
        print(f"           realized ${a['realized_pnl']}  unrealized ${a['unrealized_pnl']}")
        print(f"           closed trades {a['closed_trades']}  "
              f"win rate {a['win_rate_pct']}%  profit factor {a['profit_factor']}")
        if a["open_position"]:
            p = a["open_position"]
            print(f"           OPEN long size {round(p['size'], 4)} @ {round(p['entry'], 3)}")
        print("  " + "-" * 60)
