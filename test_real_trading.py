#!/usr/bin/env python3
"""
Quick test for updated trade engine with order execution.
"""

import os
import logging
from trade_engine import TradeTracker, PAPER_TRADING

# Set paper trading
os.environ["PAPER_TRADING"] = "true"

logging.basicConfig(level=logging.INFO)

def test_real_trading_integration():
    print("Testing real trading integration...")
    tracker = TradeTracker(max_positions=5)

    # Test adding a trade (should place paper order)
    success = tracker.add_trade("TCS", "IT", 3500, 3450, 3600, 10)
    print(f"Add trade success: {success}")
    print(f"Paper trading mode: {PAPER_TRADING}")
    print(f"Tracker summary: {tracker.summary()}")

    # Test closing
    tracker.remove_trade("TCS")
    print(f"After close: {tracker.summary()}")

if __name__ == "__main__":
    test_real_trading_integration()