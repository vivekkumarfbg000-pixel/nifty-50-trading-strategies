import React, { useState, useEffect, useCallback } from "react";
import axios from "axios";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { Activity, Target, Wallet, X, BarChart2, BookOpen } from "lucide-react";
import "./App.css";

const AlertIcon = ({ type }) => {
  if (type === 'error') return <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#ff1744" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>;
  return <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#00e676" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>;
};

const API_URL = process.env.REACT_APP_API_URL || (window.location.hostname === 'localhost' ? "http://localhost:8000" : "/api");
const api = axios.create({ baseURL: API_URL });

function App() {
  const [activeTab, setActiveTab] = useState('live'); // 'live', 'journal', 'backtest'
  
  // -- Live State --
  const [positions, setPositions] = useState({});
  const [pnl, setPnl] = useState({});
  const [symbol, setSymbol] = useState("");
  const [quantity, setQuantity] = useState(1);
  const [price, setPrice] = useState("");
  const [broker, setBroker] = useState("FYERS");
  
  // -- Journal State --
  const [journalTrades, setJournalTrades] = useState([]);
  const [journalSummary, setJournalSummary] = useState({});

  // -- Backtest State --
  const [btSymbol, setBtSymbol] = useState("NSE:RELIANCE-EQ");
  const [btDays, setBtDays] = useState(30);
  const [btLoading, setBtLoading] = useState(false);
  const [btResults, setBtResults] = useState(null);

  // -- Global State --
  const [loading, setLoading] = useState(false);
  const [toasts, setToasts] = useState([]);

  const showToast = (message, type = "success") => {
    const id = Date.now();
    setToasts(prev => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, 4000);
  };

  const fetchPositions = useCallback(async () => {
    try {
      const res = await api.get("/positions");
      setPositions(res.data.positions || {});
    } catch (err) { }
  }, []);

  const fetchPnl = useCallback(async () => {
    try {
      const res = await api.get("/pnl");
      setPnl(res.data || {});
    } catch (err) { }
  }, []);

  const fetchJournal = useCallback(async () => {
    try {
      const [resTrades, resSummary] = await Promise.all([
        api.get("/journal"),
        api.get("/journal/summary")
      ]);
      setJournalTrades(resTrades.data.trades || []);
      setJournalSummary(resSummary.data || {});
    } catch (err) { }
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

  useEffect(() => {
    if (activeTab === 'journal') fetchJournal();
  }, [activeTab, fetchJournal]);

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
      showToast(`Demo Trade executed: ${symbol} ${quantity}x @ ₹${price}`, "success");
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
      showToast(`Closed Demo Position: ${sym}`, "success");
      await Promise.all([fetchPositions(), fetchPnl()]);
      if (activeTab === 'journal') fetchJournal();
    } catch (err) {
      showToast(err.response?.data?.detail || "Failed to close position", "error");
    } finally {
      setLoading(false);
    }
  };

  const runBacktest = async (e) => {
    e.preventDefault();
    if (!btSymbol) return;
    setBtLoading(true);
    setBtResults(null);
    try {
      const res = await api.post("/backtest", { symbol: btSymbol.toUpperCase(), days: parseInt(btDays) });
      setBtResults(res.data);
      showToast(`Backtest completed for ${btSymbol}`, "success");
    } catch (err) {
      showToast(err.response?.data?.detail || "Backtest failed", "error");
    } finally {
      setBtLoading(false);
    }
  };

  return (
    <div className="app-container">
      <header>
        <div className="title-glow">
          <Activity />
          <span>NexusTrade Tracker</span>
          <span className="dot"></span>
        </div>
        
        <div className="nav-tabs">
          <button className={`tab-btn ${activeTab === 'live' ? 'active' : ''}`} onClick={() => setActiveTab('live')}>
            <Activity size={18} /> Demo Broker
          </button>
          <button className={`tab-btn ${activeTab === 'journal' ? 'active' : ''}`} onClick={() => setActiveTab('journal')}>
            <BookOpen size={18} /> Daily Journal
          </button>
          <button className={`tab-btn ${activeTab === 'backtest' ? 'active' : ''}`} onClick={() => setActiveTab('backtest')}>
            <BarChart2 size={18} /> Backtest Lab
          </button>
        </div>
      </header>

      <div className="toaster">
        {toasts.map(t => (
          <div key={t.id} className={`toast toast-${t.type}`}>
            <AlertIcon type={t.type} />
            {t.message}
          </div>
        ))}
      </div>

      {/* --- LIVE DEMO BROKER TAB --- */}
      {activeTab === 'live' && (
        <div className="dashboard-layout">
          <div className="col-left">
            <div className="panel glass-panel">
              <h2 className="panel-header">Simulated Terminal</h2>
              <form onSubmit={handleOpenTrade}>
                <div className="form-group">
                  <label>Instrument Symbol</label>
                  <input type="text" placeholder="e.g. NSE:RELIANCE-EQ" value={symbol} onChange={(e) => setSymbol(e.target.value)} required />
                </div>
                <div className="form-group" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                  <div>
                    <label>Quantity</label>
                    <input type="number" value={quantity} onChange={(e) => setQuantity(e.target.value)} min="1" required />
                  </div>
                  <div>
                    <label>Simulate Entry Price (₹)</label>
                    <input type="number" placeholder="0.00" value={price} onChange={(e) => setPrice(e.target.value)} step="0.01" required />
                  </div>
                </div>
                <div className="form-group">
                  <label>Broker Integration</label>
                  <select value={broker} onChange={(e) => setBroker(e.target.value)}>
                    <option value="FYERS">FYERS PAPER TRADING</option>
                    <option value="UPSTOX">UPSTOX DEMO</option>
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
                  <div className="metric-value">₹{(pnl.available_cash || 200000).toLocaleString('en-IN', { maximumFractionDigits: 0 })}</div>
                </div>
                <div className="metric-card">
                  <div className="metric-label">Active Nodes</div>
                  <div className="metric-value">{pnl.open_positions || 0}</div>
                </div>
                <div className="metric-card pnl-hero">
                  <div className="metric-label" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Wallet /> Absolute P&L
                  </div>
                  <div className={`metric-value ${(pnl.total_pnl || 0) >= 0 ? 'positive' : 'negative'}`} style={{ fontSize: '1.8rem' }}>
                    ₹{(pnl.total_pnl || 0).toLocaleString('en-IN', { maximumFractionDigits: 2 })}
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="col-right">
            <div className="panel glass-panel" style={{ minHeight: '520px' }}>
              <h2 className="panel-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Target /> Operations Ledger
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
                            <button onClick={() => handleCloseTrade(sym)} disabled={loading} className="btn-base btn-danger">
                              <X size={14}/> Close
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
      )}

      {/* --- DAILY JOURNAL TAB --- */}
      {activeTab === 'journal' && (
        <div className="full-width-panel">
          <div className="metrics-grid" style={{ gridTemplateColumns: 'repeat(4, 1fr)' }}>
            <div className="metric-card">
              <div className="metric-label">Total Trades Logged</div>
              <div className="metric-value">{journalSummary.total_trades || 0}</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Lifetime Win Rate</div>
              <div className="metric-value">{journalSummary.win_rate || 0}%</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Simulated Net Equity P&L</div>
              <div className={`metric-value ${(journalSummary.total_pnl || 0) >= 0 ? 'positive' : 'negative'}`}>
                ₹{(journalSummary.total_pnl || 0).toLocaleString('en-IN', { maximumFractionDigits: 2 })}
              </div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Biggest Winner</div>
              <div className="metric-value positive">₹{journalSummary.biggest_win || 0}</div>
            </div>
          </div>

          <div className="panel glass-panel" style={{ marginTop: '24px' }}>
            <h2 className="panel-header"><BookOpen /> Closed Trade Ledger</h2>
            {journalTrades.length > 0 ? (
               <div className="table-container">
                 <table>
                   <thead>
                     <tr>
                       <th>Closed Date</th>
                       <th>Symbol</th>
                       <th>Direction</th>
                       <th>Qty</th>
                       <th>Entry</th>
                       <th>Exit</th>
                       <th>Reason</th>
                       <th>Gross P&L</th>
                     </tr>
                   </thead>
                   <tbody>
                     {journalTrades.map((t, i) => (
                       <tr key={i}>
                         <td>{new Date(t.closed_at).toLocaleString()}</td>
                         <td style={{ fontWeight: 600 }}>{t.symbol}</td>
                         <td><span className={`tag tag-${t.side?.toLowerCase() === 'buy' ? 'buy' : 'sell'}`}>{t.side}</span></td>
                         <td>{t.qty}</td>
                         <td>₹{t.entry_price?.toFixed(2)}</td>
                         <td>₹{t.exit_price?.toFixed(2)}</td>
                         <td><span className="tag tag-broker">{t.status.replace('_', ' ')}</span></td>
                         <td className={t.pnl >= 0 ? 'positive' : 'negative'} style={{ fontWeight: 700 }}>
                           {t.pnl >= 0 ? '+' : ''}₹{t.pnl?.toFixed(2)}
                         </td>
                       </tr>
                     ))}
                   </tbody>
                 </table>
               </div>
            ) : (
              <div className="empty-state">
                <div className="empty-icon">📁</div>
                <h3>Ledger Empty</h3>
                <p>No trades have been closed recently to log into the journal.</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* --- BACKTEST LAB TAB --- */}
      {activeTab === 'backtest' && (
        <div className="dashboard-layout">
          <div className="col-left">
            <div className="panel glass-panel">
              <h2 className="panel-header"><BarChart2 /> Backtest Configurator</h2>
              <form onSubmit={runBacktest}>
                <div className="form-group">
                  <label>Asset Symbol</label>
                  <input type="text" value={btSymbol} onChange={e => setBtSymbol(e.target.value)} required />
                </div>
                <div className="form-group">
                  <label>Historical Range (Days)</label>
                  <input type="number" value={btDays} onChange={e => setBtDays(e.target.value)} required max="730" min="1" />
                </div>
                <button type="submit" className="btn-base btn-primary" style={{ background: 'linear-gradient(135deg, #00f0ff, #0055ff)' }} disabled={btLoading}>
                  {btLoading ? "Simulating Strategy..." : "Run Multi-Timeframe Simulation"}
                </button>
              </form>
            </div>
          </div>

          <div className="col-right">
            {!btResults && !btLoading && (
               <div className="panel glass-panel empty-state" style={{ minHeight: '500px', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
                 <div className="empty-icon">📊</div>
                 <h3>Historical Laboratory</h3>
                 <p>Configure and run a test to see deeply analyzed historical strategy performance over up to 2 years.</p>
               </div>
            )}
            {btLoading && (
               <div className="panel glass-panel empty-state" style={{ minHeight: '500px', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
                 <div className="title-glow" style={{ justifyContent: 'center' }}><span className="dot"></span></div>
                 <h3 style={{ marginTop: '20px' }}>Crunching Historical Candles...</h3>
                 <p>Simulating strict entry and exit logic down to the 5-minute resolution.</p>
               </div>
            )}
            {btResults && !btLoading && btResults.summary && (
              <div className="panel glass-panel" style={{ padding: '0' }}>
                <div style={{ padding: '24px' }}>
                  <h2 className="panel-header">Backtest Analytics Summary</h2>
                  <div className="metrics-grid" style={{ marginBottom: '0' }}>
                     <div className="metric-card">
                       <div className="metric-label">Max Drawdown</div>
                       <div className="metric-value negative">-{btResults.summary.max_drawdown_pct}%</div>
                     </div>
                     <div className="metric-card">
                       <div className="metric-label">Profit Factor</div>
                       <div className="metric-value">{btResults.summary.profit_factor === Infinity ? 'MAX' : btResults.summary.profit_factor}</div>
                     </div>
                     <div className="metric-card">
                       <div className="metric-label">Probability of Profit</div>
                       <div className="metric-value">{btResults.summary.win_rate_pct}%</div>
                     </div>
                     <div className="metric-card pnl-hero" style={{ gridColumn: '2', gridRow: '1/3', background:'linear-gradient(135deg, rgba(0,255,100,0.1), transparent)'}}>
                       <div className="metric-label">Historical ROI</div>
                       <div className={`metric-value ${btResults.summary.total_return_pct >= 0 ? 'positive' : 'negative'}`} style={{ fontSize: '2.5rem' }}>
                         {btResults.summary.total_return_pct >= 0 ? '+' : ''}{btResults.summary.total_return_pct}%
                       </div>
                     </div>
                  </div>
                </div>

                {btResults.equity_curve && (
                  <div style={{ height: '250px', width: '100%', padding: '0 20px', marginTop: '10px' }}>
                    <h3 style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: '10px' }}>Equity Curve</h3>
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={btResults.equity_curve}>
                        <defs>
                          <linearGradient id="colorEquity" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#00f0ff" stopOpacity={0.3}/>
                            <stop offset="95%" stopColor="#00f0ff" stopOpacity={0}/>
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                        <XAxis dataKey="time" hide />
                        <YAxis domain={['auto', 'auto']} tick={{fill: '#8080a0', fontSize: 10}} orientation="right" tickFormatter={(v) => '₹'+v.toLocaleString()}/>
                        <Tooltip contentStyle={{ background: '#0d0d14', border: '1px solid #333' }} />
                        <Area type="monotone" dataKey="equity" stroke="#00f0ff" strokeWidth={2} fillOpacity={1} fill="url(#colorEquity)" />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                )}

                <div className="table-container" style={{ maxHeight: '400px', overflowY: 'auto' }}>
                  <table style={{ borderTop: '1px solid rgba(255,255,255,0.1)' }}>
                    <thead style={{ position: 'sticky', top: 0, background: 'var(--bg-card)' }}>
                      <tr>
                        <th>Opened</th>
                        <th>Symbol</th>
                        <th>Side</th>
                        <th>P&L</th>
                      </tr>
                    </thead>
                    <tbody>
                      {btResults.trades.map((t, idx) => (
                        <tr key={idx}>
                          <td>{new Date(t.opened_at).toLocaleDateString()}</td>
                          <td>{t.symbol}</td>
                          <td><span className={`tag tag-${t.side?.toLowerCase() === 'buy' ? 'buy' : 'sell'}`}>{t.side}</span></td>
                          <td className={t.pnl >= 0 ? 'positive' : 'negative'}>{t.pnl >= 0 ? '+' : ''}₹{t.pnl?.toFixed(2)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

              </div>
            )}
            
          </div>
        </div>
      )}

    </div>
  );
}

export default App;
