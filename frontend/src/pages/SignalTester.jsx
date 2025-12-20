import { useState, useEffect } from 'react'
import axios from 'axios'

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

  // Sample messages for quick testing - varied formats to test AI
  const sampleMessages = [
    "BUY RELIANCE @ 2450 Target 2500 SL 2420",
    "TATASTEEL looking weak, sell below 145 for target 135, keep SL at 152",
    "INFY is bullish! Entry around 1800, book profit at 1850-1880",
    "NIFTY 23500 CE buy above 150, targets 180/200, strict SL 120",
    "Accumulate HDFCBANK in 1650-1660 zone, SL 1620, TGT 1720",
    "Short SBIN futures @ 820, target 790, SL 835"
  ]

  useEffect(() => {
    fetchAiStatus()
    fetchBalance()
    fetchPositions()
    fetchStats()
  }, [])

  const fetchAiStatus = async () => {
    try {
      const r = await axios.get('/api/paper/ai-status')
      setAiStatus(r.data)
    } catch (e) { console.error(e) }
  }

  const fetchBalance = async () => {
    try {
      const r = await axios.get('/api/paper/balance')
      setBalance(r.data)
    } catch (e) { console.error(e) }
  }

  const fetchPositions = async () => {
    try {
      const r = await axios.get('/api/paper/positions')
      setPositions({ open: r.data.open_positions || [], closed: r.data.closed_positions || [] })
    } catch (e) { console.error(e) }
  }

  const fetchStats = async () => {
    try {
      const r = await axios.get('/api/paper/stats')
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
    try {
      const r = await axios.post('/api/paper/test-signal', { message })
      setParseResult(r.data)
    } catch (e) {
      setParseResult({ status: 'error', message: e.response?.data?.detail || e.message })
    }
    setLoading(false)
  }

  const executePaperTrade = async () => {
    if (!message.trim()) return
    setLoading(true)
    try {
      const r = await axios.post('/api/paper/simulate?execute_paper=true', { message })
      setParseResult(r.data)
      if (r.data.paper_trade?.status === 'success') {
        refreshAll()
      }
    } catch (e) {
      setParseResult({ status: 'error', message: e.response?.data?.detail || e.message })
    }
    setLoading(false)
  }

  const closePosition = async (id) => {
    if (!confirm('Close this position?')) return
    try {
      await axios.post(`/api/paper/positions/${id}/close`)
      refreshAll()
    } catch (e) {
      alert(e.response?.data?.detail || e.message)
    }
  }

  const updatePrices = async () => {
    try {
      const r = await axios.post('/api/paper/update-prices')
      alert(`Updated ${r.data.updated} positions`)
      refreshAll()
    } catch (e) {
      alert(e.response?.data?.detail || 'Login to broker to update prices')
    }
  }

  const resetPaperTrading = async () => {
    if (!confirm('Reset all paper trades? This cannot be undone!')) return
    try {
      await axios.post('/api/paper/reset')
      refreshAll()
    } catch (e) {
      alert(e.response?.data?.detail || e.message)
    }
  }

  const fmt = (v) => v != null ? 'Rs ' + parseFloat(v).toFixed(2) : '-'
  const pnlColor = (v) => parseFloat(v) >= 0 ? 'var(--success-color)' : 'var(--danger-color)'

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h1>Signal Tester & Paper Trading</h1>
        {aiStatus && (
          <div style={{ 
            padding: '0.5rem 1rem', 
            borderRadius: '2rem', 
            backgroundColor: aiStatus.ai_enabled ? 'rgba(139, 92, 246, 0.1)' : 'rgba(100, 100, 100, 0.1)',
            border: `1px solid ${aiStatus.ai_enabled ? 'rgb(139, 92, 246)' : 'var(--border-color)'}`,
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem'
          }}>
            <span style={{ fontSize: '1rem' }}>{aiStatus.ai_enabled ? '🤖' : '📝'}</span>
            <span style={{ fontWeight: 'bold', color: aiStatus.ai_enabled ? 'rgb(139, 92, 246)' : 'var(--text-secondary)' }}>
              {aiStatus.mode} Mode
            </span>
          </div>
        )}
      </div>
      
      {/* Balance Card */}
      {balance && (
        <div className="card" style={{ marginBottom: '1.5rem', background: 'linear-gradient(135deg, var(--card-bg) 0%, var(--bg-color) 100%)' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '1rem', textAlign: 'center' }}>
            <div>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Initial Balance</div>
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
                {fmt(balance.total_pnl)} ({balance.total_pnl_percentage}%)
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem' }}>
        {['tester', 'positions', 'history', 'stats'].map(tab => (
          <button key={tab} onClick={() => setActiveTab(tab)} className={activeTab === tab ? 'btn btn-primary' : 'btn'}>
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
        <div style={{ flex: 1 }} />
        <button onClick={refreshAll} className="btn" disabled={refreshing}>{refreshing ? '...' : 'Refresh'}</button>
      </div>

      {/* Signal Tester Tab */}
      {activeTab === 'tester' && (
        <div className="grid grid-2">
          <div className="card">
            <h2>Test Signal Message</h2>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '1rem' }}>
              {aiStatus?.ai_enabled 
                ? '🤖 AI will intelligently parse your message and extract trading signals'
                : '📝 Using pattern matching to extract signals (set OPENAI_API_KEY for AI mode)'}
            </p>
            
            <div className="form-group">
              <label>Message</label>
              <textarea
                value={message}
                onChange={e => setMessage(e.target.value)}
                placeholder="Enter any trading message - AI will understand natural language..."
                rows={4}
                style={{ width: '100%', resize: 'vertical' }}
              />
            </div>
            
            <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
              <button onClick={testSignal} className="btn btn-primary" disabled={loading || !message.trim()}>
                {loading ? 'Analyzing...' : '🔍 Analyze Signal'}
              </button>
              <button onClick={executePaperTrade} className="btn btn-success" disabled={loading || !message.trim()}>
                {loading ? '...' : '📈 Execute Paper Trade'}
              </button>
            </div>
            
            <div style={{ marginTop: '1rem' }}>
              <label style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Try these examples:</label>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginTop: '0.5rem' }}>
                {sampleMessages.map((msg, i) => (
                  <button key={i} onClick={() => setMessage(msg)} className="btn" 
                    style={{ fontSize: '0.8rem', padding: '0.5rem', textAlign: 'left', whiteSpace: 'normal' }}>
                    {msg}
                  </button>
                ))}
              </div>
            </div>
          </div>
          
          <div className="card">
            <h2>Parse Result</h2>
            {parseResult ? (
              <div>
                {/* Status Banner */}
                <div style={{ 
                  padding: '0.75rem 1rem', 
                  borderRadius: '0.5rem', 
                  marginBottom: '1rem',
                  backgroundColor: parseResult.status === 'signal_detected' || parseResult.step === 'validate' || parseResult.step === 'execute' ? 'rgba(16,185,129,0.1)' : 
                                   parseResult.status === 'no_signal' ? 'rgba(251,191,36,0.1)' : 'rgba(239,68,68,0.1)',
                  borderLeft: `3px solid ${parseResult.status === 'signal_detected' || parseResult.step === 'validate' || parseResult.step === 'execute' ? 'var(--success-color)' : 
                               parseResult.status === 'no_signal' ? 'var(--warning-color)' : 'var(--danger-color)'}`
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <strong>
                      {parseResult.status === 'signal_detected' || parseResult.step === 'validate' || parseResult.step === 'execute' ? '✅ Signal Detected' : 
                       parseResult.status === 'no_signal' ? '⚠️ No Signal' : '❌ Error'}
                    </strong>
                    {parseResult.ai_used && (
                      <span style={{ fontSize: '0.75rem', padding: '0.25rem 0.5rem', borderRadius: '1rem', backgroundColor: 'rgba(139, 92, 246, 0.2)', color: 'rgb(139, 92, 246)' }}>
                        🤖 AI Parsed
                      </span>
                    )}
                  </div>
                </div>
                
                {/* AI Confidence & Reasoning */}
                {parseResult.confidence && (
                  <div style={{ marginBottom: '1rem', padding: '0.75rem', backgroundColor: 'rgba(139, 92, 246, 0.05)', borderRadius: '0.5rem', border: '1px solid rgba(139, 92, 246, 0.2)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '0.5rem' }}>
                      <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Confidence:</span>
                      <div style={{ flex: 1, height: '8px', backgroundColor: 'var(--bg-color)', borderRadius: '4px', overflow: 'hidden' }}>
                        <div style={{ 
                          width: `${parseResult.confidence * 100}%`, 
                          height: '100%', 
                          backgroundColor: parseResult.confidence > 0.7 ? 'var(--success-color)' : parseResult.confidence > 0.4 ? 'var(--warning-color)' : 'var(--danger-color)',
                          borderRadius: '4px'
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
                
                {/* Parsed Data Table */}
                {parseResult.parsed && (
                  <table>
                    <tbody>
                      <tr><td><strong>Symbol</strong></td><td><strong style={{ fontSize: '1.1rem' }}>{parseResult.parsed.symbol}</strong></td></tr>
                      <tr><td><strong>Action</strong></td><td style={{ color: parseResult.parsed.action === 'BUY' ? 'var(--success-color)' : 'var(--danger-color)', fontWeight: 'bold' }}>{parseResult.parsed.action}</td></tr>
                      <tr><td><strong>Entry Price</strong></td><td>{parseResult.parsed.entry_price ? fmt(parseResult.parsed.entry_price) : 'Market'}</td></tr>
                      <tr><td><strong>Target</strong></td><td>{parseResult.parsed.target_price ? fmt(parseResult.parsed.target_price) : '-'}</td></tr>
                      <tr><td><strong>Stop Loss</strong></td><td>{parseResult.parsed.stop_loss ? fmt(parseResult.parsed.stop_loss) : '-'}</td></tr>
                      <tr><td><strong>Quantity</strong></td><td>{parseResult.parsed.quantity || '1 (default)'}</td></tr>
                      <tr><td><strong>Exchange</strong></td><td>{parseResult.parsed.exchange || 'NSE'}</td></tr>
                      <tr><td><strong>Product</strong></td><td>{parseResult.parsed.product_type || 'INTRADAY'}</td></tr>
                    </tbody>
                  </table>
                )}
                
                {/* Symbol Validation */}
                {parseResult.token_info && (
                  <div style={{ marginTop: '1rem', padding: '0.5rem', backgroundColor: 'var(--bg-color)', borderRadius: '0.25rem' }}>
                    <strong>Symbol Validation: </strong>
                    {parseResult.token_info.found ? 
                      <span style={{ color: 'var(--success-color)' }}>✓ Found on {parseResult.token_info.exchange} (Token: {parseResult.token_info.token})</span> :
                      <span style={{ color: 'var(--danger-color)' }}>✗ {parseResult.token_info.warning}</span>
                    }
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
              <div style={{ color: 'var(--text-secondary)', textAlign: 'center', padding: '2rem' }}>
                <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>🔍</div>
                <p>Enter a trading message and click "Analyze Signal"</p>
                <p style={{ fontSize: '0.85rem', marginTop: '0.5rem' }}>
                  {aiStatus?.ai_enabled ? 'AI will understand natural language signals' : 'Pattern matching will extract signal data'}
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Open Positions Tab */}
      {activeTab === 'positions' && (
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h2>Open Positions ({positions.open.length})</h2>
            <button onClick={updatePrices} className="btn">Update Prices</button>
          </div>
          {positions.open.length === 0 ? (
            <p style={{ color: 'var(--text-secondary)' }}>No open positions. Test a signal and execute a paper trade!</p>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Symbol</th>
                  <th>Action</th>
                  <th>Qty</th>
                  <th>Entry</th>
                  <th>Current</th>
                  <th>Target</th>
                  <th>SL</th>
                  <th>P&L</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {positions.open.map(p => (
                  <tr key={p.id}>
                    <td><strong>{p.symbol}</strong></td>
                    <td style={{ color: p.action === 'BUY' ? 'var(--success-color)' : 'var(--danger-color)' }}>{p.action}</td>
                    <td>{p.quantity}</td>
                    <td>{fmt(p.entry_price)}</td>
                    <td>{fmt(p.current_price)}</td>
                    <td>{p.target_price ? fmt(p.target_price) : '-'}</td>
                    <td>{p.stop_loss ? fmt(p.stop_loss) : '-'}</td>
                    <td style={{ color: pnlColor(p.pnl) }}>{fmt(p.pnl)} ({p.pnl_percentage}%)</td>
                    <td><button onClick={() => closePosition(p.id)} className="btn btn-danger" style={{ padding: '0.25rem 0.5rem' }}>Close</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* History Tab */}
      {activeTab === 'history' && (
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h2>Closed Positions ({positions.closed.length})</h2>
            <button onClick={resetPaperTrading} className="btn btn-danger">Reset All</button>
          </div>
          {positions.closed.length === 0 ? (
            <p style={{ color: 'var(--text-secondary)' }}>No closed positions yet</p>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Symbol</th>
                  <th>Action</th>
                  <th>Qty</th>
                  <th>Entry</th>
                  <th>Exit</th>
                  <th>P&L</th>
                  <th>Reason</th>
                  <th>Time</th>
                </tr>
              </thead>
              <tbody>
                {positions.closed.map(p => (
                  <tr key={p.id}>
                    <td><strong>{p.symbol}</strong></td>
                    <td style={{ color: p.action === 'BUY' ? 'var(--success-color)' : 'var(--danger-color)' }}>{p.action}</td>
                    <td>{p.quantity}</td>
                    <td>{fmt(p.entry_price)}</td>
                    <td>{fmt(p.exit_price)}</td>
                    <td style={{ color: pnlColor(p.pnl) }}>{fmt(p.pnl)} ({p.pnl_percentage}%)</td>
                    <td>{p.exit_reason}</td>
                    <td style={{ fontSize: '0.85rem' }}>{p.exit_time ? new Date(p.exit_time).toLocaleString() : '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* Stats Tab */}
      {activeTab === 'stats' && stats && (
        <div className="grid grid-2">
          <div className="card">
            <h2>Performance Summary</h2>
            {stats.ai_enabled && (
              <div style={{ marginBottom: '1rem', padding: '0.5rem', backgroundColor: 'rgba(139, 92, 246, 0.1)', borderRadius: '0.5rem', textAlign: 'center' }}>
                🤖 AI-Powered Signal Analysis Active
              </div>
            )}
            <table>
              <tbody>
                <tr><td>Total Trades</td><td><strong>{stats.performance?.total_trades || 0}</strong></td></tr>
                <tr><td>Winning Trades</td><td style={{ color: 'var(--success-color)' }}><strong>{stats.performance?.winning_trades || 0}</strong></td></tr>
                <tr><td>Losing Trades</td><td style={{ color: 'var(--danger-color)' }}><strong>{stats.performance?.losing_trades || 0}</strong></td></tr>
                <tr><td>Win Rate</td><td><strong>{stats.performance?.win_rate || 0}%</strong></td></tr>
                <tr><td>Target Hits</td><td style={{ color: 'var(--success-color)' }}><strong>{stats.performance?.target_hits || 0}</strong></td></tr>
                <tr><td>Stop Loss Hits</td><td style={{ color: 'var(--danger-color)' }}><strong>{stats.performance?.sl_hits || 0}</strong></td></tr>
              </tbody>
            </table>
          </div>
          <div className="card">
            <h2>Notable Trades</h2>
            {stats.best_trade ? (
              <div style={{ marginBottom: '1rem', padding: '1rem', backgroundColor: 'rgba(16,185,129,0.1)', borderRadius: '0.5rem' }}>
                <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>🏆 Best Trade</div>
                <div><strong>{stats.best_trade.symbol}</strong></div>
                <div style={{ color: 'var(--success-color)', fontSize: '1.25rem' }}>{fmt(stats.best_trade.pnl)} ({stats.best_trade.pnl_percentage}%)</div>
              </div>
            ) : <p style={{ color: 'var(--text-secondary)' }}>No trades yet</p>}
            {stats.worst_trade && (
              <div style={{ padding: '1rem', backgroundColor: 'rgba(239,68,68,0.1)', borderRadius: '0.5rem' }}>
                <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>📉 Worst Trade</div>
                <div><strong>{stats.worst_trade.symbol}</strong></div>
                <div style={{ color: 'var(--danger-color)', fontSize: '1.25rem' }}>{fmt(stats.worst_trade.pnl)} ({stats.worst_trade.pnl_percentage}%)</div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default SignalTester
