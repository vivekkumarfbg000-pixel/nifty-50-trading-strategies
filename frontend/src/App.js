import React, { useState, useEffect } from "react";
import axios from "axios";
import "./App.css";

// SVG Icons
const ActivityIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg>
);

const TargetIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"></circle><circle cx="12" cy="12" r="6"></circle><circle cx="12" cy="12" r="2"></circle></svg>
);

const WalletIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M20 12V8H6a2 2 0 0 1-2-2c0-1.1.9-2 2-2h12v4"></path><path d="M4 6v12c0 1.1.9 2 2 2h14v-4"></path><path d="M18 12a2 2 0 1 0 0 4h4v-4Z"></path></svg>
);

const AlertIcon = ({ type }) => {
  if (type === 'error') return <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#ff1744" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>;
  return <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#00e676" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>;
};

const CloseIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
);

const API_URL = process.env.REACT_APP_API_URL || (window.location.hostname === 'localhost' ? "http://localhost:8000" : "/api");

const api = axios.create({ baseURL: API_URL });

function App() {
  const [positions, setPositions] = useState({});
  const [symbol, setSymbol] = useState("");
  const [quantity, setQuantity] = useState(1);
  const [price, setPrice] = useState("");
  const [broker, setBroker] = useState("FYERS");
  
  const [loading, setLoading] = useState(false);
  const [pnl, setPnl] = useState({});
  const [toasts, setToasts] = useState([]);

  const showToast = (message, type = "success") => {
    const id = Date.now();
    setToasts(prev => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, 4000);
  };

  const fetchPositions = React.useCallback(async () => {
    try {
      const res = await api.get("/positions");
      setPositions(res.data.positions || {});
    } catch (err) {
      console.error("Fetch positions error:", err);
    }
  }, []);

  const fetchPnl = React.useCallback(async () => {
    try {
      const res = await api.get("/pnl");
      setPnl(res.data || {});
    } catch (err) {
      console.error("Fetch P&L error:", err);
    }
  }, []);

  useEffect(() => {
    fetchPositions();
    fetchPnl();
    const interval = setInterval(() => {
      fetchPositions();
      fetchPnl();
    }, 10000);
    return () => clearInterval(interval);
  }, [fetchPositions, fetchPnl]);

  const handleOpenTrade = async (e) => {
    e.preventDefault();
    if (!symbol || !price) return;
    
    setLoading(true);
    try {
      await api.post("/open_trade", {
        symbol: symbol.toUpperCase(),
        quantity: parseInt(quantity),
        price: parseFloat(price),
        broker,
      });
      showToast(`Trade executed: ${symbol} ${quantity}x @ ₹${price}`, "success");
      setSymbol("");
      setQuantity(1);
      setPrice("");
      await Promise.all([fetchPositions(), fetchPnl()]);
    } catch (err) {
      showToast(err.response?.data?.detail || "Failed to execute trade", "error");
    } finally {
      setLoading(false);
    }
  };

  const handleCloseTrade = async (sym) => {
    setLoading(true);
    try {
      await api.post("/close_trade", { symbol: sym, broker });
      showToast(`Successfully closed position: ${sym}`, "success");
      await Promise.all([fetchPositions(), fetchPnl()]);
    } catch (err) {
      showToast(err.response?.data?.detail || "Failed to close position", "error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-container">
      <header>
        <div className="title-glow">
          <ActivityIcon />
          <span>NexusTrade</span>
          <span className="dot"></span>
        </div>
      </header>

      {/* Toast Notifications */}
      <div className="toaster">
        {toasts.map(t => (
          <div key={t.id} className={`toast toast-${t.type}`}>
            <AlertIcon type={t.type} />
            {t.message}
          </div>
        ))}
      </div>

      <div className="dashboard-layout">
        
        {/* Left Column: Actions & Metrics */}
        <div className="col-left">
          <div className="panel glass-panel">
            <h2 className="panel-header">Terminal</h2>
            <form onSubmit={handleOpenTrade}>
              <div className="form-group">
                <label>Instrument Symbol</label>
                <input
                  type="text"
                  placeholder="e.g. NSE:RELIANCE-EQ"
                  value={symbol}
                  onChange={(e) => setSymbol(e.target.value)}
                  required
                />
              </div>
              <div className="form-group" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                <div>
                  <label>Quantity</label>
                  <input
                    type="number"
                    value={quantity}
                    onChange={(e) => setQuantity(e.target.value)}
                    min="1"
                    required
                  />
                </div>
                <div>
                  <label>Entry Price (₹)</label>
                  <input
                    type="number"
                    placeholder="0.00"
                    value={price}
                    onChange={(e) => setPrice(e.target.value)}
                    step="0.01"
                    required
                  />
                </div>
              </div>
              <div className="form-group">
                <label>Broker Integration</label>
                <select value={broker} onChange={(e) => setBroker(e.target.value)}>
                  <option value="FYERS">FYERS API V3</option>
                  <option value="DHAN">DHAN HQ API</option>
                  <option value="UPSTOX">UPSTOX SANDBOX</option>
                </select>
              </div>
              <button type="submit" className="btn-base btn-primary" disabled={loading}>
                {loading ? "Executing Sequence..." : "Deploy Trade"}
              </button>
            </form>
          </div>

          <div style={{ marginTop: '32px' }}>
            <h2 className="panel-header" style={{ marginBottom: '16px' }}>Portfolio Matrix</h2>
            <div className="metrics-grid">
              <div className="metric-card">
                <div className="metric-label">Liquidity</div>
                <div className="metric-value">₹{(pnl.available_cash || 200000).toLocaleString('en-IN', { maximumFractionDigits: 2 })}</div>
              </div>
              <div className="metric-card">
                <div className="metric-label">Active Nodes</div>
                <div className="metric-value">{pnl.open_positions || 0}</div>
              </div>
            </div>
            
            <div className="metric-card" style={{ gridColumn: '1 / -1' }}>
              <div className="metric-label" style={{ display: 'flex', alignItems: 'center', gap: '8px'}}>
                <WalletIcon /> Absolute P&L
              </div>
              <div className={`metric-value ${(pnl.total_pnl || 0) >= 0 ? 'positive' : 'negative'}`} style={{ fontSize: '2rem' }}>
                ₹{(pnl.total_pnl || 0).toLocaleString('en-IN', { maximumFractionDigits: 2 })}
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Positions Ledger */}
        <div className="col-right">
          <div className="panel glass-panel" style={{ height: '100%', minHeight: '600px' }}>
            <h2 className="panel-header" style={{ display: 'flex', justifyContent: 'space-between'}}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <TargetIcon /> Operations Ledger
              </div>
              <span className="tag tag-broker">{Object.keys(positions).length} Active</span>
            </h2>

            {Object.keys(positions).length > 0 ? (
              <div className="table-container">
                <table>
                  <thead>
                    <tr>
                      <th>Instrument</th>
                      <th>Direction</th>
                      <th>Qty</th>
                      <th>Entry</th>
                      <th>Stop Loss</th>
                      <th>Target</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(positions).map(([sym, trade]) => (
                      <tr key={sym}>
                        <td style={{ fontWeight: 600 }}>{sym}</td>
                        <td>
                          <span className={`tag tag-${trade.side?.toLowerCase() === 'buy' ? 'buy' : 'sell'}`}>
                            {trade.side}
                          </span>
                        </td>
                        <td>{trade.qty}</td>
                        <td>₹{trade.entry_price?.toFixed(2)}</td>
                        <td style={{ color: 'var(--danger)' }}>₹{trade.stop_loss?.toFixed(2)}</td>
                        <td style={{ color: 'var(--success)' }}>₹{trade.target_price?.toFixed(2)}</td>
                        <td>
                          <button
                            onClick={() => handleCloseTrade(sym)}
                            disabled={loading}
                            className="btn-base btn-danger"
                          >
                            <CloseIcon /> Close
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="empty-state">
                <div className="empty-icon">⇋</div>
                <h3>No Active Operations</h3>
                <p>Deploy a trade from the terminal to monitor it here.</p>
              </div>
            )}
          </div>
        </div>

      </div>
    </div>
  );
}

export default App;
