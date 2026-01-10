import { useState, useEffect, useCallback } from 'react'
import api from '../lib/api'

const BROKER_CONFIGS = {
  angel_one: {
    name: 'Angel One',
    icon: '👼',
    color: '#ff6b35',
    fields: [
      { key: 'api_key', label: 'API Key', type: 'text', required: true, help: 'From SmartAPI developer portal' },
      { key: 'client_id', label: 'Client ID', type: 'text', required: true, help: 'Your Angel One account ID' },
      { key: 'pin', label: 'PIN', type: 'password', required: true, maxLength: 4, help: '4-digit trading PIN' },
      { key: 'totp_secret', label: 'TOTP Secret', type: 'password', required: true, help: 'From authenticator setup' }
    ]
  },
  zerodha: {
    name: 'Zerodha Kite',
    icon: '🪁',
    color: '#387ed1',
    fields: [
      { key: 'api_key', label: 'API Key', type: 'text', required: true, help: 'From Kite Connect developer console' },
      { key: 'api_secret', label: 'API Secret', type: 'password', required: true, help: 'API secret from Kite Connect' },
      { key: 'client_id', label: 'Client ID', type: 'text', required: true, help: 'Your Zerodha client ID (e.g., AB1234)' }
    ],
    loginNote: '⚠️ IMPORTANT: Update your Kite Connect app redirect URL to: http://localhost:5173/zerodha-callback.html (After saving, click Connect and follow the browser flow)'
  },
  shoonya: {
    name: 'Shoonya (Finvasia)',
    icon: '🌟',
    color: '#00a86b',
    fields: [
      { key: 'api_key', label: 'Vendor Code', type: 'text', required: true, help: 'Vendor code from Shoonya API portal' },
      { key: 'api_secret', label: 'API Key (App Key)', type: 'password', required: true, help: 'API Secret/App Key from Shoonya API portal' },
      { key: 'client_id', label: 'User ID', type: 'text', required: true, help: 'Your Shoonya user ID' },
      { key: 'pin', label: 'Password', type: 'password', required: true, help: 'Trading password' },
      { key: 'totp_secret', label: 'TOTP/OTP', type: 'password', required: true, help: '6-digit OTP or TOTP secret' },
      { key: 'imei', label: 'Device ID (IMEI)', type: 'text', required: false, help: 'Unique device identifier (optional, defaults to system value)' }
    ]
  }
}

// Format currency
const formatCurrency = (value) => {
  if (value === null || value === undefined) return '₹0'
  const num = parseFloat(value)
  if (isNaN(num)) return '₹0'
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 2 }).format(num)
}

// Format P&L with color
const formatPnL = (value) => {
  const num = parseFloat(value) || 0
  const color = num >= 0 ? 'var(--success-color)' : 'var(--danger-color)'
  const prefix = num >= 0 ? '+' : ''
  return <span style={{ color, fontWeight: 'bold' }}>{prefix}{formatCurrency(num)}</span>
}

function MultiBrokerConfig({ brokerStatus: propBrokerStatus, onBrokerStatusChange }) {
  const [selectedBroker, setSelectedBroker] = useState('angel_one')
  const [config, setConfig] = useState({ broker_name: 'angel_one', api_key: '', api_secret: '', client_id: '', pin: '', totp_secret: '', imei: '' })
  const [availableBrokers, setAvailableBrokers] = useState([])
  const [configuredBrokers, setConfiguredBrokers] = useState([])
  const [activeBroker, setActiveBroker] = useState(null)
  const [loading, setLoading] = useState(false)
  const [connectingBroker, setConnectingBroker] = useState(null)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(null)

  // Trading Dashboard State
  const [activeTab, setActiveTab] = useState('positions')
  const [positions, setPositions] = useState([])
  const [holdings, setHoldings] = useState([])
  const [orders, setOrders] = useState([])
  const [funds, setFunds] = useState(null)
  const [dashboardLoading, setDashboardLoading] = useState(false)
  const [lastRefresh, setLastRefresh] = useState(null)

  // Use prop broker status or default
  const brokerConnected = propBrokerStatus?.is_logged_in || false

  useEffect(() => {
    fetchAvailableBrokers()
    fetchConfiguredBrokers()
    fetchActiveBroker()
    // Fetch trading data if already connected
    if (brokerConnected) {
      fetchTradingData()
    }
  }, [])

  // Helper to refresh broker status from API and notify parent
  const refreshBrokerStatus = async () => {
    try {
      const r = await api.get('/broker/status')
      if (onBrokerStatusChange) {
        onBrokerStatusChange(r.data)
      }
    } catch (e) {
      console.error('Error refreshing broker status:', e)
    }
  }

  // Fetch trading data when broker connects
  useEffect(() => {
    if (brokerConnected) {
      fetchTradingData()
    } else {
      // Clear trading data when disconnected
      setPositions([])
      setHoldings([])
      setOrders([])
      setFunds(null)
    }
  }, [brokerConnected])

  useEffect(() => {
    setConfig(prev => ({ ...prev, broker_name: selectedBroker }))
  }, [selectedBroker])

  // Auto-refresh trading data every 30 seconds when connected
  useEffect(() => {
    if (!brokerConnected) return

    const interval = setInterval(() => {
      fetchTradingData()
    }, 30000)

    return () => clearInterval(interval)
  }, [brokerConnected])


  const fetchTradingData = useCallback(async () => {
    setDashboardLoading(true)
    try {
      const [posRes, holdRes, ordRes, fundRes] = await Promise.all([
        api.get('/broker/positions').catch(() => ({ data: { data: [] } })),
        api.get('/broker/holdings').catch(() => ({ data: { data: [] } })),
        api.get('/broker/orders').catch(() => ({ data: { data: [] } })),
        api.get('/broker/funds').catch(() => ({ data: null }))
      ])

      setPositions(posRes.data?.data || [])
      setHoldings(holdRes.data?.data || [])
      setOrders(ordRes.data?.data || [])
      setFunds(fundRes.data?.data || fundRes.data)
      setLastRefresh(new Date())
    } catch (e) {
      console.error('Error fetching trading data:', e)
    } finally {
      setDashboardLoading(false)
    }
  }, [])

  const fetchAvailableBrokers = async () => {
    try {
      const r = await api.get('/broker/brokers')
      setAvailableBrokers(r.data.brokers || [])
    } catch (e) { console.error(e) }
  }

  const fetchConfiguredBrokers = async () => {
    try {
      const r = await api.get('/broker/brokers/configured')
      setConfiguredBrokers(r.data.brokers || [])
    } catch (e) { console.error(e) }
  }

  const fetchActiveBroker = async () => {
    try {
      const r = await api.get('/broker/brokers/active')
      setActiveBroker(r.data.broker_type)
    } catch (e) { console.error(e) }
  }

  const showMessage = (type, msg) => {
    if (type === 'error') setError(msg)
    else setSuccess(msg)
    setTimeout(() => { setError(null); setSuccess(null) }, 4000)
  }

  const handleConfigSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    try {
      await api.post('/broker/config', config)
      showMessage('success', `${BROKER_CONFIGS[selectedBroker]?.name || selectedBroker} configuration saved!`)
      fetchConfiguredBrokers()
      setConfig({ broker_name: selectedBroker, api_key: '', api_secret: '', client_id: '', pin: '', totp_secret: '', imei: '' })
    } catch (e) {
      showMessage('error', e.response?.data?.detail || e.message)
    }
    setLoading(false)
  }

  const handleLogin = async (brokerType) => {
    setConnectingBroker(brokerType)
    try {
      // Special OAuth flow for Zerodha
      if (brokerType === 'zerodha') {
        const urlResult = await api.get('/broker/zerodha/login-url')
        if (urlResult.data.login_url) {
          // Open login page
          window.open(urlResult.data.login_url, '_blank')

          // Show better instructions
          showMessage('success', '✅ Login page opened! Follow the instructions in the popup.')

          // Better prompt with clear instructions
          setTimeout(() => {
            const requestToken = prompt(
              '📋 ZERODHA LOGIN INSTRUCTIONS:\n\n' +
              '1. Complete login in the opened browser window\n' +
              '2. After successful login, you will be redirected to:\n' +
              '   http://127.0.0.1/?request_token=XXXXX...\n\n' +
              '3. Look for "request_token=" in the URL\n' +
              '4. Copy ONLY the token value (the part after request_token=)\n' +
              '5. Paste it below and click OK\n\n' +
              'Request Token:'
            )

            if (requestToken) {
              // Clean the token (remove any extra params)
              const cleanToken = requestToken.trim().split('&')[0]

              api.post(`/broker/zerodha/complete-login?request_token=${cleanToken}`)
                .then(loginResult => {
                  showMessage('success', '✅ Successfully connected to Zerodha!')
                  fetchConfiguredBrokers()
                  refreshBrokerStatus()
                  fetchTradingData()
                  setConnectingBroker(null)
                })
                .catch(err => {
                  showMessage('error', '❌ Login failed: ' + (err.response?.data?.detail || err.message))
                  setConnectingBroker(null)
                })
            } else {
              setConnectingBroker(null)
            }
          }, 1000)
        }
      } else {
        // Standard login flow for other brokers (Angel One, Shoonya)
        const result = await api.post(`/broker/brokers/${brokerType}/login`)
        if (result.data.status === 'pending' && result.data.login_url) {
          window.open(result.data.login_url, '_blank')
          const requestToken = prompt('Complete login in browser, then enter request token:')
          if (requestToken) {
            const existing = configuredBrokers.find(b => b.broker_type === brokerType)
            await api.post('/broker/config', { broker_name: brokerType, ...existing, pin: requestToken })
            await handleLogin(brokerType)
          }
        } else {
          showMessage('success', `✅ Connected to ${BROKER_CONFIGS[brokerType]?.name || brokerType}!`)
          fetchConfiguredBrokers()
          refreshBrokerStatus()
          fetchTradingData()
        }
        setConnectingBroker(null)
      }
    } catch (e) {
      showMessage('error', '❌ Login failed: ' + (e.response?.data?.detail || e.message))
      setConnectingBroker(null)
    }
  }

  const handleLogout = async (brokerType) => {
    try {
      await api.post(`/broker/brokers/${brokerType}/logout`)
      showMessage('success', `Disconnected from ${BROKER_CONFIGS[brokerType]?.name || brokerType}`)
      fetchConfiguredBrokers()
      // Refresh broker status and notify parent
      refreshBrokerStatus()
    } catch (e) {
      showMessage('error', e.message)
    }
  }

  const handleSetActive = async (brokerType) => {
    try {
      await api.post(`/broker/brokers/active?broker_type=${brokerType}`)
      setActiveBroker(brokerType)
      showMessage('success', `Active broker set to ${BROKER_CONFIGS[brokerType]?.name || brokerType}`)
      // Refresh broker status to notify parent component
      await refreshBrokerStatus()
      // Also refresh trading data since active broker changed
      await fetchTradingData()
      // Refresh configured brokers list to update UI
      await fetchConfiguredBrokers()
    } catch (e) {
      showMessage('error', e.response?.data?.detail || e.message)
    }
  }

  const handleCancelOrder = async (orderId) => {
    if (!window.confirm('Are you sure you want to cancel this order?')) return
    try {
      await api.delete(`/broker/orders/${orderId}`)
      showMessage('success', 'Order cancelled successfully')
      fetchTradingData()
    } catch (e) {
      showMessage('error', 'Failed to cancel order: ' + (e.response?.data?.detail || e.message))
    }
  }

  const brokerConfig = BROKER_CONFIGS[selectedBroker] || BROKER_CONFIGS.angel_one

  // Calculate summary stats
  const totalPositionsPnL = positions.reduce((sum, p) => sum + (parseFloat(p.pnl) || 0), 0)
  const totalHoldingsValue = holdings.reduce((sum, h) => sum + (parseFloat(h.realisedquantity || h.quantity || 0) * parseFloat(h.ltp || h.lastprice || 0)), 0)
  const pendingOrders = orders.filter(o => ['open', 'pending', 'trigger pending'].includes((o.status || '').toLowerCase())).length

  // Render Funds Overview
  const renderFundsOverview = () => {
    if (!funds) return null

    // Parse funds data (varies by broker)
    // Zerodha returns: { available_cash, used_margin, available_margin }
    // Angel One returns: { availablecash, utiliseddebits, collateral, net }
    const availableMargin = parseFloat(
      funds.available_margin || funds.available_cash ||
      funds.availablecash || funds.available?.cash ||
      funds.net || 0
    )
    const usedMargin = parseFloat(
      funds.used_margin || funds.utiliseddebits ||
      funds.utilised?.debits || 0
    )
    const collateral = parseFloat(funds.collateral || 0)

    return (
      <div className="grid grid-4" style={{ marginBottom: '1.5rem' }}>
        <div className="stat-card">
          <div className="stat-value" style={{ color: 'var(--success-color)' }}>{formatCurrency(availableMargin)}</div>
          <div className="stat-label">Available Margin</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{formatCurrency(usedMargin)}</div>
          <div className="stat-label">Used Margin</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{formatCurrency(collateral)}</div>
          <div className="stat-label">Collateral</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ color: totalPositionsPnL >= 0 ? 'var(--success-color)' : 'var(--danger-color)' }}>
            {formatPnL(totalPositionsPnL)}
          </div>
          <div className="stat-label">Today's P&L</div>
        </div>
      </div>
    )
  }

  // Render Positions Tab
  const renderPositions = () => {
    if (positions.length === 0) {
      return (
        <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-secondary)' }}>
          <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>📊</div>
          <p>No open positions</p>
          <p style={{ fontSize: '0.9rem' }}>Intraday positions will appear here</p>
        </div>
      )
    }

    // Calculate positions statistics (handles both Zerodha and Angel One field names)
    const totalUnrealizedPnL = positions.reduce((sum, p) => {
      return sum + (parseFloat(p.pnl || p.unrealised || p.unrealized || p.unrealisedpnl || 0))
    }, 0)
    const totalRealizedPnL = positions.reduce((sum, p) => {
      return sum + (parseFloat(p.realised || p.realized || p.realisedpnl || 0))
    }, 0)
    const totalPnL = totalUnrealizedPnL + totalRealizedPnL
    const buyPositions = positions.filter(p => parseInt(p.netqty || p.quantity || p.buyqty || 0) > 0).length
    const sellPositions = positions.filter(p => parseInt(p.netqty || p.quantity || p.sellqty || 0) < 0).length

    return (
      <div>
        {/* Positions Summary */}
        <div className="grid grid-4" style={{ marginBottom: '1rem' }}>
          <div className="stat-card">
            <div className="stat-value">{positions.length}</div>
            <div className="stat-label">Open Positions ({buyPositions} Long, {sellPositions} Short)</div>
          </div>
          <div className="stat-card">
            <div className="stat-value" style={{ color: totalUnrealizedPnL >= 0 ? 'var(--success-color)' : 'var(--danger-color)' }}>
              {totalUnrealizedPnL >= 0 ? '+' : ''}{formatCurrency(totalUnrealizedPnL)}
            </div>
            <div className="stat-label">Unrealized P&L</div>
          </div>
          <div className="stat-card">
            <div className="stat-value" style={{ color: totalRealizedPnL >= 0 ? 'var(--success-color)' : 'var(--danger-color)' }}>
              {totalRealizedPnL >= 0 ? '+' : ''}{formatCurrency(totalRealizedPnL)}
            </div>
            <div className="stat-label">Realized P&L</div>
          </div>
          <div className="stat-card">
            <div className="stat-value" style={{ color: totalPnL >= 0 ? 'var(--success-color)' : 'var(--danger-color)' }}>
              {totalPnL >= 0 ? '+' : ''}{formatCurrency(totalPnL)}
            </div>
            <div className="stat-label">Total P&L</div>
          </div>
        </div>

        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Symbol</th>
                <th>Type</th>
                <th>Qty</th>
                <th>Buy Avg</th>
                <th>Sell Avg</th>
                <th>LTP</th>
                <th>P&L</th>
              </tr>
            </thead>
            <tbody>
              {positions.map((pos, idx) => {
                // Handle multiple broker field name formats
                const qty = parseInt(pos.netqty || pos.quantity || pos.net_quantity || 0)
                const buyAvg = parseFloat(pos.averageprice || pos.avgprice || pos.average_price || pos.buyavgprice || 0)
                const sellAvg = parseFloat(pos.sellavgprice || pos.sell_average_price || 0)
                const ltp = parseFloat(pos.ltp || pos.lastprice || pos.last_price || 0)
                const pnl = parseFloat(pos.pnl || pos.unrealised || pos.unrealized || 0)
                const productType = pos.producttype || pos.product_type || pos.product || 'INTRADAY'

                return (
                  <tr key={idx}>
                    <td><strong>{pos.tradingsymbol || pos.symbol}</strong></td>
                    <td>
                      <span style={{
                        backgroundColor: productType === 'DELIVERY' || productType === 'CNC' ? 'var(--primary-color)' : 'var(--secondary-color)',
                        color: 'white',
                        padding: '0.2rem 0.5rem',
                        borderRadius: '0.25rem',
                        fontSize: '0.75rem'
                      }}>
                        {productType}
                      </span>
                    </td>
                    <td style={{ color: qty > 0 ? 'var(--success-color)' : qty < 0 ? 'var(--danger-color)' : 'inherit' }}>
                      {qty > 0 ? '+' : ''}{qty}
                    </td>
                    <td>{formatCurrency(buyAvg)}</td>
                    <td>{sellAvg > 0 ? formatCurrency(sellAvg) : '-'}</td>
                    <td>{formatCurrency(ltp)}</td>
                    <td>{formatPnL(pnl)}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    )
  }

  // Render Holdings Tab
  const renderHoldings = () => {
    if (holdings.length === 0) {
      return (
        <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-secondary)' }}>
          <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>💼</div>
          <p>No holdings found</p>
          <p style={{ fontSize: '0.9rem' }}>Delivery stocks will appear here</p>
        </div>
      )
    }

    // Calculate total P&L and day's P&L
    const totalPnL = holdings.reduce((sum, h) => sum + (parseFloat(h.pnl) || 0), 0)
    const daysPnL = holdings.reduce((sum, h) => {
      const dayChange = parseFloat(h.day_change) || 0
      const qty = parseFloat(h.quantity || h.realised_quantity || 0)
      return sum + (dayChange * qty)
    }, 0)
    const totalInvested = holdings.reduce((sum, h) => {
      const qty = parseFloat(h.quantity || h.realised_quantity || 0)
      const avg = parseFloat(h.average_price || h.averageprice || 0)
      return sum + (qty * avg)
    }, 0)
    const totalCurrent = holdings.reduce((sum, h) => {
      const qty = parseFloat(h.quantity || h.realised_quantity || 0)
      const ltp = parseFloat(h.last_price || h.ltp || 0)
      return sum + (qty * ltp)
    }, 0)

    return (
      <div>
        {/* Holdings Summary */}
        <div className="grid grid-4" style={{ marginBottom: '1rem' }}>
          <div className="stat-card">
            <div className="stat-value">{formatCurrency(totalInvested)}</div>
            <div className="stat-label">Invested</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{formatCurrency(totalCurrent)}</div>
            <div className="stat-label">Current Value</div>
          </div>
          <div className="stat-card">
            <div className="stat-value" style={{ color: totalPnL >= 0 ? 'var(--success-color)' : 'var(--danger-color)' }}>
              {totalPnL >= 0 ? '+' : ''}{formatCurrency(totalPnL)}
            </div>
            <div className="stat-label">Total P&L</div>
          </div>
          <div className="stat-card">
            <div className="stat-value" style={{ color: daysPnL >= 0 ? 'var(--success-color)' : 'var(--danger-color)' }}>
              {daysPnL >= 0 ? '+' : ''}{formatCurrency(daysPnL)}
            </div>
            <div className="stat-label">Day's P&L</div>
          </div>
        </div>

        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Symbol</th>
                <th>Qty</th>
                <th>Avg Price</th>
                <th>LTP</th>
                <th>Current Value</th>
                <th>P&L</th>
                <th>P&L %</th>
                <th>Day Change</th>
              </tr>
            </thead>
            <tbody>
              {holdings.map((hold, idx) => {
                // Match Zerodha API field names (with underscores)
                const qty = parseFloat(hold.quantity || hold.realised_quantity || hold.realisedquantity || 0)
                const avgPrice = parseFloat(hold.average_price || hold.averageprice || hold.avg_price || 0)
                const ltp = parseFloat(hold.last_price || hold.ltp || hold.lastprice || hold.close_price || 0)
                const dayChange = parseFloat(hold.day_change) || 0
                const dayChangePercent = parseFloat(hold.day_change_percentage) || 0

                // Use pre-calculated values from API if available, otherwise calculate
                const currentValue = hold.current_value || (qty * ltp)
                const investedValue = hold.invested_value || (qty * avgPrice)
                const pnl = hold.pnl !== undefined ? hold.pnl : (currentValue - investedValue)
                const pnlPercent = hold.pnl_percentage !== undefined
                  ? hold.pnl_percentage
                  : (investedValue > 0 ? ((pnl / investedValue) * 100) : 0)

                return (
                  <tr key={idx}>
                    <td><strong>{hold.tradingsymbol || hold.symbol}</strong></td>
                    <td>{qty}</td>
                    <td>{formatCurrency(avgPrice)}</td>
                    <td>{formatCurrency(ltp)}</td>
                    <td>{formatCurrency(currentValue)}</td>
                    <td>{formatPnL(pnl)}</td>
                    <td style={{ color: pnlPercent >= 0 ? 'var(--success-color)' : 'var(--danger-color)' }}>
                      {pnlPercent >= 0 ? '+' : ''}{parseFloat(pnlPercent).toFixed(2)}%
                    </td>
                    <td style={{ color: dayChange >= 0 ? 'var(--success-color)' : 'var(--danger-color)' }}>
                      {dayChange >= 0 ? '+' : ''}{formatCurrency(dayChange)} ({dayChangePercent.toFixed(2)}%)
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    )
  }

  // Render Orders Tab
  const renderOrders = () => {
    if (orders.length === 0) {
      return (
        <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-secondary)' }}>
          <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>📝</div>
          <p>No orders today</p>
          <p style={{ fontSize: '0.9rem' }}>Your orders will appear here</p>
        </div>
      )
    }

    return (
      <div className="table-container">
        <table>
          <thead>
            <tr>
              <th>Time</th>
              <th>Symbol</th>
              <th>Type</th>
              <th>Side</th>
              <th>Qty</th>
              <th>Price</th>
              <th>Status</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {orders.map((order, idx) => {
              const status = (order.status || order.orderstatus || '').toLowerCase()
              const isPending = ['open', 'pending', 'trigger pending'].includes(status)

              return (
                <tr key={idx}>
                  <td style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                    {order.ordertime || order.updatetime || '-'}
                  </td>
                  <td><strong>{order.tradingsymbol || order.symbol}</strong></td>
                  <td>
                    <span style={{
                      backgroundColor: 'var(--card-bg)',
                      padding: '0.2rem 0.5rem',
                      borderRadius: '0.25rem',
                      fontSize: '0.75rem'
                    }}>
                      {order.ordertype || 'MARKET'}
                    </span>
                  </td>
                  <td>
                    <span style={{
                      color: order.transactiontype === 'BUY' ? 'var(--success-color)' : 'var(--danger-color)',
                      fontWeight: 'bold'
                    }}>
                      {order.transactiontype}
                    </span>
                  </td>
                  <td>{order.quantity}</td>
                  <td>{formatCurrency(order.price || order.averageprice || 0)}</td>
                  <td>
                    <span style={{
                      backgroundColor: isPending ? 'rgba(245, 158, 11, 0.2)' :
                        status === 'complete' ? 'rgba(16, 185, 129, 0.2)' :
                          'rgba(239, 68, 68, 0.2)',
                      color: isPending ? 'var(--warning-color)' :
                        status === 'complete' ? 'var(--success-color)' :
                          'var(--danger-color)',
                      padding: '0.2rem 0.5rem',
                      borderRadius: '0.25rem',
                      fontSize: '0.75rem',
                      textTransform: 'capitalize'
                    }}>
                      {status}
                    </span>
                  </td>
                  <td>
                    {isPending && (
                      <button
                        onClick={() => handleCancelOrder(order.orderid)}
                        className="btn btn-danger"
                        style={{ padding: '0.3rem 0.6rem', fontSize: '0.75rem' }}
                      >
                        Cancel
                      </button>
                    )}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    )
  }

  // Render Trading Dashboard
  const renderTradingDashboard = () => {
    if (!brokerConnected) {
      return (
        <div className="card" style={{ marginTop: '2rem', textAlign: 'center', padding: '3rem' }}>
          <div style={{ fontSize: '4rem', marginBottom: '1rem' }}>📊</div>
          <h2>Trading Dashboard</h2>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>
            Connect to a broker to view your positions, holdings, and orders
          </p>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', color: 'var(--warning-color)' }}>
            <span>⚠️</span> No broker connected
          </div>
        </div>
      )
    }

    return (
      <div className="card" style={{ marginTop: '2rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
          <h2 style={{ margin: 0 }}>📊 Trading Dashboard</h2>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            {lastRefresh && (
              <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                Updated: {lastRefresh.toLocaleTimeString()}
              </span>
            )}
            <button
              onClick={fetchTradingData}
              className="btn"
              disabled={dashboardLoading}
              style={{ padding: '0.5rem 1rem' }}
            >
              {dashboardLoading ? '⏳' : '🔄'} Refresh
            </button>
          </div>
        </div>

        {/* Funds Overview */}
        {renderFundsOverview()}

        {/* Quick Stats */}
        <div className="grid grid-3" style={{ marginBottom: '1.5rem' }}>
          <div
            onClick={() => setActiveTab('positions')}
            style={{
              padding: '1rem',
              borderRadius: '0.5rem',
              backgroundColor: activeTab === 'positions' ? 'var(--primary-color)' : 'var(--bg-color)',
              color: activeTab === 'positions' ? 'white' : 'inherit',
              cursor: 'pointer',
              textAlign: 'center',
              transition: 'all 0.2s'
            }}
          >
            <div style={{ fontSize: '1.5rem', fontWeight: 'bold' }}>{positions.length}</div>
            <div style={{ fontSize: '0.85rem' }}>Positions</div>
          </div>
          <div
            onClick={() => setActiveTab('holdings')}
            style={{
              padding: '1rem',
              borderRadius: '0.5rem',
              backgroundColor: activeTab === 'holdings' ? 'var(--primary-color)' : 'var(--bg-color)',
              color: activeTab === 'holdings' ? 'white' : 'inherit',
              cursor: 'pointer',
              textAlign: 'center',
              transition: 'all 0.2s'
            }}
          >
            <div style={{ fontSize: '1.5rem', fontWeight: 'bold' }}>{holdings.length}</div>
            <div style={{ fontSize: '0.85rem' }}>Holdings</div>
          </div>
          <div
            onClick={() => setActiveTab('orders')}
            style={{
              padding: '1rem',
              borderRadius: '0.5rem',
              backgroundColor: activeTab === 'orders' ? 'var(--primary-color)' : 'var(--bg-color)',
              color: activeTab === 'orders' ? 'white' : 'inherit',
              cursor: 'pointer',
              textAlign: 'center',
              transition: 'all 0.2s'
            }}
          >
            <div style={{ fontSize: '1.5rem', fontWeight: 'bold' }}>
              {orders.length}
              {pendingOrders > 0 && (
                <span style={{
                  fontSize: '0.75rem',
                  backgroundColor: 'var(--warning-color)',
                  color: 'white',
                  padding: '0.1rem 0.4rem',
                  borderRadius: '1rem',
                  marginLeft: '0.5rem'
                }}>{pendingOrders}</span>
              )}
            </div>
            <div style={{ fontSize: '0.85rem' }}>Orders</div>
          </div>
        </div>

        {/* Tab Content */}
        <div style={{
          backgroundColor: 'var(--bg-color)',
          borderRadius: '0.5rem',
          padding: '1rem',
          minHeight: '300px'
        }}>
          {activeTab === 'positions' && renderPositions()}
          {activeTab === 'holdings' && renderHoldings()}
          {activeTab === 'orders' && renderOrders()}
        </div>
      </div>
    )
  }

  return (
    <div>
      {/* Header */}
      <div style={{ marginBottom: '2rem' }}>
        <h1 style={{ marginBottom: '0.5rem' }}>Multi-Broker Configuration</h1>
        <p style={{ color: 'var(--text-secondary)', margin: 0 }}>Connect multiple broker accounts and manage your portfolio</p>
      </div>

      {/* Messages */}
      {success && (
        <div style={{ padding: '1rem', marginBottom: '1.5rem', backgroundColor: 'rgba(16, 185, 129, 0.1)', border: '1px solid var(--success-color)', borderRadius: '0.5rem' }}>
          <span style={{ color: 'var(--success-color)' }}>✓ {success}</span>
        </div>
      )}
      {error && (
        <div style={{ padding: '1rem', marginBottom: '1.5rem', backgroundColor: 'rgba(239, 68, 68, 0.1)', border: '1px solid var(--danger-color)', borderRadius: '0.5rem' }}>
          <span style={{ color: 'var(--danger-color)' }}>⚠️ {error}</span>
        </div>
      )}

      <div className="grid grid-2">
        {/* Add Broker Panel */}
        <div className="card">
          <h2 style={{ marginBottom: '1.5rem' }}>Add/Update Broker</h2>

          {/* Broker Selection Cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(100px, 1fr))', gap: '0.75rem', marginBottom: '1.5rem' }}>
            {availableBrokers.map(broker => {
              const cfg = BROKER_CONFIGS[broker]
              return (
                <div
                  key={broker}
                  onClick={() => setSelectedBroker(broker)}
                  style={{
                    padding: '1rem',
                    borderRadius: '0.5rem',
                    border: selectedBroker === broker ? `2px solid ${cfg?.color || 'var(--primary-color)'}` : '1px solid var(--border-color)',
                    backgroundColor: selectedBroker === broker ? `${cfg?.color}10` : 'var(--bg-color)',
                    cursor: 'pointer',
                    textAlign: 'center',
                    transition: 'all 0.2s'
                  }}
                >
                  <div style={{ fontSize: '1.5rem', marginBottom: '0.25rem' }}>{cfg?.icon || '🏦'}</div>
                  <div style={{ fontSize: '0.85rem', fontWeight: selectedBroker === broker ? 'bold' : 'normal' }}>
                    {cfg?.name || broker}
                  </div>
                </div>
              )
            })}
          </div>

          {/* Configuration Form */}
          <form onSubmit={handleConfigSubmit}>
            {brokerConfig.loginNote && (
              <div style={{
                padding: '0.75rem',
                borderRadius: '0.5rem',
                backgroundColor: '#fef3c7',
                border: '1px solid #fbbf24',
                color: '#92400e',
                fontSize: '0.85rem',
                marginBottom: '1rem',
                lineHeight: '1.5'
              }}>
                {brokerConfig.loginNote}
              </div>
            )}
            {brokerConfig.fields.map(field => (
              <div key={field.key} className="form-group">
                <label>{field.label} {field.required && <span style={{ color: 'var(--danger-color)' }}>*</span>}</label>
                <input
                  type={field.type}
                  value={config[field.key] || ''}
                  onChange={e => setConfig({ ...config, [field.key]: e.target.value })}
                  required={field.required}
                  maxLength={field.maxLength}
                  placeholder={field.help}
                />
              </div>
            ))}
            <button type="submit" className="btn btn-primary" disabled={loading} style={{ width: '100%' }}>
              {loading ? 'Saving...' : `💾 Save ${brokerConfig.name} Config`}
            </button>
          </form>
        </div>

        {/* Configured Brokers Panel */}
        <div className="card">
          <h2 style={{ marginBottom: '1.5rem' }}>Configured Brokers</h2>

          {configuredBrokers.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-secondary)' }}>
              <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>🏦</div>
              <p>No brokers configured yet</p>
              <p style={{ fontSize: '0.9rem' }}>Add your first broker using the form</p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {configuredBrokers.map(broker => {
                const cfg = BROKER_CONFIGS[broker.broker_type]
                const isActive = activeBroker === broker.broker_type
                const isConnecting = connectingBroker === broker.broker_type

                return (
                  <div
                    key={broker.id}
                    style={{
                      padding: '1.25rem',
                      borderRadius: '0.75rem',
                      border: isActive ? `2px solid ${cfg?.color || 'var(--primary-color)'}` : '1px solid var(--border-color)',
                      backgroundColor: isActive ? `${cfg?.color}08` : 'var(--bg-color)'
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                        <div style={{
                          width: '45px', height: '45px', borderRadius: '50%',
                          display: 'flex', alignItems: 'center', justifyContent: 'center',
                          backgroundColor: cfg?.color + '20' || 'var(--primary-color-light)',
                          fontSize: '1.5rem'
                        }}>
                          {cfg?.icon || '🏦'}
                        </div>
                        <div>
                          <h3 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            {cfg?.name || broker.broker_type}
                            {isActive && (
                              <span style={{
                                fontSize: '0.7rem', padding: '0.2rem 0.5rem', borderRadius: '1rem',
                                backgroundColor: 'var(--primary-color)', color: 'white'
                              }}>ACTIVE</span>
                            )}
                          </h3>
                          <p style={{ margin: '0.25rem 0 0', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                            Client: {broker.client_id}
                          </p>
                        </div>
                      </div>

                      {/* Status Indicator */}
                      <div style={{
                        width: '12px', height: '12px', borderRadius: '50%',
                        backgroundColor: broker.is_logged_in ? 'var(--success-color)' : 'var(--danger-color)',
                        boxShadow: broker.is_logged_in ? '0 0 8px var(--success-color)' : 'none'
                      }}></div>
                    </div>

                    {/* Connection Status */}
                    <div style={{
                      padding: '0.5rem 0.75rem',
                      borderRadius: '0.5rem',
                      backgroundColor: broker.is_logged_in ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)',
                      marginBottom: '1rem',
                      fontSize: '0.85rem',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.5rem'
                    }}>
                      <span>{broker.is_logged_in ? '✓' : '✗'}</span>
                      <span style={{ color: broker.is_logged_in ? 'var(--success-color)' : 'var(--danger-color)' }}>
                        {broker.is_logged_in ? 'Connected' : 'Disconnected'}
                      </span>
                    </div>

                    {/* Actions */}
                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                      {!broker.is_logged_in ? (
                        <button
                          onClick={() => handleLogin(broker.broker_type)}
                          className="btn btn-success"
                          disabled={isConnecting}
                          style={{ flex: 1 }}
                        >
                          {isConnecting ? 'Connecting...' : '🔌 Connect'}
                        </button>
                      ) : (
                        <button
                          onClick={() => handleLogout(broker.broker_type)}
                          className="btn btn-danger"
                          style={{ flex: 1 }}
                        >
                          Disconnect
                        </button>
                      )}

                      {!isActive && (
                        <button
                          onClick={() => handleSetActive(broker.broker_type)}
                          className="btn"
                          style={{ flex: 1 }}
                        >
                          Set Active
                        </button>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>

      {/* Trading Dashboard */}
      {renderTradingDashboard()}

      <style>{`
        .grid-3 {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 1rem;
        }
        .grid-4 {
          display: grid;
          grid-template-columns: repeat(4, 1fr);
          gap: 1rem;
        }
        @media (max-width: 768px) {
          .grid-3, .grid-4 {
            grid-template-columns: repeat(2, 1fr);
          }
        }
        .table-container {
          overflow-x: auto;
        }
        .table-container table {
          width: 100%;
          border-collapse: collapse;
        }
        .table-container th, .table-container td {
          padding: 0.75rem;
          text-align: left;
          border-bottom: 1px solid var(--border-color);
        }
        .table-container th {
          font-weight: 600;
          color: var(--text-secondary);
          font-size: 0.85rem;
        }
        .table-container tr:hover {
          background-color: var(--card-bg);
        }
      `}</style>
    </div>
  )
}

export default MultiBrokerConfig
