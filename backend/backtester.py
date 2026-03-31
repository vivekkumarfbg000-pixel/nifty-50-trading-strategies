import pandas as pd
import numpy as np
import datetime as dt
import logging
from typing import Dict, Any

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from trade_engine import fetch_candles, enrich_5min, enrich_15min, enrich_1h, check_entry_signals, calculate_position_size

logger = logging.getLogger("Backtester")

def run_backtest(symbol: str, days: int) -> Dict[str, Any]:
    """
    Simulates the exact entry/exit logic over historical data.
    """
    # 1. Fetch extensive historical data
    # To avoid API rate limits, we fetch the max allowed in one go.
    # In a full production app, this would be chunked over 2 years.
    try:
        # Fetch high timeframe data
        df_1h_all = fetch_candles(symbol, timeframe="1h", days_back=days + 15)
        df_15m_all = fetch_candles(symbol, timeframe="15min", days_back=days + 5)
        df_5m_all = fetch_candles(symbol, timeframe="5min", days_back=days)
        
        if df_5m_all.empty:
            return {"error": f"No data retrieved for {symbol}"}
            
        # Enrich all data
        df_1h_all = enrich_1h(df_1h_all)
        df_15m_all = enrich_15min(df_15m_all)
        df_5m_all = enrich_5min(df_5m_all)
        
    except Exception as e:
        logger.error(f"Backtest data fetch error: {e}")
        return {"error": str(e)}

    # 2. Simulation State Loop
    trades = []
    active_trade = None
    
    # Starting balance
    initial_cash = 200000.0
    current_cash = initial_cash

    # We iterate through the 5m dataframe row by row
    # This is slightly slow but structurally accurate to live trading
    for idx in range(25, len(df_5m_all)):
        current_5m_candle = df_5m_all.iloc[idx]
        current_time = current_5m_candle["datetime"]
        current_price = current_5m_candle["close"]
        
        # Monitor active trade
        if active_trade:
            # Check Stop Loss
            if current_5m_candle["low"] <= active_trade["stop_loss"]:
                exit_price = active_trade["stop_loss"]
                pnl = (exit_price - active_trade["entry_price"]) * active_trade["qty"]
                active_trade["exit_price"] = exit_price
                active_trade["pnl"] = round(pnl, 2)
                active_trade["closed_at"] = current_time.isoformat()
                active_trade["status"] = "SL_HIT"
                
                current_cash += pnl
                trades.append(active_trade)
                active_trade = None
                continue
                
            # Check Target
            elif current_5m_candle["high"] >= active_trade["target_price"]:
                exit_price = active_trade["target_price"]
                pnl = (exit_price - active_trade["entry_price"]) * active_trade["qty"]
                active_trade["exit_price"] = exit_price
                active_trade["pnl"] = round(pnl, 2)
                active_trade["closed_at"] = current_time.isoformat()
                active_trade["status"] = "TARGET_HIT"
                
                current_cash += pnl
                trades.append(active_trade)
                active_trade = None
                continue
                
            # Assume Intraday closure at 15:15 if trade still open
            if current_time.hour >= 15 and current_time.minute >= 15:
                exit_price = current_price
                pnl = (exit_price - active_trade["entry_price"]) * active_trade["qty"]
                active_trade["exit_price"] = exit_price
                active_trade["pnl"] = round(pnl, 2)
                active_trade["closed_at"] = current_time.isoformat()
                active_trade["status"] = "MARKET_CLOSE"
                
                current_cash += pnl
                trades.append(active_trade)
                active_trade = None
                
            continue # Only 1 trade allowed at a time for this asset
        
        # 3. Look for Entries (Only if time is < 15:00)
        if current_time.hour >= 15:
            continue
            
        # Get historical window up to current_time
        # In a real heavy-duty setup, we pre-calculate indicators, but check_entry_signals expects dataframes.
        # We pass small slices ending exactly at this candle.
        
        # optimization: use iloc indexing since df is sorted
        # Find index in large dataframe
        # df_1h_all[df_1h_all["datetime"] <= current_time]
        mask_1h = df_1h_all["datetime"] <= current_time
        df_1h_slice = df_1h_all.loc[mask_1h]
        
        mask_15m = df_15m_all["datetime"] <= current_time
        df_15m_slice = df_15m_all.loc[mask_15m]
        
        df_5m_slice = df_5m_all.iloc[:idx+1]
        
        signal = check_entry_signals(df_5m_slice, df_15m_slice, df_1h_slice)
        
        if signal:
            entry_price = signal["entry_price"]
            sl = signal["stop_loss"]
            position = calculate_position_size(entry_price, sl)
            
            if position:
                active_trade = {
                    "symbol": symbol,
                    "side": signal["signal"],
                    "entry_price": entry_price,
                    "stop_loss": sl,
                    "target_price": position["target_price"],
                    "qty": position["qty"],
                    "opened_at": current_time.isoformat(),
                    "status": "OPEN",
                    "margin_used": entry_price * position["qty"] * 0.20
                }

    # Close any remaining at end of backtest
    if active_trade:
        exit_price = current_price # Latest
        pnl = (exit_price - active_trade["entry_price"]) * active_trade["qty"]
        active_trade["exit_price"] = exit_price
        active_trade["pnl"] = round(pnl, 2)
        active_trade["closed_at"] = "END_OF_DATA"
        active_trade["status"] = "END_OF_BACKTEST"
        current_cash += pnl
        trades.append(active_trade)

    # 4. Generate Analytics
    total_trades = len(trades)
    if total_trades == 0:
        return {"error": "No trades executed during backtest period."}
        
    wins = [t for t in trades if t["pnl"] > 0]
    losses = [t for t in trades if t["pnl"] < 0]
    
    win_rate = (len(wins) / total_trades) * 100
    gross_profit = sum(t["pnl"] for t in wins)
    gross_loss = abs(sum(t["pnl"] for t in losses))
    profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else float("inf")
    
    # Calculate Max Drawdown from Equity Curve
    equity = initial_cash
    equity_curve = [{"time": trades[0]["opened_at"], "equity": equity}]
    peak = equity
    max_drawdown = 0
    
    for t in trades:
        equity += t["pnl"]
        equity_curve.append({"time": t["closed_at"], "equity": round(equity, 2)})
        if equity > peak:
            peak = equity
        drawdown = (peak - equity) / peak * 100
        if drawdown > max_drawdown:
            max_drawdown = drawdown

    total_return = ((equity - initial_cash) / initial_cash) * 100

    return {
        "summary": {
            "initial_capital": initial_cash,
            "final_equity": round(equity, 2),
            "total_return_pct": round(total_return, 2),
            "total_trades": total_trades,
            "win_rate_pct": round(win_rate, 2),
            "profit_factor": profit_factor,
            "max_drawdown_pct": round(max_drawdown, 2),
            "biggest_win": round(max([t["pnl"] for t in wins]) if wins else 0, 2),
            "biggest_loss": round(min([t["pnl"] for t in losses]) if losses else 0, 2),
            "period_days": days
        },
        "trades": list(reversed(trades)),
        "equity_curve": equity_curve
    }
