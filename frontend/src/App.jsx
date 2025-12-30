import { useState, useEffect, useRef, useCallback } from 'react'
import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import TelegramConfig from './pages/TelegramConfig'
import BrokerConfig from './pages/BrokerConfig'
import MultiBrokerConfig from './pages/MultiBrokerConfig'
import TradeHistory from './pages/TradeHistory'
import Settings from './pages/Settings'
import SignalTester from './pages/SignalTester'
import WebSocketManager from './lib/websocket'
import api from './lib/api'
import './App.css'

// Helper to get WebSocket URL
const getWebSocketUrl = () => {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.hostname
  const port = import.meta.env.VITE_API_PORT || '8000'
  // In development, use localhost:8000; in production, use same host
  if (host === 'localhost' || host === '127.0.0.1') {
    return `${protocol}//${host}:${port}/ws`
  }
  return `${protocol}//${window.location.host}/ws`
}

function NavLink({ to, children }) {
  const location = useLocation()
  const isActive = location.pathname === to

  return (
    <Link
      to={to}
      className={isActive ? 'active' : ''}
      style={{
        backgroundColor: isActive ? 'var(--primary-color)' : 'transparent',
        color: isActive ? 'white' : 'var(--text-color)'
      }}
    >
      {children}
    </Link>
  )
}

function App() {
  const [wsConnected, setWsConnected] = useState(false)
  const [telegramStatus, setTelegramStatus] = useState(null)
  const [brokerStatus, setBrokerStatus] = useState({ is_logged_in: false, client_id: null })
  const [notification, setNotification] = useState(null)
  const wsManager = useRef(null)

  // Fetch broker status from API
  const fetchBrokerStatus = useCallback(async () => {
    try {
      const response = await api.get('/broker/status')
      setBrokerStatus(response.data)
    } catch (error) {
      console.error('Error fetching broker status:', error)
      setBrokerStatus({ is_logged_in: false, client_id: null })
    }
  }, [])

  // Fetch telegram status from API (fallback if WebSocket doesn't update)
  const fetchTelegramStatus = useCallback(async () => {
    try {
      const response = await api.get('/telegram/status')
      setTelegramStatus(response.data)
    } catch (error) {
      console.error('Error fetching telegram status:', error)
    }
  }, [])

  useEffect(() => {
    // Initial fetch of statuses
    fetchTelegramStatus()
    fetchBrokerStatus()

    // Initialize WebSocket manager with dynamic URL
    wsManager.current = new WebSocketManager(getWebSocketUrl())

    // Set connection change handler
    wsManager.current.onConnectionChange = (isConnected) => {
      setWsConnected(isConnected)
      // Refresh statuses when reconnected
      if (isConnected) {
        fetchTelegramStatus()
        fetchBrokerStatus()
      }
    }

    // Subscribe to telegram status updates
    wsManager.current.on('telegram_status', (data) => {
      console.log('Telegram status update:', data)
      setTelegramStatus(data.data)
    })

    // Subscribe to broker status updates (if backend sends them)
    wsManager.current.on('broker_status', (data) => {
      console.log('Broker status update:', data)
      setBrokerStatus(data.data)
    })

    // Subscribe to important events
    wsManager.current.on('new_signal', (data) => {
      console.log('New signal received:', data)
      setNotification({
        type: 'signal',
        title: '📊 New Trading Signal',
        message: data.data?.message || `${data.data?.action} ${data.data?.symbol}`,
        data: data.data
      })
      setTimeout(() => setNotification(null), 8000)
    })

    wsManager.current.on('trade_executed', (data) => {
      console.log('Trade executed:', data)
      setNotification({
        type: 'trade',
        title: '✅ Trade Executed',
        message: data.data?.message || 'Trade completed successfully',
        data: data.data
      })
      // Refresh broker status after trade
      fetchBrokerStatus()
      setTimeout(() => setNotification(null), 8000)
    })

    wsManager.current.on('new_message', (data) => {
      console.log('New message:', data)
      if (data.data?.is_signal) {
        setNotification({
          type: 'signal',
          title: '📊 New Trading Signal',
          message: `${data.data.parsed_signal?.action || 'Signal'} for ${data.data.parsed_signal?.symbol || 'Unknown'} from ${data.data.chat_name}`,
          data: data.data
        })
        setTimeout(() => setNotification(null), 8000)
      }
    })

    // WebSocket connects automatically in constructor
    // No need to call connect() manually

    // Periodic status refresh every 30 seconds
    const statusInterval = setInterval(() => {
      fetchTelegramStatus()
      fetchBrokerStatus()
    }, 30000)

    return () => {
      clearInterval(statusInterval)
      if (wsManager.current) {
        wsManager.current.disconnect()
      }
    }
  }, [fetchTelegramStatus, fetchBrokerStatus])

  const dismissNotification = () => setNotification(null)

  // Callback for child components to update broker status
  const onBrokerStatusChange = useCallback((newStatus) => {
    setBrokerStatus(newStatus)
  }, [])

  return (
    <Router>
      <div className="App">
        <nav className="navbar">
          <div className="nav-brand">
            <h1>📊 Telegram Trading Bot</h1>
          </div>
          <ul className="nav-links">
            <li><NavLink to="/">Dashboard</NavLink></li>
            <li><NavLink to="/telegram">Telegram</NavLink></li>
            <li><NavLink to="/multi-broker">Brokers</NavLink></li>
            <li><NavLink to="/signal-tester">Signal Tester</NavLink></li>
            <li><NavLink to="/trades">Trades</NavLink></li>
            <li><NavLink to="/settings">Settings</NavLink></li>
          </ul>
          <div className="nav-status">
            {/* Broker Status Indicator */}
            <div className="status-indicator broker-status" title={brokerStatus.is_logged_in ? `Connected: ${brokerStatus.client_id}` : 'Broker disconnected'}>
              <span className={`status-dot ${brokerStatus.is_logged_in ? 'connected' : 'disconnected'}`}></span>
              <span className="status-label">
                {brokerStatus.is_logged_in
                  ? `🏦 ${brokerStatus.client_id || 'Connected'}`
                  : '🏦 Disconnected'}
              </span>
            </div>
            {/* Telegram Status Indicator */}
            {telegramStatus && (
              <div className="status-indicator telegram-status" title={telegramStatus.error || 'Telegram status'}>
                <span className={`status-dot ${telegramStatus.is_connected ? 'connected' : 'disconnected'}`}></span>
                <span className="status-label">
                  {telegramStatus.is_connected
                    ? `📱 ${telegramStatus.monitored_chats_count} channels`
                    : '📱 Disconnected'}
                </span>
              </div>
            )}
            {/* WebSocket Status */}
            <div className="status-indicator" title="WebSocket connection to backend">
              <span className={`status-dot ${wsConnected ? 'connected' : 'disconnected'}`}></span>
              <span className="status-label">{wsConnected ? 'Live' : 'Offline'}</span>
            </div>
          </div>
        </nav>

        {notification && (
          <div className={`notification notification-${notification.type}`} onClick={dismissNotification}>
            <div className="notification-content">
              <strong>{notification.title}</strong>
              <p>{notification.message}</p>
            </div>
            <button className="notification-close">×</button>
          </div>
        )}

        <div className="main-content">
          <Routes>
            <Route path="/" element={<Dashboard telegramStatus={telegramStatus} brokerStatus={brokerStatus} wsConnected={wsConnected} />} />
            <Route path="/telegram" element={<TelegramConfig />} />
            <Route path="/broker" element={<BrokerConfig />} />
            <Route path="/multi-broker" element={<MultiBrokerConfig brokerStatus={brokerStatus} onBrokerStatusChange={onBrokerStatusChange} />} />
            <Route path="/signal-tester" element={<SignalTester />} />
            <Route path="/trades" element={<TradeHistory />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </div>
      </div>
    </Router>
  )
}

export default App

