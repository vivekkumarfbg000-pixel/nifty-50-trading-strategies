#!/usr/bin/env python3
"""
================================================================================
 NIFTY 50 ALGORITHMIC TRADING ENGINE
 Author  : Senior Quant Dev
 Version : 1.1.0
 Purpose : Multi-timeframe technical analysis engine for Indian equity markets.
           Supports Fyers / Dhan API integration, strict ₹500 risk management,
           sector-diversified position sizing (max 5 concurrent trades, each in
           a unique sector), and clean logging output.
================================================================================
"""

import math
import logging
import datetime as dt
import os
from typing import Optional

import numpy as np
import pandas as pd
import pandas_ta as ta
import requests

# ─────────────────────────────────────────────────────────────────────────────
# LOGGING CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-8s │ %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("NiftyEngine")


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 1 — CONFIGURATION & CONSTANTS
# ═════════════════════════════════════════════════════════════════════════════

# ── Broker API credentials (fill before running) ────────────────────────────
BROKER = os.getenv("BROKER", "FYERS")  # "FYERS", "DHAN", or "UPSTOX"

FYERS_CONFIG = {
    "app_id":      os.getenv("FYERS_APP_ID", "YOUR_FYERS_APP_ID"),
    "secret_key":  os.getenv("FYERS_SECRET_KEY", "YOUR_FYERS_SECRET_KEY"),
    "access_token": os.getenv("FYERS_ACCESS_TOKEN", "YOUR_FYERS_ACCESS_TOKEN"),
    "base_url":    "https://api-t1.fyers.in/api/v3",
}

DHAN_CONFIG = {
    "access_token": os.getenv("DHAN_ACCESS_TOKEN", "YOUR_DHAN_ACCESS_TOKEN"),
    "client_id":    os.getenv("DHAN_CLIENT_ID", "YOUR_DHAN_CLIENT_ID"),
    "base_url":     "https://api.dhan.co",
}

UPSTOX_CONFIG = {
    "api_key":      os.getenv("UPSTOX_API_KEY", "YOUR_UPSTOX_API_KEY"),
    "api_secret":   os.getenv("UPSTOX_API_SECRET", "YOUR_UPSTOX_API_SECRET"),
    "access_token": os.getenv("UPSTOX_ACCESS_TOKEN", "YOUR_UPSTOX_ACCESS_TOKEN"),
    "redirect_uri": os.getenv("UPSTOX_REDIRECT_URI", "https://localhost/callback"),
    "use_sandbox":  os.getenv("UPSTOX_USE_SANDBOX", "true").lower() == "true",
}

UPSTOX_CONFIG["base_url"] = (
    "https://uat-api.upstox.com" if UPSTOX_CONFIG["use_sandbox"] else "https://api.upstox.com"
)


# ── Trading Mode ────────────────────────────────────────────────────────────
PAPER_TRADING = os.getenv("PAPER_TRADING", "true").lower() == "true"  # Default to paper trading

# ── Risk Management Constants ───────────────────────────────────────────────
MAX_RISK_PER_TRADE_INR = 200       # Desired risk per trade in INR
RISK_REWARD_RATIO      = 2.0       # 1:2  →  target = 2 × risk
TARGET_PROFIT_INR      = MAX_RISK_PER_TRADE_INR * RISK_REWARD_RATIO  # ₹400

# Margin multipliers for equity segment
INTRADAY_MARGIN_MULTIPLIER = 0.20  # 1/5 (20%) intraday leverage
DELIVERY_MARGIN_MULTIPLIER = 1.00  # 100% for delivery

# ── Portfolio Constraints ───────────────────────────────────────────────────
MAX_OPEN_POSITIONS     = 5         # Hard cap: exactly 5 concurrent trades max

# ── Market Timing (IST) ────────────────────────────────────────────────────
MARKET_OPEN  = dt.time(9, 15)
MARKET_CLOSE = dt.time(15, 30)

# ── Indicator Parameters ────────────────────────────────────────────────────
EMA_FAST           = 9
EMA_SLOW           = 21
SUPERTREND_LENGTH  = 7
SUPERTREND_MULT    = 3.0
RSI_PERIOD         = 14
BB_LENGTH          = 20
BB_STD             = 2.0
VOLUME_MA_PERIOD   = 20
VWAP_ANCHOR_HOUR   = 9
VWAP_ANCHOR_MIN    = 15


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 2 — NIFTY 50 UNIVERSE & SECTOR MAP
# ═════════════════════════════════════════════════════════════════════════════

NIFTY50_SECTOR_MAP: dict[str, str] = {
    # ── Information Technology ──────────────────────────────────────────────
    "NSE:TCS-EQ":        "IT",
    "NSE:INFY-EQ":       "IT",
    "NSE:HCLTECH-EQ":    "IT",
    "NSE:WIPRO-EQ":      "IT",
    "NSE:TECHM-EQ":      "IT",
    "NSE:LTIM-EQ":       "IT",

    # ── Banking ─────────────────────────────────────────────────────────────
    "NSE:HDFCBANK-EQ":   "Banking",
    "NSE:ICICIBANK-EQ":  "Banking",
    "NSE:KOTAKBANK-EQ":  "Banking",
    "NSE:SBIN-EQ":       "Banking",
    "NSE:AXISBANK-EQ":   "Banking",
    "NSE:INDUSINDBK-EQ": "Banking",

    # ── Financial Services ──────────────────────────────────────────────────
    "NSE:BAJFINANCE-EQ": "Financial Services",
    "NSE:BAJAJFINSV-EQ": "Financial Services",
    "NSE:HDFCLIFE-EQ":   "Financial Services",
    "NSE:SBILIFE-EQ":    "Financial Services",

    # ── Automobile ──────────────────────────────────────────────────────────
    "NSE:MARUTI-EQ":     "Auto",
    "NSE:TATAMOTORS-EQ": "Auto",
    "NSE:M&M-EQ":        "Auto",
    "NSE:BAJAJ-AUTO-EQ": "Auto",
    "NSE:EICHERMOT-EQ":  "Auto",
    "NSE:HEROMOTOCO-EQ": "Auto",

    # ── FMCG ────────────────────────────────────────────────────────────────
    "NSE:HINDUNILVR-EQ": "FMCG",
    "NSE:ITC-EQ":        "FMCG",
    "NSE:NESTLEIND-EQ":  "FMCG",
    "NSE:BRITANNIA-EQ":  "FMCG",
    "NSE:TATACONSUM-EQ": "FMCG",

    # ── Pharma & Healthcare ─────────────────────────────────────────────────
    "NSE:SUNPHARMA-EQ":  "Pharma",
    "NSE:DRREDDY-EQ":    "Pharma",
    "NSE:CIPLA-EQ":      "Pharma",
    "NSE:APOLLOHOSP-EQ": "Pharma",
    "NSE:DIVISLAB-EQ":   "Pharma",

    # ── Metals & Mining ─────────────────────────────────────────────────────
    "NSE:TATASTEEL-EQ":  "Metals",
    "NSE:JSWSTEEL-EQ":   "Metals",
    "NSE:HINDALCO-EQ":   "Metals",
    "NSE:COALINDIA-EQ":  "Metals",

    # ── Oil & Gas / Energy ──────────────────────────────────────────────────
    "NSE:RELIANCE-EQ":   "Energy",
    "NSE:ONGC-EQ":       "Energy",
    "NSE:BPCL-EQ":       "Energy",
    "NSE:NTPC-EQ":       "Energy",
    "NSE:POWERGRID-EQ":  "Energy",
    "NSE:ADANIENT-EQ":   "Energy",

    # ── Telecom ─────────────────────────────────────────────────────────────
    "NSE:BHARTIARTL-EQ": "Telecom",

    # ── Infrastructure / Capital Goods ──────────────────────────────────────
    "NSE:LT-EQ":         "Infra",
    "NSE:ULTRACEMCO-EQ": "Infra",
    "NSE:GRASIM-EQ":     "Infra",
    "NSE:ADANIPORTS-EQ": "Infra",
    "NSE:SHRIRAMFIN-EQ": "Infra",

    # ── Consumer Durables ───────────────────────────────────────────────────
    "NSE:TITAN-EQ":      "Consumer Durables",
    "NSE:ASIANPAINT-EQ": "Consumer Durables",

    # ── Diversified / Conglomerate ──────────────────────────────────────────
    "NSE:WIPRO-EQ":       "IT",   # already mapped, kept for count
    "NSE:HDFC-EQ":        "Financial Services",
}


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 3 — ACTIVE TRADE TRACKER  (in-memory state)
# ═════════════════════════════════════════════════════════════════════════════

class TradeTracker:
    """
    Maintains a dictionary of currently open trades keyed by symbol.
    Enforces:
      • Maximum of MAX_OPEN_POSITIONS (5) concurrent trades.
      • Each active trade must belong to a unique sector.
    """

    def __init__(
        self,
        max_positions: int = MAX_OPEN_POSITIONS,
        available_cash: float = 200000.0,
        intraday_margin: float = INTRADAY_MARGIN_MULTIPLIER,
        delivery_margin: float = DELIVERY_MARGIN_MULTIPLIER,
    ) -> None:
        self._active: dict[str, dict] = {}
        self._max_positions = max_positions
        self.available_cash = available_cash
        self.intraday_margin = intraday_margin
        self.delivery_margin = delivery_margin

    # ── public API ──────────────────────────────────────────────────────────
    def _required_margin(self, entry_price: float, qty: int, intraday: bool) -> float:
        multiplier = self.intraday_margin if intraday else self.delivery_margin
        return entry_price * qty * multiplier

    def add_trade(
        self,
        symbol: str,
        sector: str,
        side: str,
        entry_price: float,
        stop_loss: float,
        target_price: float,
        qty: int,
        intraday: bool = True,
    ) -> bool:
        """
        Register a new trade. In equity mode, calculates intraday/delivery margin and places orders.
        """
        if self.is_portfolio_full:
            logger.warning(
                "REJECTED      │ %s │ Portfolio is FULL (%d/%d positions)",
                symbol, self.open_count, self._max_positions,
            )
            return False

        required_margin = self._required_margin(entry_price, qty, intraday)
        if required_margin > self.available_cash:
            logger.warning(
                "REJECTED      │ %s │ Insufficient margin (required=%.2f, available=%.2f)",
                symbol, required_margin, self.available_cash,
            )
            return False

        order_id = place_order(symbol, side, qty, entry_price, "MARKET" if PAPER_TRADING else "LIMIT", intraday)
        if order_id is None:
            logger.error("ORDER FAILED │ %s │ Could not place %s order", symbol, side)
            return False

        self.available_cash -= required_margin
        self._active[symbol] = {
            "sector": sector,
            "side": side,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "target_price": target_price,
            "qty": qty,
            "intraday": intraday,
            "margin_used": required_margin,
            "order_id": order_id,
            "opened_at": dt.datetime.now(),
        }
        logger.info(
            "TRADE OPENED  │ %s │ side=%s │ segment=EQUITY │ mode=%s │ qty=%d │ entry=%.2f │ sl=%.2f │ tgt=%.2f │ margin=%.2f │ avail=%.2f │ slots=%d/%d",
            symbol,
            side,
            "INTRADAY" if intraday else "DELIVERY",
            qty,
            entry_price,
            stop_loss,
            target_price,
            required_margin,
            self.available_cash,
            self.open_count,
            self._max_positions,
        )
        return True

    def remove_trade(self, symbol: str, reason: str = "MANUAL_CLOSE", current_price: float = None) -> None:
        if symbol in self._active:
            trade = self._active[symbol]
            sector = trade["sector"]
            qty = trade["qty"]
            intraday = trade.get("intraday", True)
            margin_used = trade.get("margin_used", 0.0)
            entry_price = trade["entry_price"]
            side = trade.get("side", "BUY")

            # Try to fetch current price if passed in
            exit_price = current_price if current_price else entry_price 

            # Calculate actual PnL
            if side == "BUY":
                pnl = (exit_price - entry_price) * qty
            else:
                pnl = (entry_price - exit_price) * qty

            # Determine side for balance update: if we bought, we close with SELL; if we shorted, we close with BUY
            close_side = "SELL" if side == "BUY" else "BUY"
            order_id = place_order(symbol, close_side, qty, 0, "MARKET", intraday)
            if order_id is None:
                logger.error("CLOSE FAILED │ %s │ Could not place %s order", symbol, close_side)
                return

            # Log to Daily Journal
            try:
                # Add to back end path to import
                import sys
                import os
                backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
                if backend_dir not in sys.path:
                    sys.path.append(backend_dir)
                from backend.journal import log_trade
                
                log_trade({
                    "symbol": symbol,
                    "side": side,
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "qty": qty,
                    "pnl": round(pnl, 2),
                    "opened_at": trade["opened_at"].isoformat() if hasattr(trade["opened_at"], "isoformat") else str(trade["opened_at"]),
                    "closed_at": dt.datetime.now().isoformat(),
                    "status": reason,
                    "margin_used": margin_used
                })
            except Exception as e:
                logger.error(f"Failed to log trade to journal: {e}")

            # Restore margin and accrued PnL on close
            self.available_cash += (margin_used + pnl)
            del self._active[symbol]

            logger.info(
                "TRADE CLOSED  │ %s │ side=%s │ sector=%s │ reason=%s │ PnL=%.2f │ cash=%.2f",
                symbol,
                side,
                sector,
                reason,
                pnl,
                self.available_cash,
            )

    def has_sector_exposure(self, sector: str) -> bool:
        """Return True if there is already an active trade in this sector."""
        return any(t["sector"] == sector for t in self._active.values())

    def is_symbol_active(self, symbol: str) -> bool:
        return symbol in self._active

    def is_trade_allowed(self, symbol: str, sector: str) -> bool:
        """Check if a new trade can be placed under current risk rules."""
        if self.is_symbol_active(symbol):
            return False
        if self.has_sector_exposure(sector):
            return False
        if self.is_portfolio_full:
            return False
        return True

    @property
    def is_portfolio_full(self) -> bool:
        """Return True when the maximum concurrent position limit is reached."""
        return len(self._active) >= self._max_positions

    @property
    def open_count(self) -> int:
        """Number of currently open positions."""
        return len(self._active)

    @property
    def active_sectors(self) -> set[str]:
        """Set of sectors that currently have an active trade."""
        return {t["sector"] for t in self._active.values()}

    @property
    def active_trades(self) -> dict[str, dict]:
        return dict(self._active)

    def summary(self) -> str:
        """Return a human-readable summary of portfolio state."""
        return (
            f"Open: {self.open_count}/{self._max_positions} │ "
            f"Sectors: {', '.join(sorted(self.active_sectors)) or 'none'}"
        )

    # backward-compatible alias
    can_open_trade = is_trade_allowed


# Global singleton
trade_tracker = TradeTracker(max_positions=MAX_OPEN_POSITIONS)


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 3.5 — TRADE MONITORING & RISK MANAGEMENT
# ═════════════════════════════════════════════════════════════════════════════

def monitor_and_close_trades(current_prices: dict[str, float]) -> None:
    """
    Check active trades against current prices and close if stop-loss or target hit.
    current_prices: dict of symbol -> current price
    Thread-safe: makes copy to avoid race condition during iteration
    """
    to_close = []
    # Make a copy to avoid race condition if _active is modified during iteration
    active_copy = dict(trade_tracker.active_trades)
    
    for symbol, trade in active_copy.items():
        current_price = current_prices.get(symbol)
        if current_price is None:
            continue
        
        if current_price <= trade["stop_loss"]:
            logger.info("STOP LOSS HIT │ %s │ current=%.2f <= sl=%.2f", symbol, current_price, trade["stop_loss"])
            to_close.append((symbol, "SL_HIT", current_price))
        elif current_price >= trade["target_price"]:
            logger.info("TARGET HIT │ %s │ current=%.2f >= tgt=%.2f", symbol, current_price, trade["target_price"])
            to_close.append((symbol, "TARGET_HIT", current_price))

    for symbol, reason, price in to_close:
        trade_tracker.remove_trade(symbol, reason=reason, current_price=price)


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 4 — BROKER DATA FETCH LAYER
# ═════════════════════════════════════════════════════════════════════════════

def _epoch(d: dt.datetime) -> int:
    """Convert a datetime to UNIX epoch (seconds)."""
    return int(d.timestamp())


def _fyers_resolution(timeframe: str) -> str:
    """Map human-readable timeframe to Fyers resolution string."""
    mapping = {"5min": "5", "15min": "15", "1h": "60"}
    return mapping.get(timeframe, "5")


def _dhan_resolution(timeframe: str) -> str:
    """Map human-readable timeframe to Dhan resolution string."""
    mapping = {"5min": "5", "15min": "15", "1h": "60"}
    return mapping.get(timeframe, "5")


def fetch_candles_fyers(
    symbol: str,
    timeframe: str = "5min",
    days_back: int = 5,
) -> pd.DataFrame:
    """
    Fetch OHLCV candle data from the Fyers v3 API.

    Parameters
    ----------
    symbol    : Fyers-format symbol, e.g. "NSE:RELIANCE-EQ"
    timeframe : "5min" | "15min" | "1h"
    days_back : number of calendar days of history to request

    Returns
    -------
    pd.DataFrame with columns: datetime, open, high, low, close, volume
    """
    end   = dt.datetime.now()
    start = end - dt.timedelta(days=days_back)

    url = f"{FYERS_CONFIG['base_url']}/history"
    headers = {"Authorization": f"{FYERS_CONFIG['app_id']}:{FYERS_CONFIG['access_token']}"}
    params = {
        "symbol":     symbol,
        "resolution":  _fyers_resolution(timeframe),
        "date_format": "0",
        "range_from":  _epoch(start),
        "range_to":    _epoch(end),
        "cont_flag":   "1",
    }

    logger.debug("FYERS request │ %s │ tf=%s │ %s → %s", symbol, timeframe, start.date(), end.date())

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        if data.get("s") != "ok" or "candles" not in data:
            logger.warning("FYERS returned non-ok: %s", data.get("message", "unknown"))
            return pd.DataFrame()

        df = pd.DataFrame(
            data["candles"],
            columns=["epoch", "open", "high", "low", "close", "volume"],
        )
        df["datetime"] = pd.to_datetime(df["epoch"], unit="s", utc=True)
        df["datetime"] = df["datetime"].dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)
        df = df.drop(columns=["epoch"]).sort_values("datetime").reset_index(drop=True)
        return df

    except requests.RequestException as exc:
        logger.error("FYERS API error for %s: %s", symbol, exc)
        return pd.DataFrame()


def fetch_candles_dhan(
    symbol: str,
    timeframe: str = "5min",
    days_back: int = 5,
) -> pd.DataFrame:
    """
    Fetch OHLCV candle data from the Dhan API.

    Parameters
    ----------
    symbol    : Dhan instrument token / identifier
    timeframe : "5min" | "15min" | "1h"
    days_back : number of calendar days of history to request

    Returns
    -------
    pd.DataFrame with columns: datetime, open, high, low, close, volume
    """
    end   = dt.datetime.now()
    start = end - dt.timedelta(days=days_back)

    url = f"{DHAN_CONFIG['base_url']}/charts/intraday"
    headers = {
        "access-token": DHAN_CONFIG["access_token"],
        "client-id":    DHAN_CONFIG["client_id"],
        "Content-Type": "application/json",
    }
    payload = {
        "securityId":    symbol,
        "exchangeSegment": "NSE_EQ",
        "instrument":    "EQUITY",
        "interval":      _dhan_resolution(timeframe),
        "fromDate":      start.strftime("%Y-%m-%d"),
        "toDate":        end.strftime("%Y-%m-%d"),
    }

    logger.debug("DHAN request │ %s │ tf=%s │ %s → %s", symbol, timeframe, start.date(), end.date())

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        if not data.get("open"):
            logger.warning("DHAN returned empty candles for %s", symbol)
            return pd.DataFrame()

        df = pd.DataFrame({
            "datetime": pd.to_datetime(data["timestamp"], unit="s"),
            "open":     data["open"],
            "high":     data["high"],
            "low":      data["low"],
            "close":    data["close"],
            "volume":   data["volume"],
        })
        df = df.sort_values("datetime").reset_index(drop=True)
        return df

    except requests.RequestException as exc:
        logger.error("DHAN API error for %s: %s", symbol, exc)
        return pd.DataFrame()


def _upstox_resolution(timeframe: str) -> str:
    mapping = {"5min": "5minute", "15min": "15minute", "1h": "60minute"}
    return mapping.get(timeframe, "5minute")


def fetch_candles_upstox(symbol: str, timeframe: str = "5min", days_back: int = 5) -> pd.DataFrame:
    """Fetch OHLCV candles via Upstox API (sandbox or production)."""
    end = dt.datetime.now()
    start = end - dt.timedelta(days=days_back)

    url = f"{UPSTOX_CONFIG['base_url']}/quotes/historical?symbol={symbol}&interval={_upstox_resolution(timeframe)}&start_date={start.strftime('%Y-%m-%d')}&end_date={end.strftime('%Y-%m-%d')}"
    headers = {
        "Authorization": f"Bearer {UPSTOX_CONFIG['access_token']}",
        "Content-Type": "application/json",
    }

    logger.debug("UPSTOX request │ %s │ tf=%s │ %s → %s", symbol, timeframe, start.date(), end.date())
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        candles = data.get("data") or data.get("candles") or []
        if not candles:
            logger.warning("UPSTOX returned empty candles for %s", symbol)
            return pd.DataFrame()

        df = pd.DataFrame(candles)
        if "timestamp" in df.columns:
            df["datetime"] = pd.to_datetime(df["timestamp"], unit="s")
        elif "date" in df.columns:
            df["datetime"] = pd.to_datetime(df["date"])

        for col in ["open", "high", "low", "close", "volume"]:
            if col not in df.columns:
                logger.error("Upstox data missing %s", col)
                return pd.DataFrame()

        df = df[["datetime", "open", "high", "low", "close", "volume"]]
        df = df.sort_values("datetime").reset_index(drop=True)
        return df

    except requests.RequestException as exc:
        logger.error("UPSTOX API error for %s: %s", symbol, exc)
        return pd.DataFrame()


def fetch_candles(symbol: str, timeframe: str = "5min", days_back: int = 5) -> pd.DataFrame:
    """Unified data fetch dispatcher based on active BROKER setting."""
    if BROKER == "FYERS":
        return fetch_candles_fyers(symbol, timeframe, days_back)
    elif BROKER == "DHAN":
        return fetch_candles_dhan(symbol, timeframe, days_back)
    elif BROKER == "UPSTOX":
        return fetch_candles_upstox(symbol, timeframe, days_back)
    else:
        logger.error("Unknown broker: %s", BROKER)
        return pd.DataFrame()


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 4.5 — ORDER EXECUTION (REAL TRADING)
# ═════════════════════════════════════════════════════════════════════════════

def place_order_fyers(
    symbol: str,
    side: str,  # "BUY" or "SELL"
    qty: int,
    price: float,
    order_type: str = "LIMIT",  # "LIMIT", "MARKET", etc.
) -> Optional[str]:
    """
    Place an order via FYERS API.
    Returns order ID on success, None on failure.
    """
    if PAPER_TRADING:
        logger.info("PAPER TRADE │ FYERS │ %s %d %s @ %.2f", side, qty, symbol, price)
        return f"paper_{dt.datetime.now().timestamp()}"

    url = f"{FYERS_CONFIG['base_url']}/orders"
    headers = {"Authorization": f"{FYERS_CONFIG['app_id']}:{FYERS_CONFIG['access_token']}"}
    payload = {
        "symbol": symbol,
        "qty": qty,
        "type": order_type,
        "side": side,
        "productType": "INTRADAY",  # Adjust as needed
        "limitPrice": price if order_type == "LIMIT" else 0,
        "stopPrice": 0,
        "disclosedQty": 0,
        "validity": "DAY",
        "offlineOrder": False,
        "stopLoss": 0,
        "takeProfit": 0,
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data.get("s") == "ok":
            order_id = data["id"]
            logger.info("ORDER PLACED │ FYERS │ %s │ ID: %s", symbol, order_id)
            return order_id
        else:
            logger.error("FYERS order failed: %s", data.get("message"))
            return None
    except requests.RequestException as exc:
        logger.error("FYERS order API error: %s", exc)
        return None


def place_order_dhan(
    symbol: str,
    side: str,  # "BUY" or "SELL"
    qty: int,
    price: float,
    order_type: str = "LIMIT",
) -> Optional[str]:
    """
    Place an order via DHAN API.
    Returns order ID on success, None on failure.
    """
    if PAPER_TRADING:
        logger.info("PAPER TRADE │ DHAN │ %s %d %s @ %.2f", side, qty, symbol, price)
        return f"paper_{dt.datetime.now().timestamp()}"

    url = f"{DHAN_CONFIG['base_url']}/orders"
    headers = {
        "access-token": DHAN_CONFIG["access_token"],
        "client-id": DHAN_CONFIG["client_id"],
        "Content-Type": "application/json",
    }
    payload = {
        "transactionType": side,
        "exchangeSegment": "NSE_EQ",
        "productType": "INTRADAY",
        "orderType": order_type,
        "validity": "DAY",
        "securityId": symbol,
        "quantity": qty,
        "price": price if order_type == "LIMIT" else 0,
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") == "success":
            order_id = data.get("orderId")
            logger.info("ORDER PLACED │ DHAN │ %s │ ID: %s", symbol, order_id)
            return order_id
        else:
            logger.error("DHAN order failed: %s", data.get("remarks"))
            return None
    except requests.RequestException as exc:
        logger.error("DHAN order API error: %s", exc)
        return None


def place_order_upstox(
    symbol: str,
    side: str,
    qty: int,
    price: float,
    order_type: str = "MARKET",
    product_type: str = "MIS",  # MIS for intraday, CNC for delivery
) -> Optional[str]:
    """Place an order via Upstox API."""
    if PAPER_TRADING:
        logger.info("PAPER TRADE │ UPSTOX │ %s %d %s @ %.2f", side, qty, symbol, price)
        return f"paper_{dt.datetime.now().timestamp()}"

    url = f"{UPSTOX_CONFIG['base_url']}/orders"
    headers = {
        "Authorization": f"Bearer {UPSTOX_CONFIG['access_token']}",
        "Content-Type": "application/json",
    }

    payload = {
        "symbol": symbol,
        "quantity": qty,
        "side": side.upper(),
        "type": order_type.upper(),
        "product": product_type.upper(),
        "price": price if order_type.upper() == "LIMIT" else 0,
        "validity": "DAY",
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        order_id = data.get("order_id") or data.get("id") or data.get("OrderID")
        if order_id:
            logger.info("ORDER PLACED │ UPSTOX │ %s │ ID: %s", symbol, order_id)
            return str(order_id)
        logger.error("UPSTOX order failed: %s", data)
        return None

    except requests.RequestException as exc:
        logger.error("UPSTOX order API error: %s", exc)
        return None


def place_order(
    symbol: str,
    side: str,
    qty: int,
    price: float,
    order_type: str = "LIMIT",
    intraday: bool = True,
) -> Optional[str]:
    """Unified order placement dispatcher."""
    if BROKER == "FYERS":
        return place_order_fyers(symbol, side, qty, price, order_type)
    elif BROKER == "DHAN":
        return place_order_dhan(symbol, side, qty, price, order_type)
    elif BROKER == "UPSTOX":
        product_type = "MIS" if intraday else "CNC"
        return place_order_upstox(symbol, side, qty, price, order_type, product_type)
    else:
        logger.error("Unknown broker for order: %s", BROKER)
        return None


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 5 — TECHNICAL INDICATOR CALCULATIONS
# ═════════════════════════════════════════════════════════════════════════════

def compute_ema(df: pd.DataFrame, fast: int = EMA_FAST, slow: int = EMA_SLOW) -> pd.DataFrame:
    """Append EMA fast & slow columns to the dataframe."""
    df[f"ema_{fast}"] = ta.ema(df["close"], length=fast)
    df[f"ema_{slow}"] = ta.ema(df["close"], length=slow)
    return df


def compute_supertrend(
    df: pd.DataFrame,
    length: int = SUPERTREND_LENGTH,
    multiplier: float = SUPERTREND_MULT,
) -> pd.DataFrame:
    """
    Append Supertrend direction column.
    SUPERTd_{length}_{multiplier}:  1 = bullish,  -1 = bearish
    """
    st = ta.supertrend(df["high"], df["low"], df["close"], length=length, multiplier=multiplier)
    if st is not None and not st.empty:
        # pandas-ta returns columns like SUPERT_7_3.0, SUPERTd_7_3.0, etc.
        direction_col = f"SUPERTd_{length}_{multiplier}"
        value_col     = f"SUPERT_{length}_{multiplier}"
        if direction_col in st.columns:
            df["supertrend_dir"] = st[direction_col].values
        if value_col in st.columns:
            df["supertrend_val"] = st[value_col].values
    return df


def compute_rsi(df: pd.DataFrame, period: int = RSI_PERIOD) -> pd.DataFrame:
    """Append RSI column."""
    df["rsi"] = ta.rsi(df["close"], length=period)
    return df


def compute_bollinger_bands(
    df: pd.DataFrame,
    length: int = BB_LENGTH,
    std: float = BB_STD,
) -> pd.DataFrame:
    """Append Bollinger Band columns: bb_upper, bb_mid, bb_lower."""
    bb = ta.bbands(df["close"], length=length, std=std)
    if bb is not None and not bb.empty:
        df["bb_lower"]  = bb.iloc[:, 0].values
        df["bb_mid"]    = bb.iloc[:, 1].values
        df["bb_upper"]  = bb.iloc[:, 2].values
    return df


def compute_vwap(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute intraday VWAP using pandas-ta.
    Resets each trading day at 09:15 IST.
    """
    vwap_series = ta.vwap(df["high"], df["low"], df["close"], df["volume"])
    if vwap_series is not None:
        df["vwap"] = vwap_series.values
    return df


def compute_anchored_vwap(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute Anchored VWAP anchored to the 09:15 candle of the previous
    trading day.  The anchor resets at each new day's open.

    Formula:  A-VWAP = cumsum(typical_price × volume) / cumsum(volume)
              where typical_price = (high + low + close) / 3
              anchored from the previous day's 09:15 candle onward.
    """
    df = df.copy()
    df["typical_price"] = (df["high"] + df["low"] + df["close"]) / 3.0
    df["tp_x_vol"]      = df["typical_price"] * df["volume"]

    # Identify the 09:15 candle of the previous trading day as anchor
    df["date"] = df["datetime"].dt.date
    unique_dates = sorted(df["date"].unique())

    df["anchored_vwap"] = np.nan

    if len(unique_dates) < 2:
        logger.warning("Not enough days for Anchored VWAP; need ≥ 2 days of data.")
        return df

    prev_day = unique_dates[-2]

    # Anchor index: first candle of previous day (09:15)
    anchor_mask = df["date"] >= prev_day
    anchor_df   = df.loc[anchor_mask].copy()

    cum_tp_vol = anchor_df["tp_x_vol"].cumsum()
    cum_vol    = anchor_df["volume"].cumsum().replace(0, np.nan)
    anchor_df["anchored_vwap"] = cum_tp_vol / cum_vol

    df.loc[anchor_mask, "anchored_vwap"] = anchor_df["anchored_vwap"].values

    df.drop(columns=["typical_price", "tp_x_vol", "date"], inplace=True)
    return df


def compute_pivot_points(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate classic pivot points from the previous day's HLC.
    Adds columns: pivot, r1, r2, r3, s1, s2, s3
    """
    df = df.copy()
    df["date"] = df["datetime"].dt.date
    unique_dates = sorted(df["date"].unique())

    df["pivot"] = np.nan
    df["r1"] = np.nan
    df["r2"] = np.nan
    df["r3"] = np.nan
    df["s1"] = np.nan
    df["s2"] = np.nan
    df["s3"] = np.nan

    if len(unique_dates) < 2:
        logger.warning("Not enough days for Pivot Points calculation.")
        df.drop(columns=["date"], inplace=True)
        return df

    for i in range(1, len(unique_dates)):
        prev = unique_dates[i - 1]
        curr = unique_dates[i]
        prev_data = df[df["date"] == prev]
        curr_mask = df["date"] == curr

        p_high  = prev_data["high"].max()
        p_low   = prev_data["low"].min()
        p_close = prev_data["close"].iloc[-1]

        pivot = (p_high + p_low + p_close) / 3.0
        r1 = 2 * pivot - p_low
        s1 = 2 * pivot - p_high
        r2 = pivot + (p_high - p_low)
        s2 = pivot - (p_high - p_low)
        r3 = p_high + 2 * (pivot - p_low)
        s3 = p_low - 2 * (p_high - pivot)

        df.loc[curr_mask, "pivot"] = pivot
        df.loc[curr_mask, "r1"]    = r1
        df.loc[curr_mask, "s1"]    = s1
        df.loc[curr_mask, "r2"]    = r2
        df.loc[curr_mask, "s2"]    = s2
        df.loc[curr_mask, "r3"]    = r3
        df.loc[curr_mask, "s3"]    = s3

    df.drop(columns=["date"], inplace=True)
    return df


def compute_volume_validation(df: pd.DataFrame, period: int = VOLUME_MA_PERIOD) -> pd.DataFrame:
    """
    Append a boolean column 'volume_ok' that is True when the current
    candle's volume exceeds the 20-period simple moving average of volume.
    """
    df["vol_ma"] = df["volume"].rolling(window=period).mean()
    df["volume_ok"] = df["volume"] > df["vol_ma"]
    return df


# ── Master enrichment pipelines ────────────────────────────────────────────

def enrich_5min(df: pd.DataFrame) -> pd.DataFrame:
    """Apply all 5-min indicators: VWAP, Anchored VWAP, RSI, BB, Pivots, Volume."""
    if df.empty:
        return df
    df = compute_vwap(df)
    df = compute_anchored_vwap(df)
    df = compute_rsi(df)
    df = compute_bollinger_bands(df)
    df = compute_pivot_points(df)
    df = compute_volume_validation(df)
    return df


def enrich_15min(df: pd.DataFrame) -> pd.DataFrame:
    """Apply 15-min indicators: EMA(9,21) and Supertrend(7,3)."""
    if df.empty:
        return df
    df = compute_ema(df)
    df = compute_supertrend(df)
    return df


def enrich_1h(df: pd.DataFrame) -> pd.DataFrame:
    """Apply 1-hour indicators: EMA(9,21) and Supertrend(7,3)."""
    if df.empty:
        return df
    df = compute_ema(df)
    df = compute_supertrend(df)
    return df


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 6 — ENTRY SIGNAL LOGIC  (PLACEHOLDER — CUSTOMISE HERE)
# ═════════════════════════════════════════════════════════════════════════════

def check_entry_signals(
    df_5m: pd.DataFrame,
    df_15m: pd.DataFrame,
    df_1h: pd.DataFrame,
) -> dict | None:
    """
    Evaluate multi-timeframe confluence to generate a LONG entry signal.

    Returns
    -------
    dict  {"signal": "BUY"/"SELL", "entry_price": float, "stop_loss": float}
    None  if no valid signal

    ╔══════════════════════════════════════════════════════════════════╗
    ║  CUSTOMISATION GUIDE                                           ║
    ║  ─────────────────                                             ║
    ║  Modify the conditions below to tweak your crossover logic.    ║
    ║  Each block is labelled for easy identification.               ║
    ╚══════════════════════════════════════════════════════════════════╝
    """

    # Bail early if any dataframe is too small
    if df_5m.empty or df_15m.empty or df_1h.empty:
        return None
    if len(df_5m) < 25 or len(df_15m) < 25 or len(df_1h) < 25:
        return None

    # ── Grab the latest row from each timeframe ─────────────────────────
    row_5m  = df_5m.iloc[-1]
    row_15m = df_15m.iloc[-1]
    row_1h  = df_1h.iloc[-1]

    # Also grab the prior row for crossover detection
    prev_5m  = df_5m.iloc[-2]
    prev_15m = df_15m.iloc[-2]

    # ────────────────────────────────────────────────────────────────────
    # FILTER 1:  1-HOUR MACRO TREND ALIGNMENT
    # The 1h EMA(9) must be above EMA(21) AND Supertrend must be bullish.
    # ────────────────────────────────────────────────────────────────────
    hourly_bullish = (
        row_1h.get("ema_9", 0) > row_1h.get("ema_21", 0)
        and row_1h.get("supertrend_dir", -1) == 1
    )
    if not hourly_bullish:
        return None

    # ────────────────────────────────────────────────────────────────────
    # FILTER 2:  15-MIN TREND CONFIRMATION
    # The 15m EMA(9) must be above EMA(21) AND Supertrend must be bullish.
    # ────────────────────────────────────────────────────────────────────
    fifteen_bullish = (
        row_15m.get("ema_9", 0) > row_15m.get("ema_21", 0)
        and row_15m.get("supertrend_dir", -1) == 1
    )
    if not fifteen_bullish:
        return None

    # ────────────────────────────────────────────────────────────────────
    # FILTER 3:  5-MIN VOLUME VALIDATION
    # Current candle volume must exceed the 20-period volume MA.
    # ────────────────────────────────────────────────────────────────────
    if not row_5m.get("volume_ok", False):
        return None

    # ────────────────────────────────────────────────────────────────────
    # FILTER 4:  5-MIN RSI CHECK
    # RSI must be between 40 and 70 (not overbought, not oversold).
    # TODO: Adjust RSI thresholds to your preference.
    # ────────────────────────────────────────────────────────────────────
    rsi_val = row_5m.get("rsi", 50)
    if not (40 < rsi_val < 70):
        return None

    # ────────────────────────────────────────────────────────────────────
    # FILTER 5:  PRICE vs VWAP / ANCHORED VWAP
    # Price must be above both VWAP and Anchored VWAP for bullish bias.
    # TODO: You can invert these for SHORT signals.
    # ────────────────────────────────────────────────────────────────────
    close_5m = row_5m["close"]
    vwap_val = row_5m.get("vwap", 0)
    a_vwap   = row_5m.get("anchored_vwap", 0)

    if close_5m <= vwap_val or (not np.isnan(a_vwap) and close_5m <= a_vwap):
        return None

    # ────────────────────────────────────────────────────────────────────
    # FILTER 6:  BOLLINGER BAND POSITION
    # Entry near the middle or lower band is preferred (room to expand).
    # Reject if price is already touching the upper band.
    # TODO: Customise BB logic as needed.
    # ────────────────────────────────────────────────────────────────────
    bb_upper = row_5m.get("bb_upper", float("inf"))
    if close_5m >= bb_upper:
        return None

    # ────────────────────────────────────────────────────────────────────
    # SIGNAL GENERATION
    # If all filters pass → generate a BUY signal.
    # Entry  = current 5-min close
    # Stop   = max(Supertrend value on 15m, Pivot S1, lower BB)
    #          Choose the tightest (highest) SL that makes sense.
    # TODO: Implement your preferred SL logic below.
    # ────────────────────────────────────────────────────────────────────
    entry_price = close_5m

    # Candidate stop-loss levels (use the highest one for tightest risk)
    sl_candidates = []

    supertrend_15m = row_15m.get("supertrend_val", None)
    if supertrend_15m and not np.isnan(supertrend_15m):
        sl_candidates.append(supertrend_15m)

    pivot_s1 = row_5m.get("s1", None)
    if pivot_s1 and not np.isnan(pivot_s1):
        sl_candidates.append(pivot_s1)

    bb_lower = row_5m.get("bb_lower", None)
    if bb_lower and not np.isnan(bb_lower):
        sl_candidates.append(bb_lower)

    if not sl_candidates:
        return None

    # Tightest SL = the highest candidate below entry
    valid_sl = [s for s in sl_candidates if s < entry_price]
    if not valid_sl:
        return None

    stop_loss = max(valid_sl)

    logger.info(
        "SIGNAL DETECTED │ entry=%.2f │ sl=%.2f │ risk/share=%.2f",
        entry_price, stop_loss, entry_price - stop_loss,
    )

    return {
        "signal": "BUY",
        "entry_price": entry_price,
        "stop_loss": stop_loss,
    }


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 7 — RISK & POSITION SIZING CALCULATOR
# ═════════════════════════════════════════════════════════════════════════════

def calculate_position_size(
    entry_price: float,
    stop_loss: float,
    max_risk: float = MAX_RISK_PER_TRADE_INR,
    rr_ratio: float = RISK_REWARD_RATIO,
) -> Optional[dict]:
    """
    Calculate mathematically exact position sizing.

    Parameters
    ----------
    entry_price : anticipated fill price
    stop_loss   : hard stop-loss price
    max_risk    : maximum risk in INR (default ₹500)
    rr_ratio    : risk-reward ratio (default 2.0 → target = 2× risk/share)

    Returns
    -------
    dict with keys:
        qty           (int)   — number of shares to buy
        risk_per_share (float)
        total_risk     (float) — qty × risk_per_share  (≤ ₹500)
        target_price   (float)
        total_reward   (float) — qty × reward_per_share
    None if risk per share is ≤ 0 or calculation is invalid.

    Logic
    -----
    risk_per_share  = |entry_price − stop_loss|
    qty             = floor(max_risk / risk_per_share)
    target_price    = entry_price + (risk_per_share × rr_ratio)   [for LONG]
    """

    risk_per_share = abs(entry_price - stop_loss)

    # ── Guard: reject invalid risk ──────────────────────────────────────
    if risk_per_share <= 0:
        logger.warning("Invalid risk/share = %.4f → returning None", risk_per_share)
        return None

    # ── Integer quantity (floor) ────────────────────────────────────────
    qty = math.floor(max_risk / risk_per_share)
    if qty <= 0:
        logger.warning(
            "Calculated qty = 0  (risk/share ₹%.2f > max risk ₹%.0f)  → returning None",
            risk_per_share, max_risk,
        )
        return None

    # ── Target calculation (LONG bias: entry + reward) ──────────────────
    reward_per_share = risk_per_share * rr_ratio
    if entry_price > stop_loss:
        target_price = entry_price + reward_per_share  # LONG
    else:
        target_price = entry_price - reward_per_share  # SHORT

    total_risk   = qty * risk_per_share
    total_reward = qty * reward_per_share

    result = {
        "qty":            qty,
        "risk_per_share": round(risk_per_share, 2),
        "total_risk":     round(total_risk, 2),
        "target_price":   round(target_price, 2),
        "total_reward":   round(total_reward, 2),
    }

    logger.info(
        "POSITION SIZED │ qty=%d │ risk/share=₹%.2f │ total_risk=₹%.2f │ "
        "target=%.2f │ total_reward=₹%.2f",
        qty, risk_per_share, total_risk, target_price, total_reward,
    )
    return result


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 8 — SECTOR DIVERSIFICATION & PORTFOLIO LIMIT ENFORCER
# ═════════════════════════════════════════════════════════════════════════════

def is_trade_allowed(symbol: str) -> bool:
    """
    Check whether a new trade on `symbol` is permissible under
    portfolio and sector-diversification rules.

    Rules  (evaluated in order — fail fast)
    ─────
    1. Portfolio must not be full (max 5 concurrent trades).
    2. Symbol must be part of the Nifty 50 universe.
    3. No duplicate position on the same symbol.
    4. No second position in a sector that already has an active trade.
    """

    # ── Rule 1: Portfolio capacity ──────────────────────────────────────
    if trade_tracker.is_portfolio_full:
        logger.info(
            "BLOCKED │ Portfolio FULL (%d/%d) → ignoring %s",
            trade_tracker.open_count, MAX_OPEN_POSITIONS, symbol,
        )
        return False

    # ── Rule 2: Universe membership ─────────────────────────────────────
    if symbol not in NIFTY50_SECTOR_MAP:
        logger.warning("BLOCKED │ %s not in Nifty 50 universe", symbol)
        return False

    # ── Rule 3: No duplicate symbol ─────────────────────────────────────
    if trade_tracker.is_symbol_active(symbol):
        logger.info("BLOCKED │ %s already has an active trade", symbol)
        return False

    # ── Rule 4: Sector isolation ────────────────────────────────────────
    sector = NIFTY50_SECTOR_MAP[symbol]
    if trade_tracker.has_sector_exposure(sector):
        logger.info(
            "BLOCKED │ Sector '%s' already has exposure → skipping %s",
            sector, symbol,
        )
        return False

    return True


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 9 — MAIN SCANNER LOOP
# ═════════════════════════════════════════════════════════════════════════════

def scan_universe() -> None:
    """
    Iterate over every Nifty 50 stock:
      1. Check portfolio capacity (bail if 5/5 full)
      2. Fetch multi-TF data
      3. Enrich with indicators
      4. Check entry signals
      5. Validate sector diversification
      6. Size position and log output
    """
    logger.info("=" * 72)
    logger.info(
        "SCAN STARTED  │ Universe: %d stocks │ Portfolio: %s",
        len(NIFTY50_SECTOR_MAP), trade_tracker.summary(),
    )
    logger.info("=" * 72)

    # ── Early exit: if portfolio is already full, skip entire scan ──────
    if trade_tracker.is_portfolio_full:
        logger.info(
            "SCAN SKIPPED  │ Portfolio is FULL (%d/%d). "
            "Close a position before new signals are processed.",
            trade_tracker.open_count, MAX_OPEN_POSITIONS,
        )
        return

    signals_found = 0
    signals_rejected_sector = 0
    signals_rejected_full   = 0

    for symbol, sector in NIFTY50_SECTOR_MAP.items():

        # ── 0. Re-check portfolio capacity mid-scan ────────────────────
        #    (a trade may have been added during this loop iteration)
        if trade_tracker.is_portfolio_full:
            logger.info(
                "SCAN HALTED   │ Portfolio reached %d/%d during scan → "
                "skipping remaining symbols",
                trade_tracker.open_count, MAX_OPEN_POSITIONS,
            )
            signals_rejected_full += 1
            break

        # ── 1. Quick diversification + capacity pre-check ──────────────
        if not is_trade_allowed(symbol):
            continue

        logger.info("SCANNING      │ %s  [%s]", symbol, sector)

        # ── 2. Fetch multi-timeframe data ──────────────────────────────
        df_5m  = fetch_candles(symbol, timeframe="5min",  days_back=5)
        df_15m = fetch_candles(symbol, timeframe="15min", days_back=10)
        df_1h  = fetch_candles(symbol, timeframe="1h",    days_back=15)

        if df_5m.empty or df_15m.empty or df_1h.empty:
            logger.warning("SKIP          │ %s — insufficient data", symbol)
            continue

        # ── 3. Enrich with indicators ──────────────────────────────────
        df_5m  = enrich_5min(df_5m)
        df_15m = enrich_15min(df_15m)
        df_1h  = enrich_1h(df_1h)

        # ── 4. Check entry signals ─────────────────────────────────────
        signal = check_entry_signals(df_5m, df_15m, df_1h)

        if signal is None:
            logger.debug("NO SIGNAL     │ %s", symbol)
            continue

        signals_found += 1
        entry = signal["entry_price"]
        sl    = signal["stop_loss"]

        # ── 5. Position sizing ─────────────────────────────────────────
        position = calculate_position_size(entry, sl)

        if position is None:
            logger.warning("SIZING FAILED │ %s — risk too wide or invalid", symbol)
            continue

        # ── 6. Register the trade (add_trade re-checks capacity) ───────
        added = trade_tracker.add_trade(
            symbol=symbol,
            sector=sector,
            entry_price=entry,
            stop_loss=sl,
            target_price=position["target_price"],
            qty=position["qty"],
        )
        if not added:
            signals_rejected_full += 1

    logger.info("─" * 72)
    logger.info(
        "SCAN COMPLETE │ Signals: %d │ Rejected(full): %d │ %s",
        signals_found, signals_rejected_full, trade_tracker.summary(),
    )
    logger.info("─" * 72)


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 10 — ENTRY POINT
# ═════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logger.info("╔══════════════════════════════════════════════════════════════╗")
    logger.info("║   NIFTY 50 TRADING ENGINE  —  v1.1.0                       ║")
    logger.info("║   Broker : %-48s ║", BROKER)
    logger.info("║   Risk   : ₹%d / trade │ Target : ₹%d (1:%d R:R)       ║",
                MAX_RISK_PER_TRADE_INR, TARGET_PROFIT_INR, int(RISK_REWARD_RATIO))
    logger.info("║   Max Positions : %d concurrent (unique sectors)           ║",
                MAX_OPEN_POSITIONS)
    logger.info("╚══════════════════════════════════════════════════════════════╝")

    # ── Run a single scan (integrate with scheduler for live trading) ───
    scan_universe()

    # ── Print active trade summary ──────────────────────────────────────
    if trade_tracker.active_trades:
        logger.info("\n┌─── ACTIVE POSITIONS ────────────────────────────────────────┐")
        for sym, info in trade_tracker.active_trades.items():
            logger.info(
                "│ %-22s │ %s │ qty=%3d │ entry=%8.2f │ sl=%8.2f │ tgt=%8.2f │",
                sym, info["sector"], info["qty"],
                info["entry_price"], info["stop_loss"], info["target_price"],
            )
        logger.info("└─────────────────────────────────────────────────────────────┘")
    else:
        logger.info("No active trades after scan.")
