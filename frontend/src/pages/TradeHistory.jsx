import { useState, useEffect } from 'react'
import axios from 'axios'

function TradeHistory() {
  const [trades, setTrades] = useState([])
  const [filterStatus, setFilterStatus] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchTrades()
  }, [filterStatus])

  const fetchTrades = async () => {
    setLoading(true)
    try {
      const url = filterStatus 
        ? `/api/trades?status=${filterStatus}&limit=100`
        : '/api/trades?limit=100'
      const response = await axios.get(url)
      setTrades(response.data)
    } catch (error) {
      console.error('Error fetching trades:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleApprove = async (tradeId, approved) => {
    try {
      await axios.post('/api/trades/approve', {
        trade_id: tradeId,
        approved: approved
      })
      alert(approved ? 'Trade approved and executed!' : 'Trade rejected')
      fetchTrades()
    } catch (error) {
      alert('Error: ' + (error.response?.data?.detail || error.message))
    }
  }

  const handleExecute = async (tradeId) => {
    try {
      await axios.post(`/api/trades/${tradeId}/execute`)
      alert('Trade executed successfully!')
      fetchTrades()
    } catch (error) {
      alert('Execution failed: ' + (error.response?.data?.detail || error.message))
    }
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
        <h1>Trade History</h1>
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
          <label>Filter:</label>
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            style={{ padding: '0.5rem', borderRadius: '0.5rem', backgroundColor: 'var(--card-bg)', color: 'var(--text-color)', border: '1px solid var(--border-color)' }}
          >
            <option value="">All</option>
            <option value="PENDING">Pending</option>
            <option value="EXECUTED">Executed</option>
            <option value="FAILED">Failed</option>
            <option value="REJECTED">Rejected</option>
          </select>
          <button onClick={fetchTrades} className="btn btn-primary">Refresh</button>
        </div>
      </div>

      <div className="card">
        {loading ? (
          <p>Loading trades...</p>
        ) : trades.length === 0 ? (
          <p style={{ color: 'var(--text-secondary)' }}>No trades found</p>
        ) : (
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Symbol</th>
                  <th>Action</th>
                  <th>Qty</th>
                  <th>Entry Price</th>
                  <th>Target</th>
                  <th>Stop Loss</th>
                  <th>Status</th>
                  <th>Order ID</th>
                  <th>Created</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {trades.map((trade) => (
                  <tr key={trade.id}>
                    <td>{trade.id}</td>
                    <td><strong>{trade.symbol}</strong></td>
                    <td>
                      <span style={{ 
                        color: trade.action === 'BUY' ? 'var(--secondary-color)' : 'var(--danger-color)',
                        fontWeight: 'bold'
                      }}>
                        {trade.action}
                      </span>
                    </td>
                    <td>{trade.quantity}</td>
                    <td>{trade.entry_price || '-'}</td>
                    <td>{trade.target_price || '-'}</td>
                    <td>{trade.stop_loss || '-'}</td>
                    <td>
                      <span className={`badge badge-${
                        trade.status === 'EXECUTED' ? 'success' :
                        trade.status === 'PENDING' ? 'pending' : 'danger'
                      }`}>
                        {trade.status}
                      </span>
                    </td>
                    <td>
                      {trade.order_id ? (
                        <small style={{ fontFamily: 'monospace' }}>{trade.order_id}</small>
                      ) : '-'}
                    </td>
                    <td>
                      <small>{new Date(trade.created_at).toLocaleString()}</small>
                    </td>
                    <td>
                      {trade.status === 'PENDING' && (
                        <div style={{ display: 'flex', gap: '0.5rem' }}>
                          <button
                            onClick={() => handleApprove(trade.id, true)}
                            className="btn btn-success"
                            style={{ padding: '0.25rem 0.75rem', fontSize: '0.875rem' }}
                          >
                            ✓
                          </button>
                          <button
                            onClick={() => handleApprove(trade.id, false)}
                            className="btn btn-danger"
                            style={{ padding: '0.25rem 0.75rem', fontSize: '0.875rem' }}
                          >
                            ✗
                          </button>
                        </div>
                      )}
                      {trade.status === 'FAILED' && (
                        <button
                          onClick={() => handleExecute(trade.id)}
                          className="btn btn-primary"
                          style={{ padding: '0.25rem 0.75rem', fontSize: '0.875rem' }}
                        >
                          Retry
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {trades.some(t => t.error_message) && (
        <div className="card" style={{ marginTop: '2rem' }}>
          <h2>Error Messages</h2>
          {trades.filter(t => t.error_message).map(trade => (
            <div key={trade.id} style={{ padding: '0.5rem', marginBottom: '0.5rem', backgroundColor: 'var(--bg-color)', borderRadius: '0.25rem' }}>
              <strong>Trade #{trade.id} ({trade.symbol}):</strong> {trade.error_message}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default TradeHistory
