import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import api from '../lib/api'

function Dashboard({ telegramStatus, brokerStatus, wsConnected }) {
  const [stats, setStats] = useState({ total: 0, executed: 0, pending: 0, failed: 0, today: 0, limit: 10, remaining: 10 })
  const [recentTrades, setRecentTrades] = useState([])
  const [messageStats, setMessageStats] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 10000) // Refresh every 10 seconds
    return () => clearInterval(interval)
  }, [])

  const fetchData = async () => {
    try {
      const [statsRes, tradesRes, msgStatsRes] = await Promise.all([
        api.get('/trades/stats/summary'),
        api.get('/trades?limit=5'),
        api.get('/telegram/messages/stats').catch(() => ({ data: null }))
      ])

      setStats(statsRes.data)
      setRecentTrades(tradesRes.data)
      setMessageStats(msgStatsRes.data)
    } catch (error) {
      console.error('Error fetching data:', error)
    } finally {
      setLoading(false)
    }
  }


  // Determine setup steps status
  const setupSteps = [
    {
      id: 'telegram',
      title: 'Connect Telegram',
      description: 'Link your Telegram account to receive trading signals',
      status: telegramStatus?.is_connected ? 'complete' : telegramStatus?.error ? 'error' : 'pending',
      link: '/telegram',
      icon: '📱'
    },
    {
      id: 'channels',
      title: 'Select Channels',
      description: 'Choose which Telegram channels to monitor for signals',
      status: telegramStatus?.is_connected && telegramStatus?.monitored_chats_count > 0 ? 'complete' :
        telegramStatus?.is_connected ? 'action' : 'waiting',
      link: '/telegram',
      icon: '📡'
    },
    {
      id: 'broker',
      title: 'Connect Broker',
      description: 'Link your trading account to execute trades',
      status: brokerStatus?.is_logged_in ? 'complete' : 'pending',
      link: '/multi-broker',
      icon: '🏦'
    },
    {
      id: 'settings',
      title: 'Configure Settings',
      description: 'Set up trade limits, auto-trade, and preferences',
      status: 'optional',
      link: '/settings',
      icon: '⚙️'
    }
  ]

  const getStepBadge = (status) => {
    switch (status) {
      case 'complete':
        return <span className="badge badge-success">✓ Done</span>
      case 'error':
        return <span className="badge badge-danger">! Error</span>
      case 'action':
        return <span className="badge badge-warning">Action Needed</span>
      case 'waiting':
        return <span className="badge badge-secondary">Waiting</span>
      case 'optional':
        return <span className="badge badge-secondary">Optional</span>
      default:
        return <span className="badge badge-pending">Set Up</span>
    }
  }

  const isSetupComplete = setupSteps.filter(s => s.status === 'complete').length >= 3

  if (loading) {
    return (
      <div className="card" style={{ textAlign: 'center', padding: '3rem' }}>
        <div className="loading-spinner"></div>
        <p style={{ marginTop: '1rem', color: 'var(--text-secondary)' }}>Loading dashboard...</p>
      </div>
    )
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
        <h1>Dashboard</h1>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          {wsConnected ? (
            <span className="badge badge-success" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: 'currentColor', animation: 'pulse 2s infinite' }}></span>
              Live Updates
            </span>
          ) : (
            <span className="badge badge-danger">Offline</span>
          )}
        </div>
      </div>

      {/* Setup Wizard - Show if not fully configured */}
      {!isSetupComplete && (
        <div className="card" style={{ marginBottom: '2rem', borderLeft: '4px solid var(--primary-color)' }}>
          <h2 style={{ marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            🚀 Quick Setup
          </h2>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>
            Complete these steps to start receiving and executing trading signals automatically.
          </p>
          <div className="setup-steps">
            {setupSteps.map((step, index) => (
              <Link
                key={step.id}
                to={step.link}
                className={`setup-step ${step.status}`}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '1rem',
                  padding: '1rem',
                  marginBottom: '0.5rem',
                  backgroundColor: step.status === 'complete' ? 'rgba(16, 185, 129, 0.1)' :
                    step.status === 'error' ? 'rgba(239, 68, 68, 0.1)' :
                      step.status === 'action' ? 'rgba(245, 158, 11, 0.1)' :
                        'var(--bg-color)',
                  borderRadius: '0.5rem',
                  textDecoration: 'none',
                  color: 'inherit',
                  border: step.status === 'action' ? '1px solid var(--warning-color)' : '1px solid transparent',
                  transition: 'all 0.2s'
                }}
              >
                <div style={{
                  width: '40px',
                  height: '40px',
                  borderRadius: '50%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  backgroundColor: step.status === 'complete' ? 'var(--success-color)' : 'var(--card-bg)',
                  color: step.status === 'complete' ? 'white' : 'inherit',
                  fontSize: '1.2rem'
                }}>
                  {step.status === 'complete' ? '✓' : step.icon}
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 'bold', marginBottom: '0.25rem' }}>
                    {index + 1}. {step.title}
                  </div>
                  <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                    {step.description}
                  </div>
                </div>
                {getStepBadge(step.status)}
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* Connection Status Cards */}
      <div className="grid grid-3" style={{ marginBottom: '2rem' }}>
        {/* Telegram Status */}
        <div className="card status-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div>
              <h3 style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '0.5rem' }}>
                📱 Telegram
              </h3>
              <div style={{ fontSize: '1.5rem', fontWeight: 'bold', marginBottom: '0.5rem' }}>
                {telegramStatus?.is_connected ? (
                  <span style={{ color: 'var(--success-color)' }}>Connected</span>
                ) : (
                  <span style={{ color: 'var(--danger-color)' }}>Disconnected</span>
                )}
              </div>
            </div>
            <span className={`status-dot ${telegramStatus?.is_connected ? 'connected' : 'disconnected'}`}
              style={{ width: '12px', height: '12px' }}></span>
          </div>
          {telegramStatus?.is_connected ? (
            <div style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
              Monitoring <strong>{telegramStatus.monitored_chats_count}</strong> channels
              {telegramStatus.last_message_time && (
                <div style={{ marginTop: '0.25rem' }}>
                  Last: {new Date(telegramStatus.last_message_time).toLocaleTimeString()}
                </div>
              )}
            </div>
          ) : telegramStatus?.error ? (
            <div style={{ fontSize: '0.85rem', color: 'var(--danger-color)' }}>
              {telegramStatus.error}
            </div>
          ) : (
            <Link to="/telegram" className="btn btn-sm" style={{ marginTop: '0.5rem' }}>
              Set Up →
            </Link>
          )}
        </div>

        {/* Broker Status */}
        <div className="card status-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div>
              <h3 style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '0.5rem' }}>
                🏦 Broker
              </h3>
              <div style={{ fontSize: '1.5rem', fontWeight: 'bold', marginBottom: '0.5rem' }}>
                {brokerStatus?.is_logged_in ? (
                  <span style={{ color: 'var(--success-color)' }}>Connected</span>
                ) : (
                  <span style={{ color: 'var(--warning-color)' }}>Not Connected</span>
                )}
              </div>
            </div>
            <span className={`status-dot ${brokerStatus?.is_logged_in ? 'connected' : 'disconnected'}`}
              style={{ width: '12px', height: '12px' }}></span>
          </div>
          {brokerStatus?.is_logged_in ? (
            <div style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
              Client: {brokerStatus.client_id || 'Connected'}
            </div>
          ) : (
            <Link to="/multi-broker" className="btn btn-sm" style={{ marginTop: '0.5rem' }}>
              Connect →
            </Link>
          )}
        </div>

        {/* Today's Activity */}
        <div className="card status-card">
          <h3 style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '0.5rem' }}>
            📊 Today's Activity
          </h3>
          <div style={{ fontSize: '1.5rem', fontWeight: 'bold', marginBottom: '0.5rem' }}>
            {stats.today} / {stats.limit} <span style={{ fontSize: '0.9rem', fontWeight: 'normal' }}>trades</span>
          </div>
          <div style={{
            width: '100%',
            height: '6px',
            backgroundColor: 'var(--bg-color)',
            borderRadius: '3px',
            overflow: 'hidden',
            marginTop: '0.5rem'
          }}>
            <div style={{
              width: `${Math.min((stats.today / stats.limit) * 100, 100)}%`,
              height: '100%',
              backgroundColor: stats.remaining <= 2 ? 'var(--danger-color)' : 'var(--success-color)',
              transition: 'width 0.3s ease'
            }}></div>
          </div>
          <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '0.5rem' }}>
            {stats.remaining} trades remaining today
          </div>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="stats-grid" style={{ marginBottom: '2rem' }}>
        <div className="stat-card">
          <h3>{stats.total}</h3>
          <p>Total Trades</p>
        </div>
        <div className="stat-card">
          <h3 style={{ color: 'var(--success-color)' }}>{stats.executed}</h3>
          <p>Executed</p>
        </div>
        <div className="stat-card">
          <h3 style={{ color: 'var(--warning-color)' }}>{stats.pending}</h3>
          <p>Pending</p>
        </div>
        <div className="stat-card">
          <h3 style={{ color: 'var(--danger-color)' }}>{stats.failed}</h3>
          <p>Failed</p>
        </div>
        {messageStats && (
          <>
            <div className="stat-card">
              <h3>{messageStats.total_messages}</h3>
              <p>Messages</p>
            </div>
            <div className="stat-card">
              <h3 style={{ color: 'var(--primary-color)' }}>{messageStats.total_signals}</h3>
              <p>Signals</p>
            </div>
          </>
        )}
      </div>

      {/* Quick Actions */}
      <div className="card" style={{ marginBottom: '2rem' }}>
        <h2 style={{ marginBottom: '1rem' }}>⚡ Quick Actions</h2>
        <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
          <Link to="/telegram" className="btn btn-primary">
            📨 View Messages
          </Link>
          <Link to="/trades" className="btn">
            📋 Trade History
          </Link>
          <Link to="/signal-tester" className="btn">
            🧪 Test Signal Parser
          </Link>
          {messageStats?.unprocessed_signals > 0 && (
            <Link to="/telegram" className="btn" style={{ backgroundColor: 'var(--warning-color)', color: 'white' }}>
              ⚠️ {messageStats.unprocessed_signals} Pending Signals
            </Link>
          )}
        </div>
      </div>

      {/* Recent Trades */}
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <h2>Recent Trades</h2>
          <Link to="/trades" style={{ color: 'var(--primary-color)', textDecoration: 'none' }}>
            View All →
          </Link>
        </div>
        {recentTrades.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-secondary)' }}>
            <p style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>📭</p>
            <p>No trades yet. Signals from Telegram will appear here when executed.</p>
          </div>
        ) : (
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Symbol</th>
                  <th>Action</th>
                  <th>Qty</th>
                  <th>Status</th>
                  <th>Time</th>
                </tr>
              </thead>
              <tbody>
                {recentTrades.map((trade) => (
                  <tr key={trade.id}>
                    <td><strong>{trade.symbol}</strong></td>
                    <td>
                      <span style={{
                        color: trade.action === 'BUY' ? 'var(--success-color)' : 'var(--danger-color)',
                        fontWeight: 'bold'
                      }}>
                        {trade.action}
                      </span>
                    </td>
                    <td>{trade.quantity}</td>
                    <td>
                      <span className={`badge badge-${trade.status === 'EXECUTED' ? 'success' :
                          trade.status === 'PENDING' ? 'pending' : 'danger'
                        }`}>
                        {trade.status}
                      </span>
                    </td>
                    <td style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                      {new Date(trade.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <style>{`
        .grid-3 {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 1rem;
        }
        
        @media (max-width: 900px) {
          .grid-3 {
            grid-template-columns: 1fr;
          }
        }
        
        .status-card {
          min-height: 120px;
        }
        
        .btn-sm {
          padding: 0.4rem 0.8rem;
          font-size: 0.85rem;
        }
        
        .loading-spinner {
          width: 40px;
          height: 40px;
          border: 3px solid var(--border-color);
          border-top-color: var(--primary-color);
          border-radius: 50%;
          animation: spin 1s linear infinite;
          margin: 0 auto;
        }
        
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
        
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
        
        .setup-step:hover {
          transform: translateX(4px);
          background-color: var(--card-bg) !important;
        }
      `}</style>
    </div>
  )
}

export default Dashboard
