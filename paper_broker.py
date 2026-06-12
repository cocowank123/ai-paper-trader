"""
paper_broker.py — A simulated broker (fake money). It holds one LONG position at
a time, enforces a stop-loss and take-profit, sizes each trade by RISK, tracks
profit & loss, and saves everything to a JSON file so results survive restarts.

Risk-based sizing: each trade is sized so that, if the stop is hit, the loss is
exactly `risk_per_trade` percent of equity. This is cleaner and more honest than
the Pine Script's cross-currency unit math, and gives identical risk behaviour.
"""

import json
import os
from datetime import datetime, timezone


class PaperBroker:
    def __init__(self, state_file: str, starting_equity: float):
        self.state_file = state_file
        self.starting_equity = starting_equity
        self.cash = starting_equity          # realised balance
        self.realized_pnl = 0.0
        self.position = None                  # dict or None
        self.trades = []                      # history of opens/closes
        self._load()

    # --- persistence --------------------------------------------------------

    def _load(self) -> None:
        if os.path.exists(self.state_file):
            with open(self.state_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.cash = data.get("cash", self.starting_equity)
            self.starting_equity = data.get("starting_equity", self.starting_equity)
            self.realized_pnl = data.get("realized_pnl", 0.0)
            self.position = data.get("position")
            self.trades = data.get("trades", [])

    def save(self) -> None:
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "cash": self.cash,
                    "starting_equity": self.starting_equity,
                    "realized_pnl": self.realized_pnl,
                    "position": self.position,
                    "trades": self.trades,
                },
                f,
                indent=2,
            )

    # --- valuation ----------------------------------------------------------

    def unrealized(self, price: float) -> float:
        if not self.position:
            return 0.0
        # Long only: profit when price rises above entry.
        return self.position["size"] * (price - self.position["entry"])

    def equity(self, price: float) -> float:
        return self.cash + self.unrealized(price)

    # --- actions ------------------------------------------------------------

    def open_long(self, price: float, stop: float, take_profit: float, risk_pct: float) -> dict:
        """Open a long sized so that hitting `stop` loses exactly risk_pct% of equity."""
        stop_distance = price - stop
        if stop_distance <= 0:
            raise ValueError("stop must be below entry for a long")
        risk_capital = self.cash * (risk_pct / 100.0)
        size = risk_capital / stop_distance

        self.position = {
            "side": "long",
            "size": size,
            "entry": price,
            "stop": stop,
            "take_profit": take_profit,
            "opened_at": _now(),
        }
        event = {"event": "open", "side": "long", "price": price,
                 "size": round(size, 4), "stop": round(stop, 3),
                 "take_profit": round(take_profit, 3), "time": _now()}
        self.trades.append(event)
        return event

    def close_position(self, price: float, reason: str) -> dict:
        """Close the open position, bank the P&L."""
        pnl = self.unrealized(price)
        self.cash += pnl
        self.realized_pnl += pnl
        event = {"event": "close", "side": self.position["side"], "price": price,
                 "pnl": round(pnl, 2), "reason": reason, "time": _now()}
        self.trades.append(event)
        self.position = None
        return event

    def check_stops(self, price: float):
        """If price hit the stop or take-profit, close and report it. Else None."""
        if not self.position:
            return None
        p = self.position
        if price <= p["stop"]:
            return self.close_position(price, "stop-loss")
        if price >= p["take_profit"]:
            return self.close_position(price, "take-profit")
        return None

    # --- reporting ----------------------------------------------------------

    def summary(self, price: float) -> dict:
        equity = self.equity(price)
        total_return_pct = (equity / self.starting_equity - 1) * 100
        closed = [t for t in self.trades if t["event"] == "close"]
        wins = [t for t in closed if t["pnl"] > 0]
        win_rate = (len(wins) / len(closed) * 100) if closed else 0.0
        gross_win = sum(t["pnl"] for t in closed if t["pnl"] > 0)
        gross_loss = -sum(t["pnl"] for t in closed if t["pnl"] < 0)
        profit_factor = (gross_win / gross_loss) if gross_loss > 0 else 0.0
        return {
            "equity": round(equity, 2),
            "realized_pnl": round(self.realized_pnl, 2),
            "unrealized_pnl": round(self.unrealized(price), 2),
            "total_return_pct": round(total_return_pct, 2),
            "closed_trades": len(closed),
            "win_rate_pct": round(win_rate, 1),
            "profit_factor": round(profit_factor, 2),
            "open_position": self.position,
        }


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
