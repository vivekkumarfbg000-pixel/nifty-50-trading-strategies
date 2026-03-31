import json
import os
from datetime import datetime

JOURNAL_FILE = os.path.join(os.path.dirname(__file__), "data", "journal.json")

def ensure_data_dir():
    os.makedirs(os.path.dirname(JOURNAL_FILE), exist_ok=True)

def load_journal():
    ensure_data_dir()
    if not os.path.exists(JOURNAL_FILE):
        return []
    try:
        with open(JOURNAL_FILE, "r") as f:
            return json.load(f)
    except:
        return []

def save_journal(trades):
    ensure_data_dir()
    with open(JOURNAL_FILE, "w") as f:
        json.dump(trades, f, indent=4)

def log_trade(trade_data):
    """
    trade_data should look like:
    {
        "symbol": "NSE:RELIANCE-EQ",
        "side": "BUY",
        "entry_price": 2500,
        "exit_price": 2550,
        "qty": 50,
        "pnl": 2500,
        "opened_at": "2023-10-25T10:15:00",
        "closed_at": "2023-10-25T14:30:00",
        "status": "TARGET_HIT"
    }
    """
    trades = load_journal()
    trades.append(trade_data)
    save_journal(trades)

def get_journal_summary():
    trades = load_journal()
    total_trades = len(trades)
    if total_trades == 0:
        return {
            "total_trades": 0,
            "win_rate": 0,
            "total_pnl": 0,
            "biggest_win": 0,
            "biggest_loss": 0,
        }
    
    wins = [t for t in trades if t["pnl"] > 0]
    losses = [t for t in trades if t["pnl"] < 0]
    
    win_rate = (len(wins) / total_trades) * 100 if total_trades > 0 else 0
    total_pnl = sum(t["pnl"] for t in trades)
    
    biggest_win = max([t["pnl"] for t in wins]) if wins else 0
    biggest_loss = min([t["pnl"] for t in losses]) if losses else 0
    
    return {
        "total_trades": total_trades,
        "win_rate": round(win_rate, 2),
        "total_pnl": round(total_pnl, 2),
        "biggest_win": round(biggest_win, 2),
        "biggest_loss": round(biggest_loss, 2),
    }

def get_all_trades():
    # Return reversed to show newest first
    return list(reversed(load_journal()))
