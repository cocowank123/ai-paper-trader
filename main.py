"""
main.py — Entry point. Run from the terminal.

    python main.py --once       Run a single decision cycle (start here)
    python main.py --loop       Run continuously on the timer
    python main.py --status     Show your paper account without trading
    python main.py --reset      Wipe the paper account and start fresh
"""

import argparse
import os

from config import settings
from trader import Trader


def main() -> None:
    parser = argparse.ArgumentParser(description="Quant Regime Engine (QRE) paper-trading tool")
    parser.add_argument("--once", action="store_true", help="Run a single cycle and exit")
    parser.add_argument("--loop", action="store_true", help="Run continuously on a timer")
    parser.add_argument("--status", action="store_true", help="Show account, no trading")
    parser.add_argument("--reset", action="store_true", help="Delete the saved paper account")
    args = parser.parse_args()

    if args.reset:
        if os.path.exists(settings.state_file):
            os.remove(settings.state_file)
            print("Paper account reset.")
        else:
            print("No saved account to reset.")
        return

    trader = Trader(settings)

    if args.status:
        trader.print_status()
    elif args.loop:
        trader.run_loop()
    else:
        trader.run_once()


if __name__ == "__main__":
    main()
