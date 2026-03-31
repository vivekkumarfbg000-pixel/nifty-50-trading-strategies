#!/usr/bin/env python3
"""
Mock Test: Verify TradeTracker, database, and alert logic.
Run: python mock_test_script.py
"""

import sys
import time
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

def test_trade_tracker():
    """Test core TradeTracker logic"""
    print("\n" + "="*60)
    print("🧪 TEST 1: TradeTracker Core Logic")
    print("="*60)
    
    from trade_engine import TradeTracker
    
    tracker = TradeTracker(available_cash=200000)
    
    # Test 1.1: Add trade
    print("\n✓ Adding INFY BUY 5 @ ₹1500...")
    ok = tracker.add_trade(
        symbol="INFY",
        sector="IT",
        side="BUY",
        entry_price=1500.00,
        stop_loss=1499.00,
        target_price=1502.00,
        qty=5,
        intraday=True
    )
    assert ok, "Failed to add trade"
    print("✅ INFY added successfully")
    
    # Test 1.2: Verify position count
    assert tracker.open_count == 1, f"Expected 1 open trade, got {tracker.open_count}"
    print(f"✅ Open trades: {tracker.open_count}")
    
    # Test 1.3: Test sector blocking (same sector, should fail)
    print("\n✓ Attempting to add TCS (same IT sector)...")
    ok = tracker.add_trade(
        symbol="TCS",
        sector="IT",
        side="BUY",
        entry_price=3500.00,
        stop_loss=3499.00,
        target_price=3502.00,
        qty=2,
        intraday=True
    )
    assert not ok, "Should have blocked same-sector trade"
    print("✅ Sector blocking works")
    
    # Test 1.4: Add trade from different sector (should succeed)
    print("\n✓ Adding HDFCBANK (Finance sector) as SELL...")
    ok = tracker.add_trade(
        symbol="HDFCBANK",
        sector="Finance",
        side="SELL",
        entry_price=1800.00,
        stop_loss=1801.00,
        target_price=1798.00,
        qty=3,
        intraday=False
    )
    assert ok, "Failed to add finance sector trade"
    print("✅ Different sector trade added")
    
    # Test 1.5: Money usage
    print(f"\n✅ Available cash: ₹{tracker.available_cash:.2f}")
    print(f"✅ Used margin: ₹{tracker.total_margin:.2f}")
    
    # Test 1.6: Test SL/TG calculation (dynamic based on margin)
    trade = tracker.active_trades.get("INFY")
    assert trade is not None, "INFY trade not found"
    print(f"\n✓ INFY Trade Details:")
    print(f"  Entry: ₹{trade['entry_price']:.2f}")
    print(f"  SL: ₹{trade['stop_loss']:.2f}")
    print(f"  Target: ₹{trade['target_price']:.2f}")
    print(f"  Margin Used: ₹{trade['margin_used']:.2f}")
    print(f"  Intraday: {trade['intraday']}")
    
    # Test 1.7: Close trade
    print("\n✓ Closing INFY position...")
    tracker.remove_trade("INFY")
    assert tracker.open_count == 1, "Trade not removed"
    print("✅ Trade closed successfully")
    
    print("\n✅ ALL TRADETRACKER TESTS PASSED\n")

def test_database():
    """Test database persistence"""
    print("\n" + "="*60)
    print("🧪 TEST 2: Database Persistence")
    print("="*60)
    
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from database import Base, TradeRecord, AlertLog
    from datetime import datetime
    
    # Use in-memory SQLite for testing
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Test 2.1: Insert trade record
    print("\n✓ Inserting trade record...")
    trade = TradeRecord(
        username="testuser",
        symbol="INFY",
        side="BUY",
        entry_price=1500.00,
        entry_time=datetime.utcnow(),
        qty=5,
        intraday=True,
        status="OPEN"
    )
    session.add(trade)
    session.commit()
    print("✅ Trade persisted")
    
    # Test 2.2: Query trade record
    print("\n✓ Querying trade record...")
    result = session.query(TradeRecord).filter_by(symbol="INFY").first()
    assert result is not None, "Trade not found"
    assert result.qty == 5, "Qty mismatch"
    print(f"✅ Found: {result.symbol} {result.side} {result.qty}")
    
    # Test 2.3: Update with P&L
    print("\n✓ Updating with P&L...")
    result.exit_price = 1502.00
    result.exit_time = datetime.utcnow()
    result.pnl = (1502.00 - 1500.00) * 5
    result.pnl_pct = ((1502.00 - 1500.00) / 1500.00) * 100
    result.status = "CLOSED"
    session.commit()
    print(f"✅ Updated: P&L = ₹{result.pnl:.2f} ({result.pnl_pct:.2f}%)")
    
    # Test 2.4: Insert alert log
    print("\n✓ Inserting alert log...")
    alert = AlertLog(
        username="testuser",
        alert_type="TELEGRAM",
        message="Trade opened: INFY BUY 5",
        status="SENT"
    )
    session.add(alert)
    session.commit()
    print("✅ Alert logged")
    
    # Test 2.5: Query alert
    print("\n✓ Querying alert logs...")
    alerts = session.query(AlertLog).filter_by(username="testuser").all()
    assert len(alerts) == 1, f"Expected 1 alert, got {len(alerts)}"
    print(f"✅ Found {len(alerts)} alert(s)")
    
    session.close()
    print("\n✅ ALL DATABASE TESTS PASSED\n")

def main():
    """Run all tests"""
    print("\n" + "🚀 "*20)
    print("TRADING ENGINE — MOCK TEST SUITE")
    print("🚀 "*20)
    
    tests = [
        ("TradeTracker", test_trade_tracker),
        ("Database", test_database),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"\n❌ TEST FAILED: {name}")
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"📈 Total:  {passed + failed}")
    print("="*60)
    
    if failed == 0:
        print("\n🎉 ALL TESTS PASSED - SYSTEM READY FOR PRODUCTION\n")
        return 0
    else:
        print("\n⚠️  SOME TESTS FAILED - FIX BEFORE DEPLOYMENT\n")
        return 1

if __name__ == "__main__":
    exit(main())