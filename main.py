"""
main.py — The entry point. Run this from the terminal.

Examples:
    python main.py --once       Run a single analysis cycle (great for testing)
    python main.py --loop       Run continuously on the timer in your .env
    python main.py --status     Show your paper account without trading
    python main.py --reset      Wipe the paper account and start fresh
"""

import argparse
import os

from config import settings
from trader import Trader


def main() -> None:
    parser = argparse.ArgumentParser(description="AI crypto paper-trading tool")
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

    # Everything below talks to the AI, so we need the key.
    settings.require_api_key()
    trader = Trader(settings)

    if args.status:
        trader.print_status()
    elif args.loop:
        trader.run_loop()
    else:
        # Default to a single cycle if no flag (or --once) is given.
        trader.run_once()


if __name__ == "__main__":
    main()
