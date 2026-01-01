import { useState, useEffect } from 'react'
import api from '../lib/api'

function SignalTester() {
  const [message, setMessage] = useState('')
  const [parseResult, setParseResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [balance, setBalance] = useState(null)
  const [positions, setPositions] = useState({ open: [], closed: [] })
  const [stats, setStats] = useState(null)
  const [aiStatus, setAiStatus] = useState(null)
  const [activeTab, setActiveTab] = useState('tester')
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState(null)

  const sampleMessages = [
    "BUY RELIANCE @ 2450 Target 2500 SL 2420",
    "TATASTEEL looking weak, sell below 145 for target 135, keep SL at 152",
    "INFY is bullish! Entry around 1800, book profit at 1850-1880",
    "NIFTY 23500 CE buy above 150, targets 180/200, strict SL 120",
    "Accumulate HDFCBANK in 1650-1660 zone, SL 1620, TGT 1720",
    "banknifty 53200 pe buy above 350 tgt 400 sl 290",
    "nifty 24000 ce buy at 200 target 250 sl 180"
  ]

  useEffect(() => {
    fetchAiStatus()
    fetchBalance()
    fetchPositions()
    fetchStats()
  }, [])

  const fetchAiStatus = async () => {
    try {
      const r = await api.get('/paper/ai-status')
      setAiStatus(r.data)
    } catch (e) { /* AI status optional */ }
  }

  const fetchBalance = async () => {
    try {
      const r = await api.get('/paper/balance')
      setBalance(r.data)
    } catch (e) { console.error(e) }
  }

  const fetchPositions = async () => {
    try {
      const r = await api.get('/paper/positions')
      setPositions({ open: r.data.open_positions || [], closed: r.data.closed_positions || [] })
    } catch (e) { console.error(e) }
  }

  const fetchStats = async () => {
    try {
      const r = await api.get('/paper/stats')
      setStats(r.data)
    } catch (e) { console.error(e) }
  }

  const refreshAll = async () => {
    setRefreshing(true)
    await Promise.all([fetchBalance(), fetchPositions(), fetchStats()])
    setRefreshing(false)
  }

  const testSignal = async () => {
    if (!message.trim()) return
    setLoading(true)
    setParseResult(null)
    setError(null)
    try {
      const r = await api.post('/paper/test-signal', { message })
      setParseResult(r.data)
    } catch (e) {
      setError(e.response?.data?.detail || e.message)
    }
    setLoading(false)
  }

  const executePaperTrade = async () => {
    if (!message.trim()) return
    setLoading(true)
    setError(null)
    try {
      const r = await api.post('/paper/simulate?execute_paper=true', { message })
      setParseResult(r.data)
      if (r.data.paper_trade?.status === 'success') {
        refreshAll()
      }
    } catch (e) {
      setError(e.response?.data?.detail || e.message)
    }
    setLoading(false)
  }

  const closePosition = async (id) => {
    if (!confirm('Close this position?')) return
    try {
      await api.post(`/paper/positions/${id}/close`)
      refreshAll()
    } catch (e) {
      alert(e.response?.data?.detail || e.message)
    }
  }

  const updatePrices = async () => {
    try {
      const r = await api.post('/paper/update-prices')
      alert(`Updated ${r.data.updated} positions`)
      refreshAll()
    } catch (e) {
      alert(e.response?.data?.detail || 'Connect broker to update prices')
    }
  }

  const resetPaperTrading = async () => {
    if (!confirm('Reset all paper trades? This cannot be undone!')) return
    try {
      await api.post('/paper/reset')
      refreshAll()
    } catch (e) {
      alert(e.response?.data?.detail || e.message)
    }
  }

  const fmt = (v) => v != null ? '₹' + parseFloat(v).toFixed(2) : '-'
  const pnlColor = (v) => parseFloat(v) >= 0 ? 'var(--success-color)' : 'var(--danger-color)'

  const tabs = [
    { id: 'tester', label: 'Signal Tester', icon: '🔍' },
    { id: 'positions', label: 'Open Positions', icon: '📊', count: positions.open.length },
    { id: 'history', label: 'History', icon: '📜', count: positions.closed.length },
    { id: 'stats', label: 'Stats', icon: '📈' }
  ]

  return (
    <div>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h1 style={{ marginBottom: '0.5rem' }}>Signal Tester & Paper Trading</h1>
          <p style={{ color: 'var(--text-secondary)', margin: 0 }}>Test signals and practice trading with virtual money</p>
        </div>
        {aiStatus && (
          <div style={{
            padding: '0.5rem 1rem', borderRadius: '2rem',
            backgroundColor: aiStatus.ai_enabled ? 'rgba(139, 92, 246, 0.1)' : 'rgba(100, 100, 100, 0.1)',
            border: `1px solid ${aiStatus.ai_enabled ? 'rgb(139, 92, 246)' : 'var(--border-color)'}`,
            display: 'flex', alignItems: 'center', gap: '0.5rem'
          }}>
            <span>{aiStatus.ai_enabled ? '🤖' : '📝'}</span>
            <span style={{ fontWeight: 'bold', color: aiStatus.ai_enabled ? 'rgb(139, 92, 246)' : 'var(--text-secondary)' }}>
              {aiStatus.mode || 'Pattern'} Mode
            </span>
          </div>
        )}
      </div>

      {/* Balance Card */}
      {balance && (
        <div className="card" style={{ marginBottom: '1.5rem', background: 'linear-gradient(135deg, var(--card-bg) 0%, var(--bg-color) 100%)' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '1rem', textAlign: 'center' }}>
            <div>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Initial</div>
              <div style={{ fontSize: '1.25rem', fontWeight: 'bold' }}>{fmt(balance.initial_balance)}</div>
            </div>
            <div>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Available</div>
              <div style={{ fontSize: '1.25rem', fontWeight: 'bold', color: 'var(--primary-color)' }}>{fmt(balance.available_balance)}</div>
            </div>
            <div>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Invested</div>
              <div style={{ fontSize: '1.25rem', fontWeight: 'bold' }}>{fmt(balance.invested_amount)}</div>
            </div>
            <div>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Total P&L</div>
              <div style={{ fontSize: '1.25rem', fontWeight: 'bold', color: pnlColor(balance.total_pnl) }}>
                {fmt(balance.total_pnl)} ({balance.total_pnl_percentage || 0}%)
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem', flexWrap: 'wrap' }}>
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={activeTab === tab.id ? 'btn btn-primary' : 'btn'}
            style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}
          >
            <span>{tab.icon}</span>
            <span>{tab.label}</span>
            {tab.count > 0 && (
              <span style={{
                backgroundColor: activeTab === tab.id ? 'rgba(255,255,255,0.2)' : 'var(--primary-color)',
                color: activeTab === tab.id ? 'white' : 'white',
                padding: '0.1rem 0.4rem', borderRadius: '0.75rem', fontSize: '0.75rem'
              }}>{tab.count}</span>
            )}
          </button>
        ))}
        <div style={{ flex: 1 }} />
        <button onClick={refreshAll} className="btn" disabled={refreshing}>
          {refreshing ? '↻ Refreshing...' : '↻ Refresh'}
        </button>
      </div>

      {/* Signal Tester Tab */}
      {activeTab === 'tester' && (
        <div className="grid grid-2">
          {/* Input Panel */}
          <div className="card">
            <h2 style={{ marginBottom: '0.5rem' }}>Test Signal Message</h2>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '1rem' }}>
              {aiStatus?.ai_enabled
                ? '🤖 AI will intelligently parse your message'
                : '📝 Pattern matching will extract signal data'}
            </p>

            <div className="form-group">
              <textarea
                value={message}
                onChange={e => setMessage(e.target.value)}
                placeholder="Enter any trading message..."
                rows={4}
                style={{ width: '100%', resize: 'vertical' }}
              />
            </div>

            {error && (
              <div style={{ padding: '0.75rem', marginBottom: '1rem', backgroundColor: 'rgba(239, 68, 68, 0.1)', borderRadius: '0.5rem', color: 'var(--danger-color)', fontSize: '0.9rem' }}>
                ⚠️ {error}
              </div>
            )}

            <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem' }}>
              <button onClick={testSignal} className="btn btn-primary" disabled={loading || !message.trim()} style={{ flex: 1 }}>
                {loading ? 'Analyzing...' : '🔍 Analyze Signal'}
              </button>
              <button onClick={executePaperTrade} className="btn btn-success" disabled={loading || !message.trim()} style={{ flex: 1 }}>
                {loading ? '...' : '📈 Execute Paper Trade'}
              </button>
            </div>

            <div>
              <label style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.5rem', display: 'block' }}>
                Try these examples:
              </label>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {sampleMessages.map((msg, i) => (
                  <button
                    key={i}
                    onClick={() => setMessage(msg)}
                    className="btn"
                    style={{ fontSize: '0.8rem', padding: '0.5rem 0.75rem', textAlign: 'left', whiteSpace: 'normal' }}
                  >
                    {msg}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Result Panel */}
          <div className="card">
            <h2 style={{ marginBottom: '1rem' }}>Parse Result</h2>

            {parseResult ? (
              <div>
                {/* Status Banner */}
                <div style={{
                  padding: '0.75rem 1rem', borderRadius: '0.5rem', marginBottom: '1rem',
                  backgroundColor: parseResult.status === 'signal_detected' || parseResult.step ? 'rgba(16,185,129,0.1)' : parseResult.status === 'no_signal' ? 'rgba(251,191,36,0.1)' : 'rgba(239,68,68,0.1)',
                  borderLeft: `3px solid ${parseResult.status === 'signal_detected' || parseResult.step ? 'var(--success-color)' : parseResult.status === 'no_signal' ? 'var(--warning-color)' : 'var(--danger-color)'}`
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <strong>
                      {parseResult.status === 'signal_detected' || parseResult.step ? '✅ Signal Detected' : parseResult.status === 'no_signal' ? '⚠️ No Signal' : '❌ Error'}
                    </strong>
                    {parseResult.ai_used && (
                      <span style={{ fontSize: '0.75rem', padding: '0.2rem 0.5rem', borderRadius: '1rem', backgroundColor: 'rgba(139, 92, 246, 0.2)', color: 'rgb(139, 92, 246)' }}>
                        🤖 AI
                      </span>
                    )}
                  </div>
                </div>

                {/* Confidence */}
                {parseResult.confidence && (
                  <div style={{ marginBottom: '1rem', padding: '0.75rem', backgroundColor: 'rgba(139, 92, 246, 0.05)', borderRadius: '0.5rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' }}>
                      <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Confidence:</span>
                      <div style={{ flex: 1, height: '6px', backgroundColor: 'var(--bg-color)', borderRadius: '3px', overflow: 'hidden' }}>
                        <div style={{
                          width: `${parseResult.confidence * 100}%`, height: '100%',
                          backgroundColor: parseResult.confidence > 0.7 ? 'var(--success-color)' : parseResult.confidence > 0.4 ? 'var(--warning-color)' : 'var(--danger-color)'
                        }} />
                      </div>
                      <span style={{ fontWeight: 'bold' }}>{(parseResult.confidence * 100).toFixed(0)}%</span>
                    </div>
                    {parseResult.reasoning && (
                      <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', fontStyle: 'italic' }}>
                        💭 {parseResult.reasoning}
                      </div>
                    )}
                  </div>
                )}

                {/* Parsed Data */}
                {parseResult.parsed && (
                  <div className="table-container">
                    <table>
                      <tbody>
                        <tr><td style={{ fontWeight: 'bold' }}>Symbol</td><td style={{ fontSize: '1.1rem', fontWeight: 'bold' }}>{parseResult.parsed.symbol}</td></tr>
                        <tr><td style={{ fontWeight: 'bold' }}>Action</td><td style={{ color: parseResult.parsed.action === 'BUY' ? 'var(--success-color)' : 'var(--danger-color)', fontWeight: 'bold' }}>{parseResult.parsed.action}</td></tr>
                        <tr><td style={{ fontWeight: 'bold' }}>Entry</td><td>{parseResult.parsed.entry_price ? fmt(parseResult.parsed.entry_price) : 'Market'}</td></tr>
                        <tr><td style={{ fontWeight: 'bold' }}>Target</td><td style={{ color: 'var(--success-color)' }}>{parseResult.parsed.target_price ? fmt(parseResult.parsed.target_price) : '-'}</td></tr>
                        <tr><td style={{ fontWeight: 'bold' }}>Stop Loss</td><td style={{ color: 'var(--danger-color)' }}>{parseResult.parsed.stop_loss ? fmt(parseResult.parsed.stop_loss) : '-'}</td></tr>
                        <tr><td style={{ fontWeight: 'bold' }}>Quantity</td><td>{parseResult.parsed.quantity || '1'}</td></tr>
                      </tbody>
                    </table>
                  </div>
                )}

                {/* Paper Trade Result */}
                {parseResult.paper_trade && (
                  <div style={{ marginTop: '1rem', padding: '0.75rem', backgroundColor: parseResult.paper_trade.status === 'success' ? 'rgba(16,185,129,0.1)' : 'rgba(239,68,68,0.1)', borderRadius: '0.5rem' }}>
                    <strong>📝 Paper Trade: </strong>{parseResult.paper_trade.message}
                    {parseResult.paper_trade.trade && <div style={{ marginTop: '0.5rem', fontSize: '0.9rem' }}>Trade ID: #{parseResult.paper_trade.trade.id}</div>}
                  </div>
                )}
              </div>
            ) : (
              <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-secondary)' }}>
                <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>🔍</div>
                <p>Enter a trading message and click "Analyze Signal"</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Open Positions Tab */}
      {activeTab === 'positions' && (
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h2 style={{ margin: 0 }}>Open Positions ({positions.open.length})</h2>
            <button onClick={updatePrices} className="btn">📊 Update Prices</button>
          </div>

          {positions.open.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-secondary)' }}>
              <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>📊</div>
              <p>No open positions</p>
              <p style={{ fontSize: '0.9rem' }}>Test a signal and execute a paper trade to get started!</p>
            </div>
          ) : (
            <div className="table-container">
              <table>
                <thead>
                  <tr><th>Symbol</th><th>Action</th><th>Qty</th><th>Entry</th><th>Current</th><th>Target</th><th>SL</th><th>P&L</th><th></th></tr>
                </thead>
                <tbody>
                  {positions.open.map(p => (
                    <tr key={p.id}>
                      <td><strong>{p.symbol}</strong></td>
                      <td style={{ color: p.action === 'BUY' ? 'var(--success-color)' : 'var(--danger-color)', fontWeight: 'bold' }}>{p.action}</td>
                      <td>{p.quantity}</td>
                      <td>{fmt(p.entry_price)}</td>
                      <td>{fmt(p.current_price)}</td>
                      <td>{p.target_price ? fmt(p.target_price) : '-'}</td>
                      <td>{p.stop_loss ? fmt(p.stop_loss) : '-'}</td>
                      <td style={{ color: pnlColor(p.pnl), fontWeight: 'bold' }}>{fmt(p.pnl)} ({p.pnl_percentage || 0}%)</td>
                      <td><button onClick={() => closePosition(p.id)} className="btn btn-danger" style={{ padding: '0.25rem 0.5rem', fontSize: '0.8rem' }}>Close</button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* History Tab */}
      {activeTab === 'history' && (
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h2 style={{ margin: 0 }}>Closed Positions ({positions.closed.length})</h2>
            <button onClick={resetPaperTrading} className="btn btn-danger">🗑️ Reset All</button>
          </div>

          {positions.closed.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-secondary)' }}>
              <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>📜</div>
              <p>No closed positions yet</p>
            </div>
          ) : (
            <div className="table-container">
              <table>
                <thead>
                  <tr><th>Symbol</th><th>Action</th><th>Qty</th><th>Entry</th><th>Exit</th><th>P&L</th><th>Reason</th><th>Time</th></tr>
                </thead>
                <tbody>
                  {positions.closed.map(p => (
                    <tr key={p.id}>
                      <td><strong>{p.symbol}</strong></td>
                      <td style={{ color: p.action === 'BUY' ? 'var(--success-color)' : 'var(--danger-color)', fontWeight: 'bold' }}>{p.action}</td>
                      <td>{p.quantity}</td>
                      <td>{fmt(p.entry_price)}</td>
                      <td>{fmt(p.exit_price)}</td>
                      <td style={{ color: pnlColor(p.pnl), fontWeight: 'bold' }}>{fmt(p.pnl)} ({p.pnl_percentage || 0}%)</td>
                      <td>{p.exit_reason || '-'}</td>
                      <td style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>{p.exit_time ? new Date(p.exit_time).toLocaleString() : '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Stats Tab */}
      {activeTab === 'stats' && stats && (
        <div className="grid grid-2">
          <div className="card">
            <h2 style={{ marginBottom: '1.5rem' }}>Performance Summary</h2>
            {stats.ai_enabled && (
              <div style={{ marginBottom: '1rem', padding: '0.5rem', backgroundColor: 'rgba(139, 92, 246, 0.1)', borderRadius: '0.5rem', textAlign: 'center' }}>
                🤖 AI-Powered Analysis
              </div>
            )}

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem' }}>
              {[
                { label: 'Total Trades', value: stats.performance?.total_trades || 0, color: 'var(--primary-color)' },
                { label: 'Win Rate', value: `${stats.performance?.win_rate || 0}%`, color: 'var(--success-color)' },
                { label: 'Winning', value: stats.performance?.winning_trades || 0, color: 'var(--success-color)' },
                { label: 'Losing', value: stats.performance?.losing_trades || 0, color: 'var(--danger-color)' },
                { label: 'Target Hits', value: stats.performance?.target_hits || 0, color: 'var(--success-color)' },
                { label: 'SL Hits', value: stats.performance?.sl_hits || 0, color: 'var(--danger-color)' }
              ].map(item => (
                <div key={item.label} style={{ padding: '1rem', backgroundColor: 'var(--bg-color)', borderRadius: '0.5rem', textAlign: 'center' }}>
                  <div style={{ fontSize: '1.75rem', fontWeight: 'bold', color: item.color }}>{item.value}</div>
                  <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>{item.label}</div>
                </div>
              ))}
            </div>
          </div>

          <div className="card">
            <h2 style={{ marginBottom: '1.5rem' }}>Notable Trades</h2>

            {stats.best_trade ? (
              <div style={{ marginBottom: '1rem', padding: '1rem', backgroundColor: 'rgba(16,185,129,0.1)', borderRadius: '0.5rem' }}>
                <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>🏆 Best Trade</div>
                <div><strong>{stats.best_trade.symbol}</strong></div>
                <div style={{ color: 'var(--success-color)', fontSize: '1.25rem', fontWeight: 'bold' }}>
                  {fmt(stats.best_trade.pnl)} ({stats.best_trade.pnl_percentage || 0}%)
                </div>
              </div>
            ) : (
              <p style={{ color: 'var(--text-secondary)' }}>No completed trades yet</p>
            )}

            {stats.worst_trade && (
              <div style={{ padding: '1rem', backgroundColor: 'rgba(239,68,68,0.1)', borderRadius: '0.5rem' }}>
                <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>📉 Worst Trade</div>
                <div><strong>{stats.worst_trade.symbol}</strong></div>
                <div style={{ color: 'var(--danger-color)', fontSize: '1.25rem', fontWeight: 'bold' }}>
                  {fmt(stats.worst_trade.pnl)} ({stats.worst_trade.pnl_percentage || 0}%)
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default SignalTester
