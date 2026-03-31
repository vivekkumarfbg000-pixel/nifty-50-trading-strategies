import React, { useState, useEffect, useCallback } from "react";
import axios from "axios";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { Activity, Target, Wallet, X, BarChart2, BookOpen, Terminal, CheckCircle } from "lucide-react";
import "./App.css";

const AlertIcon = ({ type }) => {
  if (type === 'error') return <X style={{ color: '#ff3e3e' }} />;
  return <CheckCircle style={{ color: '#00ff9d' }} />;
};

const API_URL = process.env.REACT_APP_API_URL || (window.location.hostname === 'localhost' ? "http://localhost:8000" : "/api");
const api = axios.create({ baseURL: API_URL });

function App() {
  const [activeTab, setActiveTab] = useState('live'); 
  const [positions, setPositions] = useState({});
  const [pnl, setPnl] = useState({});
  const [symbol, setSymbol] = useState("");
  const [quantity, setQuantity] = useState(1);
  const [price, setPrice] = useState("");
  const [broker, setBroker] = useState("UPSTOX");
  const [journalTrades, setJournalTrades] = useState([]);
  const [journalSummary, setJournalSummary] = useState({});
  const [btSymbol, setBtSymbol] = useState("NSE:RELIANCE-EQ");
  const [btDays, setBtDays] = useState(30);
  const [btLoading, setBtLoading] = useState(false);
  const [btResults, setBtResults] = useState(null);
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
      showToast(`Trade sequence initiated for ${symbol}`, "success");
      setSymbol("");
      setQuantity(1);
      setPrice("");
      await Promise.all([fetchPositions(), fetchPnl()]);
    } catch (err) {
      showToast(err.response?.data?.detail || "Sequence failed", "error");
    } finally {
      setLoading(false);
    }
  };

  const handleCloseTrade = async (sym) => {
    setLoading(true);
    try {
      await api.post("/close_trade", { symbol: sym, broker });
      showToast(`Position ${sym} neutralized`, "success");
      await Promise.all([fetchPositions(), fetchPnl()]);
      if (activeTab === 'journal') fetchJournal();
    } catch (err) {
      showToast(err.response?.data?.detail || "Neutralization failed", "error");
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
      showToast(`Simulation complete: ${btSymbol}`, "success");
    } catch (err) {
      showToast(err.response?.data?.detail || "Simulation failed", "error");
    } finally {
      setBtLoading(false);
    }
  };

  return (
    <div className={`app-container ${pnl.is_paper ? 'paper-mode' : 'live-mode'}`}>
      <header>
        <div className="title-glow">
          <Activity size={32}/>
          <span>NexusTrade</span>
          <span className="dot"></span>
          <div className="engine-status">
            <span className="engine-dot pulse"></span>
            ENGINE ONLINE
          </div>
        </div>
        
        <div className="nav-tabs">
          <button className={`tab-btn ${activeTab === 'live' ? 'active' : ''}`} onClick={() => setActiveTab('live')}>
            <Terminal size={18} /> Engine
          </button>
          <button className={`tab-btn ${activeTab === 'journal' ? 'active' : ''}`} onClick={() => setActiveTab('journal')}>
            <BookOpen size={18} /> Journal
          </button>
          <button className={`tab-btn ${activeTab === 'backtest' ? 'active' : ''}`} onClick={() => setActiveTab('backtest')}>
            <BarChart2 size={18} /> Lab
          </button>
        </div>
      </header>

      {pnl.is_paper && <div className="mode-badge">PAPER TRADING MODE</div>}

      <div className="toaster">
        {toasts.map(t => (
          <div key={t.id} className={`toast toast-${t.type}`}>
            <AlertIcon type={t.type} />
            {t.message}
          </div>
        ))}
      </div>

      {activeTab === 'live' && (
        <div className="dashboard-layout animate-fade">
          <div className="col-left">
            <div className="panel-premium" style={{ padding: '2rem' }}>
              <h2 className="panel-header">Deployment System</h2>
              <form onSubmit={handleOpenTrade}>
                <div className="form-group">
                  <label>Asset Identity</label>
                  <input type="text" placeholder="NSE:RELIANCE-EQ" value={symbol} onChange={(e) => setSymbol(e.target.value)} required />
                </div>
                <div className="form-group" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                  <div>
                    <label>Volume</label>
                    <input type="number" value={quantity} onChange={(e) => setQuantity(e.target.value)} min="1" required />
                  </div>
                  <div>
                    <label>Fill Price (₹)</label>
                    <input type="number" placeholder="0.00" value={price} onChange={(e) => setPrice(e.target.value)} step="0.01" required />
                  </div>
                </div>
                <div className="form-group">
                  <label>Broker Relay</label>
                  <select value={broker} onChange={(e) => setBroker(e.target.value)}>
                    <option value="UPSTOX">UPSTOX LIVE/PAPER</option>
                    <option value="FYERS">FYERS API V3</option>
                  </select>
                </div>
                <button type="submit" className="btn-primary" disabled={loading}>
                  {loading ? "Initializing..." : "Deploy Order"}
                </button>
              </form>
            </div>

            <div style={{ marginTop: '2.5rem' }}>
              <div className="metrics-grid">
                <div className="metric-card panel-premium">
                  <span className="metric-label">Liquidity Pool</span>
                  <span className="metric-value mono">₹{(pnl.available_cash || 200000).toLocaleString('en-IN')}</span>
                </div>
                <div className="metric-card panel-premium">
                  <span className="metric-label">Active Nodes</span>
                  <span className="metric-value mono">{pnl.open_positions || 0}</span>
                </div>
                <div className="metric-card pnl-hero panel-premium">
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    <span className="metric-label">Net Performance</span>
                    <span className={`metric-value mono ${(pnl.total_pnl || 0) >= 0 ? 'positive' : 'negative'}`}>
                      {pnl.total_pnl >= 0 ? '+' : ''}₹{(pnl.total_pnl || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                    </span>
                  </div>
                  <Wallet size={32} style={{ opacity: 0.3 }} />
                </div>
              </div>
            </div>
          </div>

          <div className="col-right">
            <div className="panel-premium" style={{ minHeight: '600px', padding: '2rem' }}>
              <h2 className="panel-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <Target size={20} color="#00f0ff" /> Live Activity Feed
                </div>
                <span className="tag tag-broker">{Object.keys(positions).length} Concurrent</span>
              </h2>

              {Object.keys(positions).length > 0 ? (
                <div className="table-container">
                  <table>
                    <thead>
                      <tr>
                        <th>Asset</th>
                        <th>Path</th>
                        <th>Qty</th>
                        <th>Entry</th>
                        <th>SL (Risk)</th>
                        <th>TP (Target)</th>
                        <th>Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(positions).map(([sym, trade]) => (
                        <tr key={sym} className="animate-slide">
                          <td style={{ fontWeight: 700 }} className="mono">{sym}</td>
                          <td><span className={`tag tag-${trade.side?.toLowerCase() === 'buy' ? 'buy' : 'sell'}`}>{trade.side}</span></td>
                          <td className="mono">{trade.qty}</td>
                          <td className="mono">₹{trade.entry_price?.toFixed(2)}</td>
                          <td className="mono" style={{ color: 'var(--danger)' }}>₹{trade.stop_loss?.toFixed(2)}</td>
                          <td className="mono" style={{ color: 'var(--success)' }}>₹{trade.target_price?.toFixed(2)}</td>
                          <td>
                            <button onClick={() => handleCloseTrade(sym)} disabled={loading} style={{ background: 'transparent', border:'none', color: 'var(--danger)', cursor:'pointer' }}>
                              <X size={20}/>
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="empty-state">
                  <Terminal size={64} style={{ opacity: 0.1, marginBottom: '20px' }} />
                  <h3 style={{ fontSize: '1.2rem', color: 'var(--text-primary)' }}>Terminal Idle</h3>
                  <p style={{ maxWidth: '300px', margin: '10px auto' }}>Ready for deployment signals. Initialize a trade from the control unit.</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {activeTab === 'journal' && (
        <div className="animate-fade">
          <div className="metrics-grid" style={{ gridTemplateColumns: 'repeat(4, 1fr)' }}>
            <div className="metric-card panel-premium">
              <span className="metric-label">Journal Entries</span>
              <span className="metric-value mono">{journalSummary.total_trades || 0}</span>
            </div>
            <div className="metric-card panel-premium">
              <span className="metric-label">Precision Rate</span>
              <span className="metric-value mono positive">{journalSummary.win_rate || 0}%</span>
            </div>
            <div className="metric-card panel-premium">
              <span className="metric-label">Historical Net PnL</span>
              <span className={`metric-value mono ${(journalSummary.total_pnl || 0) >= 0 ? 'positive' : 'negative'}`}>
                ₹{(journalSummary.total_pnl || 0).toLocaleString('en-IN')}
              </span>
            </div>
            <div className="metric-card panel-premium">
              <span className="metric-label">Max Upside</span>
              <span className="metric-value mono positive">₹{journalSummary.biggest_win?.toLocaleString()}</span>
            </div>
          </div>

          <div className="panel-premium" style={{ marginTop: '2.5rem', padding: '2rem' }}>
            <h2 className="panel-header"><BookOpen size={20} color="#7000ff" /> Archive Ledger</h2>
            {journalTrades.length > 0 ? (
               <div className="table-container">
                 <table>
                   <thead>
                     <tr>
                       <th>Closed Date</th>
                       <th>Asset</th>
                       <th>Side</th>
                       <th>Qty</th>
                       <th>Entry</th>
                       <th>Exit</th>
                       <th>Outcome</th>
                     </tr>
                   </thead>
                   <tbody>
                     {journalTrades.map((t, i) => (
                       <tr key={i}>
                         <td className="mono">{new Date(t.closed_at).toLocaleDateString()}</td>
                         <td style={{ fontWeight: 700 }} className="mono">{t.symbol}</td>
                         <td><span className={`tag tag-${t.side?.toLowerCase() === 'buy' ? 'buy' : 'sell'}`}>{t.side}</span></td>
                         <td className="mono">{t.qty}</td>
                         <td className="mono">₹{t.entry_price?.toFixed(2)}</td>
                         <td className="mono">₹{t.exit_price?.toFixed(2)}</td>
                         <td className={t.pnl >= 0 ? 'positive mono' : 'negative mono'} style={{ fontWeight: 800 }}>
                           {t.pnl >= 0 ? '+' : ''}₹{t.pnl?.toFixed(2)}
                         </td>
                       </tr>
                     ))}
                   </tbody>
                 </table>
               </div>
            ) : (
              <div className="empty-state"><h3>History Empty</h3><p>Complete a cycle to see data here.</p></div>
            )}
          </div>
        </div>
      )}

      {activeTab === 'backtest' && (
        <div className="dashboard-layout animate-fade">
          <div className="col-left">
            <div className="panel-premium" style={{ padding: '2rem' }}>
              <h2 className="panel-header">Simulation Laboratory</h2>
              <form onSubmit={runBacktest}>
                <div className="form-group">
                  <label>Genetic Asset Sequence</label>
                  <input type="text" value={btSymbol} onChange={e => setBtSymbol(e.target.value)} required />
                </div>
                <div className="form-group">
                  <label>Iteration Range (Days)</label>
                  <input type="number" value={btDays} onChange={e => setBtDays(e.target.value)} required max="730" min="1" />
                </div>
                <button type="submit" className="btn-primary" style={{ background: 'linear-gradient(135deg, #00f0ff, #4f46e5)' }} disabled={btLoading}>
                  {btLoading ? "Sequencing..." : "Execute Backtest"}
                </button>
              </form>
            </div>
          </div>

          <div className="col-right">
            {!btResults && !btLoading && (
               <div className="panel-premium empty-state" style={{ minHeight: '600px' }}>
                 <BarChart2 size={64} style={{ opacity: 0.1, marginBottom: '20px' }} />
                 <h3>Laboratory Idle</h3>
                 <p>Initialize a historical simulation to calculate deep analytics.</p>
               </div>
            )}
            {btLoading && (
               <div className="panel-premium empty-state" style={{ minHeight: '600px' }}>
                 <div className="engine-dot pulse" style={{ width:'20px', height:'20px' }}></div>
                 <h3 style={{ marginTop: '20px' }}>Analyzing Historical Streams...</h3>
               </div>
            )}
            {btResults && !btLoading && (
              <div className="panel-premium animate-fade" style={{ minHeight: '600px' }}>
                <div style={{ padding: '2rem' }}>
                  <h2 className="panel-header">Analytic Findings</h2>
                  <div className="metrics-grid">
                     <div className="metric-card panel-premium" style={{ background: 'rgba(0,0,0,0.2)' }}>
                       <span className="metric-label">Max Risk Sink</span>
                       <span className="metric-value mono negative">-{btResults.summary.max_drawdown_pct}%</span>
                     </div>
                     <div className="metric-card panel-premium" style={{ background: 'rgba(0,0,0,0.2)' }}>
                       <span className="metric-label">Factor of Profit</span>
                       <span className="metric-value mono">{btResults.summary.profit_factor}</span>
                     </div>
                     <div className="metric-card pnl-hero panel-premium">
                       <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                         <span className="metric-label">Historical ROI</span>
                         <span className={`metric-value mono ${btResults.summary.total_return_pct >= 0 ? 'positive' : 'negative'}`}>
                           {btResults.summary.total_return_pct >= 0 ? '+' : ''}{btResults.summary.total_return_pct}%
                         </span>
                       </div>
                       <div className="metric-value mono positive" style={{ fontSize: '1rem', opacity: 0.8 }}>W/R: {btResults.summary.win_rate_pct}%</div>
                     </div>
                  </div>

                  {btResults.equity_curve && (
                    <div className="equity-chart-container">
                      <ResponsiveContainer width="100%" height={250}>
                        <AreaChart data={btResults.equity_curve}>
                          <defs>
                            <linearGradient id="colorEquity" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="5%" stopColor="#00f0ff" stopOpacity={0.4}/>
                              <stop offset="95%" stopColor="#00f0ff" stopOpacity={0}/>
                            </linearGradient>
                          </defs>
                          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" vertical={false} />
                          <XAxis dataKey="time" hide />
                          <YAxis domain={['auto', 'auto']} tick={{fill: '#8080a0', fontSize: 10}} orientation="right" tickFormatter={(v) => '₹'+v.toLocaleString()}/>
                          <Tooltip contentStyle={{ background: '#0e1015', border: '1px solid var(--border-glass)', borderRadius: '12px' }} itemStyle={{ color: '#fff' }} />
                          <Area type="monotone" dataKey="equity" stroke="#00f0ff" strokeWidth={3} fillOpacity={1} fill="url(#colorEquity)" />
                        </AreaChart>
                      </ResponsiveContainer>
                    </div>
                  )}

                  <div className="table-container" style={{ marginTop: '2rem', maxHeight: '300px' }}>
                    <table>
                      <thead style={{ position: 'sticky', top: 0, zIndex:10 }}>
                        <tr><th>Opened</th><th>Asset</th><th>Outcome</th></tr>
                      </thead>
                      <tbody>
                        {btResults.trades.map((t, idx) => (
                          <tr key={idx}>
                            <td className="mono">{new Date(t.opened_at).toLocaleDateString()}</td>
                            <td className="mono" style={{ fontWeight: 700 }}>{t.symbol}</td>
                            <td className={t.pnl >= 0 ? 'positive mono' : 'negative mono'}>{t.pnl >= 0 ? '+' : ''}₹{t.pnl}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
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
