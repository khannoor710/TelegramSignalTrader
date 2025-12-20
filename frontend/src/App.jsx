import { useState, useEffect, useRef } from 'react'
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import TelegramConfig from './pages/TelegramConfig'
import BrokerConfig from './pages/BrokerConfig'
import MultiBrokerConfig from './pages/MultiBrokerConfig'
import TradeHistory from './pages/TradeHistory'
import Settings from './pages/Settings'
import SignalTester from './pages/SignalTester'
import WebSocketManager from './lib/websocket'
import './App.css'

function App() {
  const [wsConnected, setWsConnected] = useState(false)
  const [notification, setNotification] = useState(null)
  const wsManager = useRef(null)

  useEffect(() => {
    // Initialize WebSocket manager with auto-reconnect
    wsManager.current = new WebSocketManager('ws://localhost:8000/ws')
    
    // Set connection change handler
    wsManager.current.onConnectionChange = (isConnected) => {
      setWsConnected(isConnected)
    }
    
    // Subscribe to important events
    wsManager.current.on('new_signal', (data) => {
      console.log('New signal received:', data)
      setNotification(data)
      setTimeout(() => setNotification(null), 5000)
    })
    
    wsManager.current.on('trade_executed', (data) => {
      console.log('Trade executed:', data)
      setNotification(data)
      setTimeout(() => setNotification(null), 5000)
    })
    
    wsManager.current.on('new_message', (data) => {
      console.log('New message:', data)
      if (data.data?.is_signal) {
        setNotification({ type: 'new_signal', data: data.data })
        setTimeout(() => setNotification(null), 5000)
      }
    })
    
    // Connect
    wsManager.current.connect().catch(console.error)
    
    return () => {
      if (wsManager.current) {
        wsManager.current.disconnect()
      }
    }
  }, [])

  return (
    <Router>
      <div className="App">
        <nav className="navbar">
          <div className="nav-brand">
            <h1>📊 Telegram Trading Bot</h1>
          </div>
          <ul className="nav-links">
            <li><Link to="/">Dashboard</Link></li>
            <li><Link to="/telegram">Telegram</Link></li>
            <li><Link to="/broker">Broker (Legacy)</Link></li>
            <li><Link to="/multi-broker">Multi-Broker</Link></li>
            <li><Link to="/signal-tester">Signal Tester</Link></li>
            <li><Link to="/trades">Trades</Link></li>
            <li><Link to="/settings">Settings</Link></li>
          </ul>
          <div className="nav-status">
            <span className={`status-dot ${wsConnected ? 'connected' : 'disconnected'}`}></span>
            <span>{wsConnected ? 'Connected' : 'Disconnected'}</span>
          </div>
        </nav>

        {notification && (
          <div className="notification">
            <strong>{notification.type}</strong>
            <p>{JSON.stringify(notification.data)}</p>
          </div>
        )}

        <div className="main-content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/telegram" element={<TelegramConfig />} />
            <Route path="/broker" element={<BrokerConfig />} />
            <Route path="/multi-broker" element={<MultiBrokerConfig />} />
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
