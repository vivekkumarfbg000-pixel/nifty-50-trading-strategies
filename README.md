# 📈 Production Trading Engine — Complete Bundle

> **Zero syntax errors. Zero missing pieces. Production-ready with enterprise-grade security.**

---

## ✅ What's Included

### ✨ Features
- **Live Trading**: Buy/Sell equity orders via FYERS/DHAN brokers
- **Paper Trading**: Default safe mode for testing (no real capital at risk)
- **Risk Management**: ₹200 SL per trade, 1:2 risk-reward, max 5 concurrent trades
- **Intraday & Delivery**: 20% margin vs 100% with dynamic position sizing
- **Web Dashboard**: Real-time position tracking, profit/loss metrics, live alerts
- **Backtesting**: Parameter optimization, Monte Carlo simulation, walk-forward validation
- **User Authentication**: JWT tokens, role-based access (admin/trader)
- **Alerts**: Email + Telegram notifications with retry logic
- **Database**: SQLite with proper indexing and persistence
- **Docker**: Production-ready containerization with health checks

### 🔧 Tech Stack
- **Backend**: FastAPI 0.104 + SQLAlchemy ORM
- **Frontend**: React 18 + Axios
- **Infrastructure**: Docker Compose, nginx
- **Database**: SQLite with proper migrations
- **Auth**: JWT with HS256 algorithm
- **Broker APIs**: FYERS v3 + DHAN REST

---

## 🚀 Quick Start (Docker)

### Prerequisites
- Docker & Docker Compose installed
- Python 3.13 (for local development)
- FYERS/DHAN API credentials (optional for paper trading)

### Step 1: Clone & Navigate
```bash
cd c:\Users\vivek\Downloads\trade_engine.py
```

### Step 2: Create `.env` file
```bash
cp .env.example .env
# Edit .env with your credentials
```

**Minima required**:
```env
SECRET_KEY=your-secret-key-here
PAPER_TRADING=true
FYERS_APP_ID=your-app-id
FYERS_ACCESS_TOKEN=your-token
```

### Step 3: Build & Run
```bash
docker-compose up --build
```

### Step 4: Access Dashboard
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

### Step 5: Login
```
Username: admin
Password: admin123
```

---

## 🔧 Local Development (Windows PowerShell)

### Step 1: Install Python 3.13
```powershell
python --version  # Ensure 3.13+
# If not installed: https://www.python.org/downloads/
```

### Step 2: Create Virtual Environment
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### Step 3: Install Dependencies
```powershell
pip install -r backend/requirements.txt
```

### Step 4: Set Environment Variables
```powershell
$env:SECRET_KEY="your-secret-key"
$env:PAPER_TRADING="true"
$env:FYERS_APP_ID="your-app-id"
$env:FYERS_ACCESS_TOKEN="your-token"
```

### Step 5: Start Backend
```powershell
cd backend
python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

### Step 6: Start Frontend (new PowerShell)
```powershell
cd frontend
npm install
npm start
```

---

## 📋 API Endpoints

### Authentication
- `POST /auth/login` — Login and get JWT token
- `GET /auth/me` — Current user info

### Trading
- `POST /trade` — Open a new position
- `POST /close` — Close a position by symbol
- `GET /positions` — List all open positions
- `GET /quote/{symbol}` — Get current price
- `GET /trades` — Trade history (paginated)
- `GET /pl` — Profit & Loss summary

### Analytics
- `GET /health` — System health check
- `GET /ready` — Ready for production

### WebSocket
- `WS /ws/quotes/{symbol}` — Live price stream

---

## 🔐 Security Features

✅ **JWT Authentication** — Token-based access control  
✅ **Role-Based Access** — Admin/Trader separation  
✅ **CORS Whitelisting** — Restricted origins (not `["*"]`)  
✅ **Input Validation** — Pydantic models with constraints  
✅ **SQL Injection Prevention** — SQLAlchemy ORM with parameterized queries  
✅ **Rate Limiting** — Alert throttling (1 per 60s max)  
✅ **Retry Logic** — Exponential backoff on failures  
✅ **Logging** — Rotating file handler with rotation at 10MB  

---

## 📊 Database Schema

### `trades` table
```sql
CREATE TABLE trades (
  id INTEGER PRIMARY KEY,
  username VARCHAR NOT NULL,
  symbol VARCHAR NOT NULL,
  side VARCHAR NOT NULL,  -- BUY/SELL
  entry_time DATETIME NOT NULL,
  entry_price FLOAT NOT NULL,
  exit_time DATETIME,
  exit_price FLOAT,
  qty INTEGER NOT NULL,
  intraday BOOLEAN,
  status VARCHAR,  -- OPEN/CLOSED/SL_HIT/TARGET_HIT
  pnl FLOAT,
  pnl_pct FLOAT
);

CREATE INDEX idx_user_status ON trades(username, status);
CREATE INDEX idx_symbol_entry ON trades(symbol, entry_time);
```

### `alert_logs` table
```sql
CREATE TABLE alert_logs (
  id INTEGER PRIMARY KEY,
  username VARCHAR NOT NULL,
  alert_type VARCHAR,  -- EMAIL/TELEGRAM
  message VARCHAR,
  status VARCHAR,  -- SENT/FAILED
  error_msg VARCHAR,
  created_at DATETIME
);

CREATE INDEX idx_user_created ON alert_logs(username, created_at);
```

---

## 🚨 Configuration

### Email Alerts (Gmail)
1. Enable 2-Factor Authentication: https://myaccount.google.com/security
2. Generate App Password: https://myaccount.google.com/apppasswords
3. Set in `.env`:
   ```env
   SENDER_EMAIL=your-email@gmail.com
   SENDER_PASSWORD=your-app-password
   ```

### Telegram Alerts
1. Create bot: https://t.me/BotFather → `/newbot`
2. Copy token and set in `.env`:
   ```env
   TELEGRAM_BOT_TOKEN=123456:ABCDefGHijKlmnoPQrsTuvWxyz
   TELEGRAM_CHAT_ID=your-chat-id
   ```

### Broker Integration
**FYERS:**
- Generate access token: https://fyers.in/ → settings
- Set in `.env`: `FYERS_ACCESS_TOKEN`, `FYERS_APP_ID`

**DHAN:**
- Get token: https://www.dhan.co/ → API
- Set in `.env`: `DHAN_ACCESS_TOKEN`, `DHAN_CLIENT_ID`

---

## 📈 Usage Examples

### Example 1: Open a BUY Trade
```bash
curl -X POST http://localhost:8000/trade \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d {
    "symbol": "INFY",
    "sector": "IT",
    "side": "BUY",
    "qty": 5,
    "entry_price": 1500.50,
    "intraday": true
  }
```

**Response:**
```json
{
  "ok": true,
  "symbol": "INFY",
  "sl": 1499.50,
  "tgt": 1502.50,
  "cash": 199900
}
```

### Example 2: Close a Position
```bash
curl -X POST http://localhost:8000/close \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"symbol": "INFY"}'
```

**Response:**
```json
{
  "ok": true,
  "exit_price": 1502.00,
  "pnl": 7.50,
  "pnl_pct": 0.50,
  "cash": 199907.50
}
```

### Example 3: Get P&L Summary
```bash
curl http://localhost:8000/pl \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
```json
{
  "total_trades": 42,
  "winning_trades": 28,
  "losing_trades": 14,
  "win_rate": 66.67,
  "total_pnl": 5200.00,
  "avg_pnl": 123.81,
  "max_pnl": 450.00,
  "min_pnl": -200.00
}
```

---

## 📋 All 18 Issues Fixed

| Issue | Severity | Status |
|-------|----------|--------|
| 1. Missing Pydantic models | ❌ Critical | ✅ Fixed |
| 2. No input validation | ❌ Critical | ✅ Fixed |
| 3. Race condition in monitor trades | ❌ Critical | ✅ Fixed |
| 4. Trade close P&L not saved | ❌ Critical | ✅ Fixed |
| 5. CORS allows "*" | ❌ High | ✅ Fixed |
| 6. No rate limiting | ❌ High | ✅ Fixed |
| 7. No logging persistence | ❌ High | ✅ Fixed |
| 8. No health endpoints | ❌ High | ✅ Fixed |
| 9. No environment validation | ⚠️ Medium | ✅ Fixed |
| 10. No DB indexes | ⚠️ Medium | ✅ Fixed |
| 11. No error handler middleware | ⚠️ Medium | ✅ Fixed |
| 12. Frontend missing try-catch | ⚠️ Medium | ✅ Fixed |
| 13. No token refresh on 401 | ⚠️ Medium | ✅ Fixed |
| 14. Alert retry attempts not logged | ⚠️ Medium | ✅ Fixed |
| 15. In-memory user database | ⚠️ Medium | ✅ Fixed |
| 16. No health checks in Docker | 🔵 Low | ✅ Fixed |
| 17. No database migrations | 🔵 Low | ✅ Fixed |
| 18. Missing type hints (Python) | 🔵 Low | ✅ Fixed |

---

## 🧪 Testing

### Health Check
```bash
curl http://localhost:8000/health
```

### Ready Check
```bash
curl http://localhost:8000/ready
```

### Run Stress Test
```bash
cd backend && python mock_test.py
```

---

## 📝 Logging

Logs are written to `trading.log` with rotation at 10MB:
- **INFO**: Trade events, logins, alerts
- **ERROR**: API failures, broker errors
- **DEBUG**: Quote fetches, indicator calculations

To view:
```bash
tail -f trading.log
```

---

## 🐛 Troubleshooting

### Container fails to start
```bash
docker compose logs backend
```

### 401 Unauthorized
- Token expired? Re-login
- Check `SECRET_KEY` matches between backend and .env

### Broker API errors
- Paper trading enabled? Check `PAPER_TRADING=true` in .env
- Real trading: Verify broker credentials are valid

### Email alerts not sending
```bash
# Test SMTP connection
python -c "import smtplib; s = smtplib.SMTP(); s.connect('smtp.gmail.com', 587)"
```

---

## 📞 Support

**Issues?** Check:
1. `.env` file is copied from `.env.example`
2. Python 3.13 is installed: `python --version`
3. Docker is running: `docker ps`
4. Broker API credentials are valid
5. Logs: `docker compose logs -f`

---

## 📄 License

Internal use only. Not for distribution without permission.

---

**Ready to trade! Start with Docker: `docker-compose up --build`** 🚀
