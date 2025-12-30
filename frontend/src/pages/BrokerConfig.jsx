import { useState, useEffect, useRef } from 'react'
import api from '../lib/api'

function BrokerConfig() {
  const [config, setConfig] = useState({ api_key: '', client_id: '', pin: '', totp_secret: '' })
  const [savedConfig, setSavedConfig] = useState(null)
  const [status, setStatus] = useState({ is_logged_in: false })
  const [positions, setPositions] = useState([])
  const [holdings, setHoldings] = useState([])
  const [orders, setOrders] = useState([])
  const [funds, setFunds] = useState(null)
  const [runningTrades, setRunningTrades] = useState([])
  const [loading, setLoading] = useState(false)
  const [loginLoading, setLoginLoading] = useState(false)
  const [activeTab, setActiveTab] = useState('positions')
  const [refreshing, setRefreshing] = useState(false)
  const [showHelp, setShowHelp] = useState(false)
  const [symbolSearch, setSymbolSearch] = useState('')
  const [searchResults, setSearchResults] = useState([])
  const [searching, setSearching] = useState(false)
  const [error, setError] = useState(null)
  const [dataLoaded, setDataLoaded] = useState(false)
  const [lastUpdated, setLastUpdated] = useState({})
  
  // Track loading state per tab for progressive loading
  const [tabLoading, setTabLoading] = useState({})
  const abortControllerRef = useRef(null)

  useEffect(() => { fetchStatus(); fetchConfig() }, [])
  // Load data when logged in, but only once
  useEffect(() => { 
    if (status.is_logged_in && !dataLoaded) {
      loadBrokerDataSequential()
    }
  }, [status.is_logged_in, dataLoaded])

  const fetchConfig = async () => {
    try {
      const r = await api.get('/broker/config')
      let configObj = r.data
      if (Array.isArray(r.data.brokers)) {
        configObj = r.data.brokers.find(b => b.broker_name === 'angel_one') || r.data.brokers[0]
      }
      setSavedConfig(configObj)
      setConfig(p => ({ ...p, client_id: configObj?.client_id || '' }))
    } catch (e) { /* No config yet */ }
  }

  const fetchStatus = async () => {
    try {
      const r = await api.get('/broker/status')
      console.log('Broker status:', r.data)
      setStatus(r.data)
    } catch (e) {
      console.error('Status fetch error:', e)
      setStatus({ is_logged_in: false })
    }
  }

  // Load broker data sequentially to show results faster
  const loadBrokerDataSequential = async () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }
    abortControllerRef.current = new AbortController()
    const signal = abortControllerRef.current.signal
    
    setRefreshing(true)
    setError(null)
    
    try {
      // Load funds first (fastest, most important for display)
      setTabLoading(p => ({ ...p, funds: true }))
      const fundRes = await api.get('/broker/funds', { signal }).catch(() => ({ data: { data: null } }))
      setFunds(fundRes.data?.data || null)
      if (fundRes.data?.cached_at) setLastUpdated(p => ({ ...p, funds: fundRes.data.cached_at }))
      setTabLoading(p => ({ ...p, funds: false }))
      
      // Then load positions (usually small dataset)
      setTabLoading(p => ({ ...p, positions: true }))
      const posRes = await api.get('/broker/positions', { signal }).catch(() => ({ data: { data: [] } }))
      setPositions(posRes.data?.data || [])
      if (posRes.data?.cached_at) setLastUpdated(p => ({ ...p, positions: posRes.data.cached_at }))
      setTabLoading(p => ({ ...p, positions: false }))
      
      // Load pending trades
      const tradesRes = await api.get('/trades?status=PENDING,APPROVED', { signal }).catch(() => ({ data: [] }))
      setRunningTrades(Array.isArray(tradesRes.data) ? tradesRes.data : [])
      
      // Load orders
      setTabLoading(p => ({ ...p, orders: true }))
      const ordRes = await api.get('/broker/orders', { signal }).catch(() => ({ data: { data: [] } }))
      setOrders(ordRes.data?.data || [])
      if (ordRes.data?.cached_at) setLastUpdated(p => ({ ...p, orders: ordRes.data.cached_at }))
      setTabLoading(p => ({ ...p, orders: false }))
      
      // Holdings last (slowest due to LTP enrichment)
      setTabLoading(p => ({ ...p, holdings: true }))
      const holdRes = await api.get('/broker/holdings', { signal }).catch(() => ({ data: { data: [] } }))
      setHoldings(holdRes.data?.data || [])
      if (holdRes.data?.cached_at) setLastUpdated(p => ({ ...p, holdings: holdRes.data.cached_at }))
      setTabLoading(p => ({ ...p, holdings: false }))
      
      setDataLoaded(true)
    } catch (e) {
      if (e.name !== 'AbortError' && e.name !== 'CanceledError') {
        console.error('Error loading broker data:', e)
        setError('Failed to load some broker data')
      }
    }
    setRefreshing(false)
  }

  const refreshAllData = async () => {
    setDataLoaded(false)
    await loadBrokerDataSequential()
  }

  const formatLastUpdated = (timestamp) => {
    if (!timestamp) return ''
    const seconds = Math.floor(Date.now() / 1000 - timestamp)
    if (seconds < 5) return '🟢 Live'
    if (seconds < 30) return `🟡 ${seconds}s ago`
    return `🔴 ${seconds}s ago`
  }

  const handleConfigSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      await api.post('/broker/config', config)
      fetchConfig()
      setConfig(p => ({ ...p, pin: '', totp_secret: '' }))
    } catch (e) {
      setError(e.response?.data?.detail || e.message)
    }
    setLoading(false)
  }

  const handleLogin = async () => {
    setLoginLoading(true)
    setError(null)
    try {
      const response = await api.post('/broker/login')
      console.log('Login successful:', response.data)
      await fetchStatus()
      // Small delay to allow status to update
      setTimeout(refreshAllData, 500)
    } catch (e) {
      console.error('Login error:', e)
      setError(e.response?.data?.detail || e.message)
    }
    setLoginLoading(false)
  }

  const handleLogout = async () => {
    try {
      await api.post('/broker/logout')
      setStatus({ is_logged_in: false })
      setPositions([]); setHoldings([]); setOrders([]); setFunds(null)
    } catch (e) { alert(e.message) }
  }

  const handleCancelOrder = async (id) => {
    if (!confirm('Cancel this order?')) return
    try {
      await api.delete('/broker/orders/' + id)
      refreshAllData()
    } catch (e) { alert(e.response?.data?.detail || e.message) }
  }

  const handleSymbolSearch = async (e) => {
    e.preventDefault()
    if (symbolSearch.length < 2) return
    setSearching(true)
    try {
      const r = await api.get('/broker/symbols/search?query=' + encodeURIComponent(symbolSearch))
      setSearchResults(r.data.symbols || [])
    } catch (e) { setSearchResults([]) }
    setSearching(false)
  }

  const fmt = (v) => v ? '₹' + parseFloat(v).toFixed(2) : '-'
  const pnlColor = (v) => parseFloat(v) >= 0 ? 'var(--success-color)' : 'var(--danger-color)'

  return (
    <div>
      {/* Header */}
      <div style={{ marginBottom: '2rem' }}>
        <h1 style={{ marginBottom: '0.5rem' }}>Angel One Broker</h1>
        <p style={{ color: 'var(--text-secondary)', margin: 0 }}>Connect and manage your Angel One trading account</p>
      </div>

      {/* Error Banner */}
      {error && (
        <div style={{ padding: '1rem', marginBottom: '1.5rem', backgroundColor: 'rgba(239, 68, 68, 0.1)', border: '1px solid var(--danger-color)', borderRadius: '0.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ color: 'var(--danger-color)' }}>⚠️ {error}</span>
          <button onClick={() => setError(null)} style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '1.2rem' }}>×</button>
        </div>
      )}

      <div className="grid grid-2">
        {/* Configuration Card */}
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
            <h2 style={{ margin: 0 }}>Configuration</h2>
            <button onClick={() => setShowHelp(!showHelp)} className="btn" style={{ fontSize: '0.8rem' }}>
              {showHelp ? 'Hide Help' : '? Help'}
            </button>
          </div>

          {showHelp && (
            <div style={{ marginBottom: '1.5rem', padding: '1rem', backgroundColor: 'rgba(59, 130, 246, 0.05)', borderRadius: '0.5rem', borderLeft: '3px solid var(--primary-color)' }}>
              <h4 style={{ margin: '0 0 0.75rem', color: 'var(--primary-color)' }}>How to get credentials:</h4>
              <ul style={{ margin: 0, paddingLeft: '1.25rem', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
                <li><strong>API Key:</strong> SmartAPI Portal → Create App</li>
                <li><strong>Client ID:</strong> Your Angel One account ID</li>
                <li><strong>PIN:</strong> Your 4-digit trading PIN</li>
                <li><strong>TOTP Secret:</strong> From authenticator app setup</li>
              </ul>
            </div>
          )}

          <form onSubmit={handleConfigSubmit}>
            <div className="form-group">
              <label>API Key</label>
              <input type="text" value={config.api_key} onChange={e => setConfig({ ...config, api_key: e.target.value })} placeholder="Enter API Key" required />
            </div>
            <div className="form-group">
              <label>Client ID</label>
              <input type="text" value={config.client_id} onChange={e => setConfig({ ...config, client_id: e.target.value })} placeholder="e.g., A12345" required />
            </div>
            <div className="form-group">
              <label>PIN (4 digits)</label>
              <input type="password" value={config.pin} onChange={e => setConfig({ ...config, pin: e.target.value })} maxLength={4} placeholder="••••" required />
            </div>
            <div className="form-group">
              <label>TOTP Secret</label>
              <input type="password" value={config.totp_secret} onChange={e => setConfig({ ...config, totp_secret: e.target.value })} placeholder="From authenticator setup" required />
            </div>
            <button type="submit" className="btn btn-primary" disabled={loading} style={{ width: '100%' }}>
              {loading ? 'Saving...' : '💾 Save Configuration'}
            </button>
          </form>

          {savedConfig && (
            <div style={{ marginTop: '1rem', padding: '0.75rem', backgroundColor: 'var(--bg-color)', borderRadius: '0.5rem', fontSize: '0.9rem' }}>
              <strong>Saved:</strong> {savedConfig.client_id}
              {savedConfig.has_totp_secret && <span style={{ marginLeft: '0.5rem', color: 'var(--success-color)' }}>✓ TOTP configured</span>}
            </div>
          )}
        </div>

        {/* Connection Card */}
        <div className="card">
          <h2 style={{ marginBottom: '1.5rem' }}>Connection Status</h2>
          
          <div style={{ textAlign: 'center', padding: '2rem', backgroundColor: 'var(--bg-color)', borderRadius: '0.75rem', marginBottom: '1.5rem' }}>
            <div style={{
              width: '80px', height: '80px', borderRadius: '50%', margin: '0 auto 1rem',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              backgroundColor: status.is_logged_in ? 'rgba(16,185,129,0.2)' : 'rgba(239,68,68,0.2)',
              border: `3px solid ${status.is_logged_in ? 'var(--success-color)' : 'var(--danger-color)'}`
            }}>
              <span style={{ fontSize: '2rem' }}>{status.is_logged_in ? '✓' : '✗'}</span>
            </div>
            <h3 style={{ margin: '0 0 0.5rem', color: status.is_logged_in ? 'var(--success-color)' : 'var(--danger-color)' }}>
              {status.is_logged_in ? 'Connected' : 'Disconnected'}
            </h3>
            {status.client_id && <p style={{ color: 'var(--text-secondary)', margin: 0 }}>Client: {status.client_id}</p>}
          </div>

          {!status.is_logged_in ? (
            savedConfig?.has_totp_secret ? (
              <button onClick={handleLogin} className="btn btn-success" disabled={loginLoading} style={{ width: '100%' }}>
                {loginLoading ? (
                  <><span className="loading-spinner" style={{ width: '16px', height: '16px', marginRight: '0.5rem' }}></span>Connecting...</>
                ) : '🔌 Connect to Angel One'}
              </button>
            ) : (
              <div style={{ textAlign: 'center', padding: '1rem', backgroundColor: 'rgba(251, 191, 36, 0.1)', borderRadius: '0.5rem' }}>
                <p style={{ margin: 0, color: 'var(--text-secondary)' }}>⚠️ Save configuration first</p>
              </div>
            )
          ) : (
            <button onClick={handleLogout} className="btn btn-danger" style={{ width: '100%' }}>
              🔌 Disconnect
            </button>
          )}

          {/* Funds Display */}
          {status.is_logged_in && funds && (
            <div style={{ marginTop: '1.5rem', padding: '1.25rem', background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(59, 130, 246, 0.1) 100%)', borderRadius: '0.75rem' }}>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>Available Funds</div>
              <div style={{ fontSize: '1.75rem', fontWeight: 'bold', color: 'var(--success-color)' }}>
                {fmt(funds.availablecash || funds.net)}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Portfolio Data */}
      {status.is_logged_in && (
        <div className="card" style={{ marginTop: '1.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              {['positions', 'running', 'holdings', 'orders'].map(tab => (
                <button key={tab} onClick={() => setActiveTab(tab)} className={activeTab === tab ? 'btn btn-primary' : 'btn'}>
                  {tab === 'running' ? 'Running Trades' : tab.charAt(0).toUpperCase() + tab.slice(1)}
                  {tab === 'positions' && positions.length > 0 && <span className="badge" style={{ marginLeft: '0.5rem' }}>{positions.length}</span>}
                  {tab === 'running' && runningTrades.length > 0 && <span className="badge" style={{ marginLeft: '0.5rem', backgroundColor: 'var(--warning-color)' }}>{runningTrades.length}</span>}
                  {tab === 'orders' && orders.length > 0 && <span className="badge" style={{ marginLeft: '0.5rem' }}>{orders.length}</span>}
                </button>
              ))}
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
              {lastUpdated[activeTab] && (
                <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                  {formatLastUpdated(lastUpdated[activeTab])}
                </span>
              )}
              <button onClick={refreshAllData} className="btn" disabled={refreshing}>
                {refreshing ? '↻ Refreshing...' : '↻ Refresh'}
              </button>
            </div>
          </div>

          {/* Positions Tab */}
          {activeTab === 'positions' && (
            positions.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-secondary)' }}>
                <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>📊</div>
                <p>No open positions</p>
              </div>
            ) : (
              <div className="table-container">
                <table>
                  <thead>
                    <tr><th>Symbol</th><th>Qty</th><th>Avg Price</th><th>LTP</th><th>P&L</th></tr>
                  </thead>
                  <tbody>
                    {positions.map((p, i) => (
                      <tr key={i}>
                        <td><strong>{p.tradingsymbol}</strong></td>
                        <td>{p.netqty}</td>
                        <td>{fmt(p.avgnetprice)}</td>
                        <td>{fmt(p.ltp)}</td>
                        <td style={{ color: pnlColor(p.pnl), fontWeight: 'bold' }}>{fmt(p.pnl)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )
          )}

          {/* Running Trades Tab */}
          {activeTab === 'running' && (
            runningTrades.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-secondary)' }}>
                <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>🎯</div>
                <p>No active signal trades</p>
                <p style={{ fontSize: '0.85rem', margin: '0.5rem 0 0' }}>Trades from Telegram signals will appear here</p>
              </div>
            ) : (
              <div className="table-container">
                <table>
                  <thead>
                    <tr><th>Symbol</th><th>Action</th><th>Qty</th><th>Entry</th><th>Target</th><th>SL</th><th>Status</th><th>Created</th></tr>
                  </thead>
                  <tbody>
                    {runningTrades.map((t, i) => (
                      <tr key={i}>
                        <td><strong>{t.symbol}</strong></td>
                        <td>
                          <span style={{ color: t.action === 'BUY' ? 'var(--success-color)' : 'var(--danger-color)', fontWeight: 'bold' }}>
                            {t.action}
                          </span>
                        </td>
                        <td>{t.quantity}</td>
                        <td>{fmt(t.entry_price)}</td>
                        <td style={{ color: 'var(--success-color)' }}>{fmt(t.target_price)}</td>
                        <td style={{ color: 'var(--danger-color)' }}>{fmt(t.stop_loss)}</td>
                        <td>
                          <span className={`badge badge-${t.status === 'APPROVED' ? 'success' : 'pending'}`}>
                            {t.status}
                          </span>
                        </td>
                        <td style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                          {new Date(t.created_at).toLocaleString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )
          )}

          {/* Holdings Tab */}
          {activeTab === 'holdings' && (
            holdings.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-secondary)' }}>
                <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>📦</div>
                <p>No holdings</p>
              </div>
            ) : (
              <div className="table-container">
                <table>
                  <thead>
                    <tr><th>Symbol</th><th>Qty</th><th>Avg Price</th><th>LTP</th><th>P&L</th></tr>
                  </thead>
                  <tbody>
                    {holdings.map((h, i) => (
                      <tr key={i}>
                        <td><strong>{h.tradingsymbol}</strong></td>
                        <td>{h.quantity}</td>
                        <td>{fmt(h.averageprice)}</td>
                        <td>{fmt(h.ltp)}</td>
                        <td style={{ color: pnlColor(h.profitandloss), fontWeight: 'bold' }}>{fmt(h.profitandloss)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )
          )}

          {/* Orders Tab */}
          {activeTab === 'orders' && (
            orders.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-secondary)' }}>
                <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>📋</div>
                <p>No orders today</p>
              </div>
            ) : (
              <div className="table-container">
                <table>
                  <thead>
                    <tr><th>Symbol</th><th>Type</th><th>Qty</th><th>Price</th><th>Status</th><th></th></tr>
                  </thead>
                  <tbody>
                    {orders.map((o, i) => (
                      <tr key={i}>
                        <td><strong>{o.tradingsymbol}</strong></td>
                        <td>
                          <span style={{ color: o.transactiontype === 'BUY' ? 'var(--success-color)' : 'var(--danger-color)', fontWeight: 'bold' }}>
                            {o.transactiontype}
                          </span>
                        </td>
                        <td>{o.quantity}</td>
                        <td>{fmt(o.price)}</td>
                        <td>
                          <span className={`badge badge-${o.status === 'complete' ? 'success' : o.status === 'open' ? 'pending' : 'danger'}`}>
                            {o.status}
                          </span>
                        </td>
                        <td>
                          {o.status === 'open' && (
                            <button onClick={() => handleCancelOrder(o.orderid)} className="btn btn-danger" style={{ padding: '0.25rem 0.5rem', fontSize: '0.8rem' }}>
                              Cancel
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )
          )}
        </div>
      )}

      {/* Symbol Search */}
      <div className="card" style={{ marginTop: '1.5rem' }}>
        <h2 style={{ marginBottom: '1rem' }}>Symbol Search</h2>
        <form onSubmit={handleSymbolSearch} style={{ display: 'flex', gap: '1rem', marginBottom: '1rem' }}>
          <input 
            type="text" 
            value={symbolSearch} 
            onChange={e => setSymbolSearch(e.target.value.toUpperCase())} 
            placeholder="Search symbol (e.g., RELIANCE)" 
            style={{ flex: 1 }} 
          />
          <button type="submit" className="btn btn-primary" disabled={searching || symbolSearch.length < 2}>
            {searching ? 'Searching...' : '🔍 Search'}
          </button>
        </form>

        {searchResults.length > 0 && (
          <div className="table-container">
            <table>
              <thead>
                <tr><th>Symbol</th><th>Name</th><th>Token</th><th>Exchange</th></tr>
              </thead>
              <tbody>
                {searchResults.map((r, i) => (
                  <tr key={i}>
                    <td><strong>{r.symbol}</strong></td>
                    <td style={{ color: 'var(--text-secondary)' }}>{r.name}</td>
                    <td style={{ fontFamily: 'monospace' }}>{r.token}</td>
                    <td>{r.exchange}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

export default BrokerConfig
