import React, { useState, useEffect } from "react";
import axios from "axios";
import "./App.css";

const API_URL = process.env.REACT_APP_API_URL || "http://localhost:8000";

function App() {
  const [positions, setPositions] = useState([]);
  const [symbol, setSymbol] = useState("");
  const [quantity, setQuantity] = useState(1);
  const [price, setPrice] = useState(0);
  const [broker, setBroker] = useState("FYERS");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [pnl, setPnl] = useState({});

  const api = axios.create({
    baseURL: API_URL,
  });

  // ── Fetch Positions ────────────────────────────────────
  const fetchPositions = async () => {
    setLoading(true);
    try {
      const res = await api.get("/positions");
      setPositions(res.data.positions || []);
      setSuccess("");
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to fetch positions");
    } finally {
      setLoading(false);
    }
  };

  // ── Fetch P&L ────────────────────────────────────
  const fetchPnl = async () => {
    try {
      const res = await api.get("/pnl");
      setPnl(res.data.pnl || {});
    } catch (err) {
      console.error("Failed to fetch P&L:", err);
    }
  };

  // ── Open Trade ────────────────────────────────────
  const handleOpenTrade = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    setSuccess("");
    try {
      const res = await api.post("/open_trade", {
        symbol: symbol.toUpperCase(),
        quantity: parseInt(quantity),
        price: parseFloat(price),
        broker,
      });
      setSuccess(`Trade opened: ${symbol} ${quantity} @ ₹${price}`);
      setSymbol("");
      setQuantity(1);
      setPrice(0);
      await fetchPositions();
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to open trade");
    } finally {
      setLoading(false);
    }
  };

  // ── Close Trade ────────────────────────────────────
  const handleCloseTrade = async (sym) => {
    setLoading(true);
    setError("");
    try {
      await api.post("/close_trade", { symbol: sym, broker });
      setSuccess(`Trade closed: ${sym}`);
      await fetchPositions();
      await fetchPnl();
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to close trade");
    } finally {
      setLoading(false);
    }
  };

  // ── Auto-refresh ────────────────────────────────────
  useEffect(() => {
    fetchPositions();
    fetchPnl();
    const interval = setInterval(() => {
      fetchPositions();
      fetchPnl();
    }, 10000);
    return () => clearInterval(interval);
  }, []);

  // ── Dashboard ────────────────────────────────────
  return (
    <div className="container">
      <div className="header">
        <h1>📈 Trading Dashboard</h1>
      </div>

      {error && <div className="alert error">{error}</div>}
      {success && <div className="alert success">{success}</div>}

      <div className="dashboard-grid">
        {/* Trade Form */}
        <div className="card">
          <h2>Open Trade</h2>
          <form onSubmit={handleOpenTrade}>
            <input
              type="text"
              placeholder="Symbol (e.g., INFY)"
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
              required
            />
            <input
              type="number"
              placeholder="Quantity"
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
              min="1"
              required
            />
            <input
              type="number"
              placeholder="Price"
              value={price}
              onChange={(e) => setPrice(e.target.value)}
              step="0.01"
              required
            />
            <select value={broker} onChange={(e) => setBroker(e.target.value)}>
              <option value="FYERS">FYERS</option>
              <option value="DHAN">DHAN</option>
              <option value="UPSTOX">UPSTOX</option>
            </select>
            <button type="submit" disabled={loading}>
              {loading ? "Opening..." : "Open Trade"}
            </button>
          </form>
        </div>

        {/* P&L Summary */}
        <div className="card">
          <h2>P&L Summary</h2>
          <div className="metric">
            <span>Total Trades:</span>
            <strong>{pnl.total_trades || 0}</strong>
          </div>
          <div className="metric">
            <span>Win Rate:</span>
            <strong>{pnl.win_rate?.toFixed(2) || 0}%</strong>
          </div>
          <div className="metric">
            <span>Total P&L:</span>
            <strong className={pnl.total_pnl > 0 ? "positive" : "negative"}>
              ₹{pnl.total_pnl?.toFixed(2) || 0}
            </strong>
          </div>
          <div className="metric">
            <span>Avg P&L:</span>
            <strong>₹{pnl.avg_pnl?.toFixed(2) || 0}</strong>
          </div>
        </div>
      </div>

      {/* Open Positions */}
      <div className="card">
        <h2>Open Positions ({Object.keys(positions).length})</h2>
        {Object.keys(positions).length > 0 ? (
          <table>
            <thead>
              <tr>
                <th>Symbol</th>
                <th>Side</th>
                <th>Qty</th>
                <th>Entry</th>
                <th>SL</th>
                <th>Target</th>
                <th>Broker</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(positions).map(([sym, trade]) => (
                <tr key={sym}>
                  <td>{sym}</td>
                  <td>{trade.side}</td>
                  <td>{trade.qty}</td>
                  <td>₹{trade.entry_price?.toFixed(2) || "-"}</td>
                  <td>₹{trade.stop_loss?.toFixed(2) || "-"}</td>
                  <td>₹{trade.target_price?.toFixed(2) || "-"}</td>
                  <td>{trade.broker}</td>
                  <td>
                    <button
                      onClick={() => handleCloseTrade(sym)}
                      disabled={loading}
                      className="close-btn"
                    >
                      Close
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p>No open positions</p>
        )}
      </div>
    </div>
  );
}

export default App;
