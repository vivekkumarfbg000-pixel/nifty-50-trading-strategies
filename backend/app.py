from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Adjust sys.path to include the root directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from trade_engine import TradeTracker

app = FastAPI(title="Trading Engine API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize TradeTracker
tracker = TradeTracker()

class TradeRequest(BaseModel):
    symbol: str
    quantity: int
    price: float
    broker: str = "FYERS"  # Default broker

class CloseTradeRequest(BaseModel):
    symbol: str
    broker: str = "FYERS"

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/positions")
async def get_positions():
    try:
        positions = tracker.active_trades
        return {"positions": positions, "count": tracker.open_count, "max": tracker._max_positions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/pnl")
async def get_pnl():
    try:
        return {
            "available_cash": tracker.available_cash,
            "open_positions": tracker.open_count,
            "total_pnl": 0.0,
            "win_rate": 0.0,
            "avg_pnl": 0.0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/open_trade")
async def open_trade(trade: TradeRequest):
    try:
        # Calculate stop loss and target based on entry price
        sl = trade.price * 0.98  # 2% stop loss
        tp = trade.price * 1.03  # 3% target
        
        result = tracker.add_trade(
            symbol=trade.symbol,
            sector="TECH",  # Default sector
            side="BUY",
            entry_price=trade.price,
            stop_loss=sl,
            target_price=tp,
            qty=trade.quantity,
            intraday=True
        )
        return {"message": "Trade opened" if result else "Trade rejected", "success": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/close_trade")
async def close_trade(close_req: CloseTradeRequest):
    try:
        tracker.remove_trade(close_req.symbol)
        return {"message": "Trade closed"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/candles/{symbol}")
async def get_candles(symbol: str, broker: str = "FYERS"):
    try:
        from trade_engine import fetch_candles
        candles = fetch_candles(symbol, timeframe="5min", days_back=5)
        return {"candles": candles.tail(50).to_dict(orient='records')}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/signals/{symbol}")
async def get_signals(symbol: str, broker: str = "FYERS"):
    try:
        from trade_engine import fetch_candles, compute_ema, compute_supertrend, compute_rsi
        
        df = fetch_candles(symbol, timeframe="5min", days_back=5)
        df = compute_ema(df)
        df = compute_supertrend(df)
        df = compute_rsi(df)
        
        latest = df.iloc[-1].to_dict()
        return {
            "symbol": symbol,
            "ema_fast": latest.get("EMA_FAST"),
            "ema_slow": latest.get("EMA_SLOW"),
            "supertrend": latest.get("SuperTrend"),
            "rsi": latest.get("RSI")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))