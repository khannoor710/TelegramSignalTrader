import { useState, useEffect, useCallback } from 'react'
import api from '../lib/api'

function TradeHistory() {
  const [trades, setTrades] = useState([])
  const [filterStatus, setFilterStatus] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [actionLoading, setActionLoading] = useState({})
  const [stats, setStats] = useState({ total: 0, pending: 0, executed: 0, failed: 0 })
  const [selectedTrades, setSelectedTrades] = useState([])

  const fetchTrades = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const url = filterStatus 
        ? `/trades?status=${filterStatus}&limit=100`
        : '/trades?limit=100'
      const response = await api.get(url)
      const tradesData = response.data || []
      setTrades(tradesData)
      
      setStats({
        total: tradesData.length,
        pending: tradesData.filter(t => t.status === 'PENDING').length,
        executed: tradesData.filter(t => t.status === 'EXECUTED').length,
        failed: tradesData.filter(t => t.status === 'FAILED').length
      })
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load trades')
    } finally {
      setLoading(false)
    }
  }, [filterStatus])

  useEffect(() => {
    fetchTrades()
  }, [fetchTrades])

  const handleApprove = async (tradeId, approved) => {
    setActionLoading(prev => ({ ...prev, [tradeId]: true }))
    try {
      await api.post('/trades/approve', { trade_id: tradeId, approved })
      fetchTrades()
    } catch (err) {
      alert('Error: ' + (err.response?.data?.detail || err.message))
    } finally {
      setActionLoading(prev => ({ ...prev, [tradeId]: false }))
    }
  }

  const handleExecute = async (tradeId) => {
    setActionLoading(prev => ({ ...prev, [tradeId]: true }))
    try {
      await api.post(`/trades/${tradeId}/execute`)
      fetchTrades()
    } catch (err) {
      alert('Execution failed: ' + (err.response?.data?.detail || err.message))
    } finally {
      setActionLoading(prev => ({ ...prev, [tradeId]: false }))
    }
  }

  const handleBulkAction = async (action) => {
    if (selectedTrades.length === 0) return
    if (!confirm(`${action === 'approve' ? 'Approve' : 'Reject'} ${selectedTrades.length} trades?`)) return
    
    for (const tradeId of selectedTrades) {
      await handleApprove(tradeId, action === 'approve')
    }
    setSelectedTrades([])
  }

  const toggleSelect = (id) => {
    setSelectedTrades(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id])
  }

  const selectAllPending = () => {
    setSelectedTrades(trades.filter(t => t.status === 'PENDING').map(t => t.id))
  }

  const fmt = (v) => v ? `₹${parseFloat(v).toFixed(2)}` : '-'
  const fmtDate = (d) => new Date(d).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })

  const pendingTrades = trades.filter(t => t.status === 'PENDING')

  return (
    <div>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h1 style={{ marginBottom: '0.5rem' }}>Trade History</h1>
          <p style={{ color: 'var(--text-secondary)', margin: 0 }}>Manage trading signals and executions</p>
        </div>
        <button onClick={fetchTrades} className="btn btn-primary" disabled={loading}>
          {loading ? '↻ Loading...' : '↻ Refresh'}
        </button>
      </div>

      {/* Stats Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '1rem', marginBottom: '1.5rem' }}>
        {[
          { label: 'Total', value: stats.total, color: 'var(--primary-color)', filter: '' },
          { label: 'Pending', value: stats.pending, color: 'var(--warning-color)', filter: 'PENDING' },
          { label: 'Executed', value: stats.executed, color: 'var(--success-color)', filter: 'EXECUTED' },
          { label: 'Failed', value: stats.failed, color: 'var(--danger-color)', filter: 'FAILED' }
        ].map(s => (
          <div 
            key={s.label}
            className="card" 
            onClick={() => setFilterStatus(s.filter)}
            style={{ 
              padding: '1rem', 
              textAlign: 'center', 
              cursor: 'pointer',
              border: filterStatus === s.filter ? `2px solid ${s.color}` : undefined,
              transition: 'all 0.2s'
            }}
          >
            <div style={{ fontSize: '2rem', fontWeight: 'bold', color: s.color }}>{s.value}</div>
            <div style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>{s.label}</div>
          </div>
        ))}
      </div>

      {/* Bulk Actions */}
      {pendingTrades.length > 0 && (
        <div className="card" style={{ marginBottom: '1.5rem', padding: '1rem', backgroundColor: 'rgba(251, 191, 36, 0.05)', border: '1px solid rgba(251, 191, 36, 0.3)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
            <div>
              <strong>⏳ {pendingTrades.length} trades awaiting approval</strong>
              {selectedTrades.length > 0 && <span style={{ marginLeft: '0.5rem', color: 'var(--primary-color)' }}>({selectedTrades.length} selected)</span>}
            </div>
            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
              <button onClick={selectAllPending} className="btn" style={{ fontSize: '0.85rem' }}>Select All</button>
              {selectedTrades.length > 0 && (
                <>
                  <button onClick={() => handleBulkAction('approve')} className="btn btn-success" style={{ fontSize: '0.85rem' }}>✓ Approve</button>
                  <button onClick={() => handleBulkAction('reject')} className="btn btn-danger" style={{ fontSize: '0.85rem' }}>✗ Reject</button>
                  <button onClick={() => setSelectedTrades([])} className="btn" style={{ fontSize: '0.85rem' }}>Clear</button>
                </>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Main Table */}
      <div className="card">
        {/* Filter Tabs */}
        <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem', paddingBottom: '1rem', borderBottom: '1px solid var(--border-color)', flexWrap: 'wrap' }}>
          {['', 'PENDING', 'EXECUTED', 'FAILED', 'REJECTED'].map(status => (
            <button key={status} onClick={() => setFilterStatus(status)} className={filterStatus === status ? 'btn btn-primary' : 'btn'} style={{ fontSize: '0.85rem', padding: '0.4rem 0.75rem' }}>
              {status || 'All'}
            </button>
          ))}
        </div>

        {/* Error */}
        {error && (
          <div style={{ padding: '2rem', textAlign: 'center', backgroundColor: 'rgba(239, 68, 68, 0.1)', borderRadius: '0.5rem', marginBottom: '1rem' }}>
            <p style={{ color: 'var(--danger-color)', marginBottom: '1rem' }}>⚠️ {error}</p>
            <button onClick={fetchTrades} className="btn btn-primary">Try Again</button>
          </div>
        )}

        {/* Loading */}
        {loading && !error && (
          <div style={{ padding: '3rem', textAlign: 'center' }}>
            <div className="loading-spinner" style={{ margin: '0 auto 1rem' }}></div>
            <p style={{ color: 'var(--text-secondary)' }}>Loading trades...</p>
          </div>
        )}

        {/* Empty */}
        {!loading && !error && trades.length === 0 && (
          <div style={{ padding: '3rem', textAlign: 'center' }}>
            <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>📊</div>
            <h3>No trades yet</h3>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>Connect Telegram channels or test signals to get started</p>
            <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center' }}>
              <a href="/telegram" className="btn btn-primary">Configure Telegram</a>
              <a href="/signal-tester" className="btn">Test Signals</a>
            </div>
          </div>
        )}

        {/* Table */}
        {!loading && !error && trades.length > 0 && (
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  {pendingTrades.length > 0 && <th style={{ width: '40px' }}></th>}
                  <th>ID</th>
                  <th>Symbol</th>
                  <th>Action</th>
                  <th>Qty</th>
                  <th>Entry</th>
                  <th>Target</th>
                  <th>SL</th>
                  <th>Status</th>
                  <th>Time</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {trades.map(trade => (
                  <tr key={trade.id} style={{ backgroundColor: selectedTrades.includes(trade.id) ? 'rgba(59, 130, 246, 0.1)' : undefined }}>
                    {pendingTrades.length > 0 && (
                      <td>
                        {trade.status === 'PENDING' && (
                          <input type="checkbox" checked={selectedTrades.includes(trade.id)} onChange={() => toggleSelect(trade.id)} />
                        )}
                      </td>
                    )}
                    <td style={{ fontFamily: 'monospace', fontSize: '0.85rem' }}>#{trade.id}</td>
                    <td><strong>{trade.symbol}</strong></td>
                    <td>
                      <span style={{ 
                        color: trade.action === 'BUY' ? 'var(--success-color)' : 'var(--danger-color)',
                        fontWeight: 'bold',
                        padding: '0.2rem 0.5rem',
                        borderRadius: '0.25rem',
                        backgroundColor: trade.action === 'BUY' ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)'
                      }}>
                        {trade.action}
                      </span>
                    </td>
                    <td>{trade.quantity}</td>
                    <td>{fmt(trade.entry_price)}</td>
                    <td style={{ color: 'var(--success-color)' }}>{fmt(trade.target_price)}</td>
                    <td style={{ color: 'var(--danger-color)' }}>{fmt(trade.stop_loss)}</td>
                    <td>
                      <span className={`badge badge-${trade.status === 'EXECUTED' ? 'success' : trade.status === 'PENDING' ? 'pending' : 'danger'}`}>
                        {trade.status}
                      </span>
                    </td>
                    <td style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>{fmtDate(trade.created_at)}</td>
                    <td>
                      {trade.status === 'PENDING' && (
                        <div style={{ display: 'flex', gap: '0.25rem' }}>
                          <button onClick={() => handleApprove(trade.id, true)} className="btn btn-success" disabled={actionLoading[trade.id]} style={{ padding: '0.25rem 0.5rem', fontSize: '0.8rem' }}>
                            {actionLoading[trade.id] ? '...' : '✓'}
                          </button>
                          <button onClick={() => handleApprove(trade.id, false)} className="btn btn-danger" disabled={actionLoading[trade.id]} style={{ padding: '0.25rem 0.5rem', fontSize: '0.8rem' }}>✗</button>
                        </div>
                      )}
                      {trade.status === 'FAILED' && (
                        <button onClick={() => handleExecute(trade.id)} className="btn btn-primary" disabled={actionLoading[trade.id]} style={{ padding: '0.25rem 0.5rem', fontSize: '0.8rem' }}>
                          {actionLoading[trade.id] ? '...' : '↻ Retry'}
                        </button>
                      )}
                      {trade.order_id && <span style={{ fontFamily: 'monospace', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>{trade.order_id}</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Error Messages */}
      {trades.some(t => t.error_message) && (
        <div className="card" style={{ marginTop: '1.5rem' }}>
          <h3 style={{ color: 'var(--danger-color)', marginBottom: '1rem' }}>⚠️ Error Details</h3>
          {trades.filter(t => t.error_message).map(trade => (
            <div key={trade.id} style={{ padding: '0.75rem', backgroundColor: 'rgba(239, 68, 68, 0.05)', borderRadius: '0.5rem', borderLeft: '3px solid var(--danger-color)', marginBottom: '0.5rem' }}>
              <strong>Trade #{trade.id} - {trade.symbol}:</strong> {trade.error_message}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default TradeHistory
