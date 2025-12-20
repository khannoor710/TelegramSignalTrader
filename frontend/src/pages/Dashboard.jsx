import { useState, useEffect } from 'react'
import api from '../lib/api'

function Dashboard() {
  const [stats, setStats] = useState({ total: 0, executed: 0, pending: 0, failed: 0, today: 0, limit: 10, remaining: 10 })
  const [recentTrades, setRecentTrades] = useState([])
  const [brokerStatus, setBrokerStatus] = useState({ is_logged_in: false })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 5000) // Refresh every 5 seconds
    return () => clearInterval(interval)
  }, [])

  const fetchData = async () => {
    try {
      const [statsRes, tradesRes, brokerRes] = await Promise.all([
        api.get('/trades/stats/summary'),
        api.get('/trades?limit=10'),
        api.get('/broker/status')
      ])
      
      setStats(statsRes.data)
      setRecentTrades(tradesRes.data)
      setBrokerStatus(brokerRes.data)
    } catch (error) {
      console.error('Error fetching data:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return <div className="card"><p>Loading dashboard...</p></div>
  }

  return (
    <div>
      <h1 style={{ marginBottom: '2rem' }}>Dashboard</h1>

      {/* Stats Cards */}
      <div className="stats-grid">
        <div className="stat-card">
          <h3>{stats.total}</h3>
          <p>Total Trades</p>
        </div>
        <div className="stat-card">
          <h3 style={{ color: 'var(--secondary-color)' }}>{stats.executed}</h3>
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
      </div>

      {/* Daily Limit Progress */}
      <div className="card" style={{ marginBottom: '2rem' }}>
        <h2>Today's Trading Activity</h2>
        <div style={{ marginTop: '1rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
            <span>Trades Today: {stats.today} / {stats.limit}</span>
            <span style={{ color: stats.remaining <= 2 ? 'var(--danger-color)' : 'var(--text-secondary)' }}>
              {stats.remaining} remaining
            </span>
          </div>
          <div style={{ 
            width: '100%', 
            height: '8px', 
            backgroundColor: 'var(--bg-color)', 
            borderRadius: '4px',
            overflow: 'hidden'
          }}>
            <div style={{ 
              width: `${(stats.today / stats.limit) * 100}%`, 
              height: '100%', 
              backgroundColor: stats.remaining <= 2 ? 'var(--danger-color)' : 'var(--secondary-color)',
              transition: 'width 0.3s ease'
            }}></div>
          </div>
        </div>
      </div>

      {/* Status Cards */}
      <div className="grid grid-2" style={{ marginBottom: '2rem' }}>
        <div className="card">
          <h2>Broker Status</h2>
          <div style={{ marginTop: '1rem' }}>
            <p>Status: <span className={`badge ${brokerStatus.is_logged_in ? 'badge-success' : 'badge-danger'}`}>
              {brokerStatus.is_logged_in ? 'Connected' : 'Disconnected'}
            </span></p>
            {brokerStatus.client_id && (
              <p style={{ marginTop: '0.5rem' }}>Client ID: {brokerStatus.client_id}</p>
            )}
          </div>
        </div>

        <div className="card">
          <h2>System Status</h2>
          <div style={{ marginTop: '1rem' }}>
            <p>WebSocket: <span className="badge badge-success">Connected</span></p>
            <p style={{ marginTop: '0.5rem' }}>Backend: <span className="badge badge-success">Running</span></p>
          </div>
        </div>
      </div>

      {/* Recent Trades */}
      <div className="card">
        <h2>Recent Trades</h2>
        {recentTrades.length === 0 ? (
          <p style={{ marginTop: '1rem', color: 'var(--text-secondary)' }}>No trades yet</p>
        ) : (
          <div className="table-container" style={{ marginTop: '1rem' }}>
            <table>
              <thead>
                <tr>
                  <th>Symbol</th>
                  <th>Action</th>
                  <th>Quantity</th>
                  <th>Price</th>
                  <th>Status</th>
                  <th>Time</th>
                </tr>
              </thead>
              <tbody>
                {recentTrades.map((trade) => (
                  <tr key={trade.id}>
                    <td><strong>{trade.symbol}</strong></td>
                    <td>
                      <span style={{ color: trade.action === 'BUY' ? 'var(--secondary-color)' : 'var(--danger-color)' }}>
                        {trade.action}
                      </span>
                    </td>
                    <td>{trade.quantity}</td>
                    <td>{trade.entry_price || '-'}</td>
                    <td>
                      <span className={`badge badge-${
                        trade.status === 'EXECUTED' ? 'success' :
                        trade.status === 'PENDING' ? 'pending' : 'danger'
                      }`}>
                        {trade.status}
                      </span>
                    </td>
                    <td>{new Date(trade.created_at).toLocaleString()}</td>
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

export default Dashboard
