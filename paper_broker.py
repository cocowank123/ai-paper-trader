"""
paper_broker.py — A simulated broker. It holds fake money, opens/closes one
position at a time, enforces a stop-loss and take-profit, tracks profit & loss,
and saves everything to a JSON file so your results survive restarts.

This is "paper trading": no real money, no real exchange. It models trades as
simple directional bets (like a CFD) — when you're long, you profit if price
rises; when short, you profit if price falls.
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
        p = self.position
        if p["side"] == "long":
            return p["size"] * (price - p["entry"])
        return p["size"] * (p["entry"] - price)

    def equity(self, price: float) -> float:
        return self.cash + self.unrealized(price)

    # --- actions ------------------------------------------------------------

    def open_position(self, side: str, price: float, atr: float,
                      atr_mult: float, reward_risk: float, fraction: float) -> dict:
        """Open a long or short, sizing off current cash and setting stop/TP."""
        notional = self.cash * fraction
        size = notional / price
        if side == "long":
            stop = price - atr * atr_mult
            take_profit = price + atr * atr_mult * reward_risk
        else:
            stop = price + atr * atr_mult
            take_profit = price - atr * atr_mult * reward_risk

        self.position = {
            "side": side,
            "size": size,
            "entry": price,
            "stop": stop,
            "take_profit": take_profit,
            "opened_at": _now(),
        }
        event = {"event": "open", "side": side, "price": price,
                 "size": round(size, 6), "stop": round(stop, 2),
                 "take_profit": round(take_profit, 2), "time": _now()}
        self.trades.append(event)
        return event

    def close_position(self, price: float, reason: str) -> dict:
        """Close the open position, bank the P&L."""
        pnl = self.unrealized(price)
        self.cash += pnl
        self.realized_pnl += pnl
        side = self.position["side"]
        event = {"event": "close", "side": side, "price": price,
                 "pnl": round(pnl, 2), "reason": reason, "time": _now()}
        self.trades.append(event)
        self.position = None
        return event

    def check_stops(self, price: float):
        """If price hit the stop or take-profit, close and report it. Else None."""
        if not self.position:
            return None
        p = self.position
        if p["side"] == "long":
            if price <= p["stop"]:
                return self.close_position(price, "stop-loss")
            if price >= p["take_profit"]:
                return self.close_position(price, "take-profit")
        else:  # short
            if price >= p["stop"]:
                return self.close_position(price, "stop-loss")
            if price <= p["take_profit"]:
                return self.close_position(price, "take-profit")
        return None

    # --- reporting ----------------------------------------------------------

    def summary(self, price: float) -> dict:
        equity = self.equity(price)
        total_return_pct = (equity / self.starting_equity - 1) * 100
        closed = [t for t in self.trades if t["event"] == "close"]
        wins = [t for t in closed if t["pnl"] > 0]
        win_rate = (len(wins) / len(closed) * 100) if closed else 0.0
        return {
            "equity": round(equity, 2),
            "cash": round(self.cash, 2),
            "unrealized_pnl": round(self.unrealized(price), 2),
            "realized_pnl": round(self.realized_pnl, 2),
            "total_return_pct": round(total_return_pct, 2),
            "closed_trades": len(closed),
            "win_rate_pct": round(win_rate, 1),
            "open_position": self.position,
        }


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
