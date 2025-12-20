import { useState, useEffect } from 'react'
import axios from 'axios'

function BrokerConfig() {
  const [config, setConfig] = useState({ api_key: '', client_id: '', pin: '', totp_secret: '' })
  const [savedConfig, setSavedConfig] = useState(null)
  const [status, setStatus] = useState({ is_logged_in: false })
  const [positions, setPositions] = useState([])
  const [holdings, setHoldings] = useState([])
  const [orders, setOrders] = useState([])
  const [funds, setFunds] = useState(null)
  const [loading, setLoading] = useState(false)
  const [loginLoading, setLoginLoading] = useState(false)
  const [symbolSearch, setSymbolSearch] = useState('')
  const [searchResults, setSearchResults] = useState([])
  const [searching, setSearching] = useState(false)
  const [showHelp, setShowHelp] = useState(false)
  const [activeTab, setActiveTab] = useState('positions')
  const [refreshing, setRefreshing] = useState(false)

  useEffect(() => { fetchStatus(); fetchConfig() }, [])
  useEffect(() => { if (status.is_logged_in) refreshAllData() }, [status.is_logged_in])

  const fetchConfig = async () => {
    try {
      const r = await axios.get('/api/broker/config');
      let configObj = r.data;
      // If response is a list (multi-broker), pick Angel One
      if (Array.isArray(r.data.brokers)) {
        configObj = r.data.brokers.find(b => b.broker_name === 'angel_one') || r.data.brokers[0];
      }
      setSavedConfig(configObj);
      setConfig(p => ({ ...p, client_id: configObj?.client_id || '' }));
    } catch (e) { console.log('No config') }
  }
  const fetchStatus = async () => {
    try { const r = await axios.get('/api/broker/status'); setStatus(r.data) }
    catch (e) { console.error(e) }
  }
  const refreshAllData = async () => {
    setRefreshing(true)
    const [pos, hold, ord, fund] = await Promise.all([
      axios.get('/api/broker/positions').catch(() => ({ data: { data: [] } })),
      axios.get('/api/broker/holdings').catch(() => ({ data: { data: [] } })),
      axios.get('/api/broker/orders').catch(() => ({ data: { data: [] } })),
      axios.get('/api/broker/funds').catch(() => ({ data: { data: null } }))
    ])
    setPositions(pos.data?.data || []); setHoldings(hold.data?.data || [])
    setOrders(ord.data?.data || []); setFunds(fund.data?.data || null)
    setRefreshing(false)
  }
  const handleConfigSubmit = async (e) => {
    e.preventDefault(); setLoading(true)
    try { await axios.post('/api/broker/config', config); alert('Saved!'); fetchConfig(); setConfig(p => ({ ...p, pin: '', totp_secret: '' })) }
    catch (e) { alert('Error: ' + (e.response?.data?.detail || e.message)) }
    setLoading(false)
  }
  const handleLogin = async () => {
    setLoginLoading(true)
    try { await axios.post('/api/broker/login'); alert('Connected!'); fetchStatus() }
    catch (e) { alert('Failed: ' + (e.response?.data?.detail || e.message)) }
    setLoginLoading(false)
  }
  const handleLogout = async () => {
    try { await axios.post('/api/broker/logout'); setStatus({ is_logged_in: false }); setPositions([]); setHoldings([]); setOrders([]); setFunds(null) }
    catch (e) { alert(e.message) }
  }
  const handleCancelOrder = async (id) => {
    if (!confirm('Cancel?')) return
    try { await axios.delete('/api/broker/orders/' + id); refreshAllData() }
    catch (e) { alert(e.response?.data?.detail || e.message) }
  }
  const handleSymbolSearch = async (e) => {
    e.preventDefault(); if (symbolSearch.length < 2) return; setSearching(true)
    try { const r = await axios.get('/api/broker/symbols/search?query=' + encodeURIComponent(symbolSearch)); setSearchResults(r.data.symbols || []) }
    catch (e) { setSearchResults([]) }
    setSearching(false)
  }
  const fmt = (v) => v ? 'Rs ' + parseFloat(v).toFixed(2) : '-'
  const pnl = (v) => parseFloat(v) >= 0 ? 'var(--success-color)' : 'var(--danger-color)'

  return (
    <div>
      <h1 style={{ marginBottom: '2rem' }}>Angel One Broker</h1>
      <div className="grid grid-2">
        <div className="card">
          <h2>Configuration</h2>
          <div style={{ marginBottom: '1rem', padding: '0.75rem', backgroundColor: 'var(--bg-color)', borderRadius: '0.5rem', borderLeft: '3px solid var(--primary-color)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}><strong>Guide</strong><button onClick={() => setShowHelp(!showHelp)} style={{ background: 'none', border: 'none', color: 'var(--primary-color)', cursor: 'pointer' }}>{showHelp ? 'Hide' : 'Show'}</button></div>
            {showHelp && <div style={{ marginTop: '0.5rem', fontSize: '0.85rem' }}><p>API Key: SmartAPI Portal</p><p>Client ID: Account ID</p><p>PIN: 4-digit</p><p>TOTP: Authenticator key</p></div>}
          </div>
          <form onSubmit={handleConfigSubmit}>
            <div className="form-group"><label>API Key</label><input type="text" value={config.api_key} onChange={e => setConfig({ ...config, api_key: e.target.value })} required /></div>
            <div className="form-group"><label>Client ID</label><input type="text" value={config.client_id} onChange={e => setConfig({ ...config, client_id: e.target.value })} required /></div>
            <div className="form-group"><label>PIN</label><input type="password" value={config.pin} onChange={e => setConfig({ ...config, pin: e.target.value })} maxLength={4} required /></div>
            <div className="form-group"><label>TOTP Secret</label><input type="password" value={config.totp_secret} onChange={e => setConfig({ ...config, totp_secret: e.target.value })} required /></div>
            <button type="submit" className="btn btn-primary" disabled={loading} style={{ width: '100%' }}>{loading ? 'Saving...' : 'Save'}</button>
          </form>
          {savedConfig && <div style={{ marginTop: '0.75rem', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Saved: {savedConfig.client_id} {savedConfig.has_totp_secret && '(TOTP OK)'}</div>}
        </div>
        <div className="card">
          <h2>Connection</h2>
          <div style={{ textAlign: 'center', padding: '1.5rem', backgroundColor: 'var(--bg-color)', borderRadius: '0.75rem', marginBottom: '1rem' }}>
            <div style={{ width: '70px', height: '70px', borderRadius: '50%', margin: '0 auto 1rem', display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: status.is_logged_in ? 'rgba(16,185,129,0.2)' : 'rgba(239,68,68,0.2)', border: '3px solid ' + (status.is_logged_in ? 'var(--success-color)' : 'var(--danger-color)') }}><span style={{ fontSize: '1.5rem' }}>{status.is_logged_in ? 'OK' : 'X'}</span></div>
            <h3 style={{ color: status.is_logged_in ? 'var(--success-color)' : 'var(--danger-color)' }}>{status.is_logged_in ? 'Connected' : 'Disconnected'}</h3>
            {status.client_id && <p style={{ color: 'var(--text-secondary)', margin: '0.5rem 0 0' }}>Client: {status.client_id}</p>}
          </div>
          {!status.is_logged_in ? (savedConfig?.has_totp_secret ? <button onClick={handleLogin} className="btn btn-success" disabled={loginLoading} style={{ width: '100%' }}>{loginLoading ? '...' : 'Connect'}</button> : <p style={{ textAlign: 'center', color: 'var(--text-secondary)' }}>Save config first</p>) : <button onClick={handleLogout} className="btn btn-danger" style={{ width: '100%' }}>Disconnect</button>}
          {status.is_logged_in && funds && <div style={{ marginTop: '1rem', padding: '1rem', backgroundColor: 'var(--bg-color)', borderRadius: '0.5rem' }}><strong>Funds:</strong> {fmt(funds.availablecash || funds.net)}</div>}
        </div>
      </div>
      {status.is_logged_in && <div className="card" style={{ marginTop: '1.5rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1rem' }}>
          <div style={{ display: 'flex', gap: '0.5rem' }}>{['positions','holdings','orders'].map(t => <button key={t} onClick={() => setActiveTab(t)} className={activeTab === t ? 'btn btn-primary' : 'btn'}>{t}</button>)}</div>
          <button onClick={refreshAllData} className="btn" disabled={refreshing}>{refreshing ? '...' : 'Refresh'}</button>
        </div>
        {activeTab === 'positions' && (positions.length === 0 ? <p>No positions</p> : <table><thead><tr><th>Symbol</th><th>Qty</th><th>Avg</th><th>LTP</th><th>PnL</th></tr></thead><tbody>{positions.map((p,i) => <tr key={i}><td>{p.tradingsymbol}</td><td>{p.netqty}</td><td>{fmt(p.avgnetprice)}</td><td>{fmt(p.ltp)}</td><td style={{color:pnl(p.pnl)}}>{fmt(p.pnl)}</td></tr>)}</tbody></table>)}
        {activeTab === 'holdings' && (holdings.length === 0 ? <p>No holdings</p> : <table><thead><tr><th>Symbol</th><th>Qty</th><th>Avg</th><th>LTP</th><th>PnL</th></tr></thead><tbody>{holdings.map((h,i) => <tr key={i}><td>{h.tradingsymbol}</td><td>{h.quantity}</td><td>{fmt(h.averageprice)}</td><td>{fmt(h.ltp)}</td><td style={{color:pnl(h.profitandloss)}}>{fmt(h.profitandloss)}</td></tr>)}</tbody></table>)}
        {activeTab === 'orders' && (orders.length === 0 ? <p>No orders</p> : <table><thead><tr><th>Symbol</th><th>Type</th><th>Qty</th><th>Status</th><th></th></tr></thead><tbody>{orders.map((o,i) => <tr key={i}><td>{o.tradingsymbol}</td><td>{o.transactiontype}</td><td>{o.quantity}</td><td>{o.status}</td><td>{o.status === 'open' && <button onClick={() => handleCancelOrder(o.orderid)} className="btn btn-danger">X</button>}</td></tr>)}</tbody></table>)}
      </div>}
      <div className="card" style={{ marginTop: '1.5rem' }}>
        <h2>Symbol Search</h2>
        <form onSubmit={handleSymbolSearch} style={{ display: 'flex', gap: '1rem' }}>
          <input type="text" value={symbolSearch} onChange={e => setSymbolSearch(e.target.value.toUpperCase())} placeholder="RELIANCE" style={{ flex: 1 }} />
          <button type="submit" className="btn btn-primary" disabled={searching}>Search</button>
        </form>
        {searchResults.length > 0 && <table style={{marginTop:'1rem'}}><thead><tr><th>Symbol</th><th>Name</th><th>Token</th><th>Exchange</th></tr></thead><tbody>{searchResults.map((r,i) => <tr key={i}><td>{r.symbol}</td><td>{r.name}</td><td>{r.token}</td><td>{r.exchange}</td></tr>)}</tbody></table>}
      </div>
    </div>
  )
}
export default BrokerConfig
