import { useState, useEffect } from 'react'
import api from '../lib/api'

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
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const [saveSuccess, setSaveSuccess] = useState(false)
  const [activeSection, setActiveSection] = useState('trading')

  useEffect(() => { fetchSettings() }, [])

  const fetchSettings = async () => {
    setLoading(true)
    try {
      const response = await api.get('/config/settings')
      setSettings(prev => ({ ...prev, ...response.data }))
    } catch (err) {
      if (err.response?.status !== 404) setError('Failed to load settings')
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSaving(true)
    setSaveSuccess(false)
    setError(null)
    try {
      await api.post('/config/settings', settings)
      setSaveSuccess(true)
      setTimeout(() => setSaveSuccess(false), 3000)
    } catch (err) {
      setError('Failed to save: ' + (err.response?.data?.detail || err.message))
    } finally {
      setSaving(false)
    }
  }

  const update = (key, value) => {
    setSettings(prev => ({ ...prev, [key]: value }))
    setSaveSuccess(false)
  }

  const sections = [
    { id: 'trading', label: 'Trading Mode', icon: '📊' },
    { id: 'automation', label: 'Automation', icon: '🤖' },
    { id: 'risk', label: 'Risk Management', icon: '🛡️' },
    { id: 'help', label: 'Help', icon: '❓' }
  ]

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '50vh' }}>
        <div style={{ textAlign: 'center' }}>
          <div className="loading-spinner" style={{ margin: '0 auto 1rem' }}></div>
          <p style={{ color: 'var(--text-secondary)' }}>Loading settings...</p>
        </div>
      </div>
    )
  }

  return (
    <div>
      <div style={{ marginBottom: '2rem' }}>
        <h1 style={{ marginBottom: '0.5rem' }}>Settings</h1>
        <p style={{ color: 'var(--text-secondary)', margin: 0 }}>Configure trading preferences and risk parameters</p>
      </div>

      {/* Messages */}
      {saveSuccess && (
        <div style={{ padding: '1rem', marginBottom: '1.5rem', backgroundColor: 'rgba(16, 185, 129, 0.1)', border: '1px solid var(--success-color)', borderRadius: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <span>✓</span>
          <span style={{ color: 'var(--success-color)', fontWeight: '500' }}>Settings saved successfully!</span>
        </div>
      )}
      {error && (
        <div style={{ padding: '1rem', marginBottom: '1.5rem', backgroundColor: 'rgba(239, 68, 68, 0.1)', border: '1px solid var(--danger-color)', borderRadius: '0.5rem' }}>
          <span style={{ color: 'var(--danger-color)' }}>⚠️ {error}</span>
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '200px 1fr', gap: '1.5rem' }}>
        {/* Sidebar */}
        <div className="card" style={{ padding: '0.5rem', height: 'fit-content' }}>
          {sections.map(s => (
            <button
              key={s.id}
              onClick={() => setActiveSection(s.id)}
              style={{
                display: 'flex', alignItems: 'center', gap: '0.75rem', width: '100%',
                padding: '0.75rem 1rem', border: 'none', borderRadius: '0.5rem',
                backgroundColor: activeSection === s.id ? 'var(--primary-color)' : 'transparent',
                color: activeSection === s.id ? 'white' : 'var(--text-color)',
                cursor: 'pointer', textAlign: 'left', marginBottom: '0.25rem'
              }}
            >
              <span>{s.icon}</span><span>{s.label}</span>
            </button>
          ))}
        </div>

        {/* Main Content */}
        <form onSubmit={handleSubmit}>
          {/* Trading Mode */}
          {activeSection === 'trading' && (
            <div className="card">
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.5rem' }}>
                <span style={{ fontSize: '1.5rem' }}>📊</span>
                <div>
                  <h2 style={{ margin: 0 }}>Trading Mode</h2>
                  <p style={{ margin: 0, color: 'var(--text-secondary)', fontSize: '0.9rem' }}>Choose paper or live trading</p>
                </div>
              </div>

              {/* Mode Toggle */}
              <div 
                onClick={() => update('paper_trading_enabled', !settings.paper_trading_enabled)}
                style={{
                  padding: '1.5rem', borderRadius: '0.75rem', cursor: 'pointer', marginBottom: '1.5rem',
                  border: `2px solid ${settings.paper_trading_enabled ? 'var(--success-color)' : 'var(--danger-color)'}`,
                  backgroundColor: settings.paper_trading_enabled ? 'rgba(16, 185, 129, 0.05)' : 'rgba(239, 68, 68, 0.05)'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                    <div style={{
                      width: '50px', height: '50px', borderRadius: '50%',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      backgroundColor: settings.paper_trading_enabled ? 'var(--success-color)' : 'var(--danger-color)',
                      color: 'white', fontSize: '1.5rem'
                    }}>
                      {settings.paper_trading_enabled ? '📝' : '💰'}
                    </div>
                    <div>
                      <h3 style={{ margin: 0, color: settings.paper_trading_enabled ? 'var(--success-color)' : 'var(--danger-color)' }}>
                        {settings.paper_trading_enabled ? 'Paper Trading Mode' : 'LIVE Trading Mode'}
                      </h3>
                      <p style={{ margin: '0.25rem 0 0', color: 'var(--text-secondary)' }}>
                        {settings.paper_trading_enabled ? 'Practice with virtual money' : '⚠️ Real money trades!'}
                      </p>
                    </div>
                  </div>
                  <div style={{
                    width: '60px', height: '30px', borderRadius: '15px', position: 'relative',
                    backgroundColor: settings.paper_trading_enabled ? 'var(--success-color)' : 'var(--border-color)'
                  }}>
                    <div style={{
                      width: '24px', height: '24px', borderRadius: '50%', backgroundColor: 'white',
                      position: 'absolute', top: '3px',
                      left: settings.paper_trading_enabled ? '33px' : '3px',
                      transition: 'left 0.3s', boxShadow: '0 2px 4px rgba(0,0,0,0.2)'
                    }}></div>
                  </div>
                </div>
              </div>

              {settings.paper_trading_enabled && (
                <div className="form-group">
                  <label>💵 Virtual Balance (₹)</label>
                  <input type="number" min="10000" step="10000" value={settings.paper_trading_balance}
                    onChange={(e) => update('paper_trading_balance', parseFloat(e.target.value) || 100000)} />
                </div>
              )}

              {!settings.paper_trading_enabled && (
                <div style={{ padding: '1rem', backgroundColor: 'rgba(239, 68, 68, 0.1)', borderRadius: '0.5rem', borderLeft: '4px solid var(--danger-color)' }}>
                  <strong style={{ color: 'var(--danger-color)' }}>⚠️ Live Trading Warning</strong>
                  <p style={{ margin: '0.5rem 0 0', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
                    Real money trades will be executed. Test thoroughly first!
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Automation */}
          {activeSection === 'automation' && (
            <div className="card">
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.5rem' }}>
                <span style={{ fontSize: '1.5rem' }}>🤖</span>
                <div>
                  <h2 style={{ margin: 0 }}>Automation</h2>
                  <p style={{ margin: 0, color: 'var(--text-secondary)', fontSize: '0.9rem' }}>Control signal processing</p>
                </div>
              </div>

              <div style={{ padding: '1rem', backgroundColor: 'var(--bg-color)', borderRadius: '0.5rem', marginBottom: '1rem' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', cursor: 'pointer' }}>
                  <input type="checkbox" checked={settings.auto_trade_enabled} onChange={(e) => update('auto_trade_enabled', e.target.checked)} style={{ width: '20px', height: '20px' }} />
                  <div>
                    <strong>Enable Auto Trading</strong>
                    <p style={{ margin: 0, color: 'var(--text-secondary)', fontSize: '0.85rem' }}>Automatically create trades from signals</p>
                  </div>
                </label>
              </div>

              <div style={{ padding: '1rem', backgroundColor: 'var(--bg-color)', borderRadius: '0.5rem', marginBottom: '1rem' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', cursor: 'pointer' }}>
                  <input type="checkbox" checked={settings.require_manual_approval} onChange={(e) => update('require_manual_approval', e.target.checked)} style={{ width: '20px', height: '20px' }} />
                  <div>
                    <strong>Require Manual Approval</strong>
                    <p style={{ margin: 0, color: 'var(--text-secondary)', fontSize: '0.85rem' }}>Review trades before execution (recommended)</p>
                  </div>
                </label>
              </div>

              {/* Workflow */}
              <div style={{ padding: '1rem', backgroundColor: 'rgba(59, 130, 246, 0.05)', borderRadius: '0.5rem', border: '1px solid rgba(59, 130, 246, 0.2)' }}>
                <h4 style={{ margin: '0 0 0.75rem', color: 'var(--primary-color)' }}>Current Workflow</h4>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap', fontSize: '0.9rem' }}>
                  <span style={{ padding: '0.4rem 0.75rem', backgroundColor: 'var(--card-bg)', borderRadius: '0.5rem' }}>📨 Signal</span>
                  <span>→</span>
                  <span style={{ padding: '0.4rem 0.75rem', backgroundColor: 'var(--card-bg)', borderRadius: '0.5rem' }}>🔍 Parse</span>
                  <span>→</span>
                  {settings.auto_trade_enabled ? (
                    <span style={{ padding: '0.4rem 0.75rem', backgroundColor: 'rgba(16, 185, 129, 0.2)', borderRadius: '0.5rem' }}>📝 Trade</span>
                  ) : (
                    <span style={{ padding: '0.4rem 0.75rem', backgroundColor: 'rgba(251, 191, 36, 0.2)', borderRadius: '0.5rem' }}>⏸️ Manual</span>
                  )}
                  {settings.require_manual_approval && settings.auto_trade_enabled && (
                    <><span>→</span><span style={{ padding: '0.4rem 0.75rem', backgroundColor: 'rgba(251, 191, 36, 0.2)', borderRadius: '0.5rem' }}>✋ Approve</span></>
                  )}
                  <span>→</span>
                  <span style={{ padding: '0.4rem 0.75rem', backgroundColor: settings.paper_trading_enabled ? 'rgba(139, 92, 246, 0.2)' : 'rgba(239, 68, 68, 0.2)', borderRadius: '0.5rem' }}>
                    {settings.paper_trading_enabled ? '📝 Paper' : '💰 Live'}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Risk Management */}
          {activeSection === 'risk' && (
            <div className="card">
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.5rem' }}>
                <span style={{ fontSize: '1.5rem' }}>🛡️</span>
                <div>
                  <h2 style={{ margin: 0 }}>Risk Management</h2>
                  <p style={{ margin: 0, color: 'var(--text-secondary)', fontSize: '0.9rem' }}>Set trading limits</p>
                </div>
              </div>

              <div className="grid grid-2" style={{ gap: '1.5rem' }}>
                <div className="form-group">
                  <label>📦 Default Quantity</label>
                  <input type="number" min="1" value={settings.default_quantity} onChange={(e) => update('default_quantity', parseInt(e.target.value) || 1)} />
                  <small style={{ color: 'var(--text-secondary)' }}>Shares/lots if not in signal</small>
                </div>
                <div className="form-group">
                  <label>📈 Max Trades/Day</label>
                  <input type="number" min="1" max="100" value={settings.max_trades_per_day} onChange={(e) => update('max_trades_per_day', parseInt(e.target.value) || 10)} />
                </div>
                <div className="form-group">
                  <label>⚖️ Risk % per Trade</label>
                  <input type="number" min="0.1" max="10" step="0.1" value={settings.risk_percentage} onChange={(e) => update('risk_percentage', parseFloat(e.target.value) || 1)} />
                </div>
              </div>

              <div style={{ marginTop: '1.5rem', padding: '1rem', backgroundColor: 'var(--bg-color)', borderRadius: '0.5rem' }}>
                <h4 style={{ margin: '0 0 0.75rem' }}>Summary</h4>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem', textAlign: 'center' }}>
                  <div>
                    <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: 'var(--primary-color)' }}>{settings.default_quantity}</div>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Qty/Trade</div>
                  </div>
                  <div>
                    <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: 'var(--warning-color)' }}>{settings.max_trades_per_day}</div>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Max/Day</div>
                  </div>
                  <div>
                    <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: 'var(--danger-color)' }}>{settings.risk_percentage}%</div>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Risk</div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Help */}
          {activeSection === 'help' && (
            <div className="card">
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.5rem' }}>
                <span style={{ fontSize: '1.5rem' }}>❓</span>
                <h2 style={{ margin: 0 }}>Getting Started</h2>
              </div>

              {[
                { step: 1, title: 'Test with Paper Trading', icon: '📝' },
                { step: 2, title: 'Configure Broker Credentials', icon: '🔌' },
                { step: 3, title: 'Connect Telegram Groups', icon: '📱' },
                { step: 4, title: 'Review & Approve Trades', icon: '✅' },
                { step: 5, title: 'Go Live When Confident', icon: '🚀' }
              ].map(item => (
                <div key={item.step} style={{ display: 'flex', gap: '1rem', padding: '1rem', backgroundColor: 'var(--bg-color)', borderRadius: '0.5rem', marginBottom: '0.5rem' }}>
                  <div style={{ width: '35px', height: '35px', borderRadius: '50%', backgroundColor: 'var(--primary-color)', color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 'bold', flexShrink: 0 }}>{item.step}</div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}><span>{item.icon}</span> {item.title}</div>
                </div>
              ))}

              <div style={{ marginTop: '1rem', padding: '1rem', backgroundColor: 'rgba(251, 191, 36, 0.1)', borderRadius: '0.5rem', borderLeft: '4px solid var(--warning-color)' }}>
                <strong style={{ color: 'var(--warning-color)' }}>⚠️ Risk Warning</strong>
                <p style={{ margin: '0.5rem 0 0', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
                  Trading involves risk. Always test with paper trading first. Never invest more than you can afford to lose.
                </p>
              </div>
            </div>
          )}

          {/* Save Button */}
          {activeSection !== 'help' && (
            <div style={{ marginTop: '1.5rem', padding: '1rem', backgroundColor: 'var(--card-bg)', borderRadius: '0.5rem', display: 'flex', justifyContent: 'flex-end' }}>
              <button type="submit" className="btn btn-primary" disabled={saving} style={{ minWidth: '150px' }}>
                {saving ? 'Saving...' : '💾 Save Settings'}
              </button>
            </div>
          )}
        </form>
      </div>
    </div>
  )
}

export default Settings
