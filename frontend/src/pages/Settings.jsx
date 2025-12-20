import { useState, useEffect } from 'react'
import axios from 'axios'

function Settings() {
  const [settings, setSettings] = useState({
    auto_trade_enabled: false,
    require_manual_approval: true,
    default_quantity: 1,
    max_trades_per_day: 10,
    risk_percentage: 1.0,
    paper_trading_enabled: true,
    paper_trading_balance: 100000
  })
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    fetchSettings()
  }, [])

  const fetchSettings = async () => {
    try {
      const response = await axios.get('/api/config/settings')
      setSettings(response.data)
    } catch (error) {
      console.error('Error fetching settings:', error)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)

    try {
      await axios.post('/api/config/settings', settings)
      alert('Settings saved successfully!')
    } catch (error) {
      alert('Error saving settings: ' + (error.response?.data?.detail || error.message))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h1 style={{ marginBottom: '2rem' }}>Settings</h1>

      <div className="grid grid-2">
        <div className="card">
          <h2>Trading Settings</h2>
          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <input
                  type="checkbox"
                  checked={settings.paper_trading_enabled}
                  onChange={(e) => setSettings({ ...settings, paper_trading_enabled: e.target.checked })}
                  style={{ width: 'auto' }}
                />
                Paper Trading Mode
              </label>
              <small style={{ color: 'var(--text-secondary)', display: 'block', marginTop: '0.25rem' }}>
                Practice with virtual money before going live
              </small>
            </div>

            <div className="form-group">
              <label>Paper Trading Balance (Rs)</label>
              <input
                type="number"
                min="1000"
                step="1000"
                value={settings.paper_trading_balance}
                onChange={(e) => setSettings({ ...settings, paper_trading_balance: parseFloat(e.target.value) })}
              />
              <small style={{ color: 'var(--text-secondary)', display: 'block', marginTop: '0.25rem' }}>
                Starting virtual balance for paper trading
              </small>
            </div>

            <hr style={{ margin: '1.5rem 0', borderColor: 'var(--border-color)' }} />

            <div className="form-group">
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <input
                  type="checkbox"
                  checked={settings.auto_trade_enabled}
                  onChange={(e) => setSettings({ ...settings, auto_trade_enabled: e.target.checked })}
                  style={{ width: 'auto' }}
                />
                Enable Auto Trading
              </label>
              <small style={{ color: 'var(--text-secondary)', display: 'block', marginTop: '0.25rem' }}>
                Automatically execute trades from parsed signals
              </small>
            </div>

            <div className="form-group">
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <input
                  type="checkbox"
                  checked={settings.require_manual_approval}
                  onChange={(e) => setSettings({ ...settings, require_manual_approval: e.target.checked })}
                  style={{ width: 'auto' }}
                />
                Require Manual Approval
              </label>
              <small style={{ color: 'var(--text-secondary)', display: 'block', marginTop: '0.25rem' }}>
                All trades must be manually approved before execution
              </small>
            </div>

            <div className="form-group">
              <label>Default Quantity</label>
              <input
                type="number"
                min="1"
                value={settings.default_quantity}
                onChange={(e) => setSettings({ ...settings, default_quantity: parseInt(e.target.value) })}
                required
              />
            </div>

            <div className="form-group">
              <label>Max Trades Per Day</label>
              <input
                type="number"
                min="1"
                max="100"
                value={settings.max_trades_per_day}
                onChange={(e) => setSettings({ ...settings, max_trades_per_day: parseInt(e.target.value) })}
                required
              />
            </div>

            <div className="form-group">
              <label>Risk Percentage</label>
              <input
                type="number"
                min="0.1"
                max="100"
                step="0.1"
                value={settings.risk_percentage}
                onChange={(e) => setSettings({ ...settings, risk_percentage: parseFloat(e.target.value) })}
                required
              />
            </div>

            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? 'Saving...' : 'Save Settings'}
            </button>
          </form>
        </div>

        <div className="card">
          <h2>How to Use</h2>
          <div style={{ lineHeight: '1.8' }}>
            <h3 style={{ marginBottom: '1rem', color: 'var(--primary-color)' }}>Getting Started</h3>
            
            <ol style={{ paddingLeft: '1.5rem', color: 'var(--text-secondary)' }}>
              <li style={{ marginBottom: '0.75rem' }}>
                <strong>Test with Paper Trading:</strong> Use Signal Tester to practice without real money
              </li>
              <li style={{ marginBottom: '0.75rem' }}>
                <strong>Configure Broker:</strong> Add your Angel One API credentials
              </li>
              <li style={{ marginBottom: '0.75rem' }}>
                <strong>Configure Telegram:</strong> Add your Telegram API and select groups
              </li>
              <li style={{ marginBottom: '0.75rem' }}>
                <strong>Go Live:</strong> Disable paper trading when confident
              </li>
            </ol>

            <h3 style={{ marginTop: '1.5rem', marginBottom: '1rem', color: 'var(--primary-color)' }}>
              Signal Format
            </h3>
            <pre style={{ 
              backgroundColor: 'var(--bg-color)', 
              padding: '1rem', 
              borderRadius: '0.5rem',
              marginTop: '0.5rem',
              overflow: 'auto',
              fontSize: '0.85rem'
            }}>
{`BUY RELIANCE @ 2500
Target: 2550
SL: 2480
Qty: 10`}
            </pre>
            
            <h3 style={{ marginTop: '1.5rem', marginBottom: '1rem', color: 'var(--warning-color)' }}>
              ⚠️ Risk Warning
            </h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
              Trading involves substantial risk. Always test thoroughly with paper trading before using real money. 
              Never invest more than you can afford to lose.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Settings
