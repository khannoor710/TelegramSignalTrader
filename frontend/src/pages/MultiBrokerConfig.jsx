import { useState, useEffect } from 'react'
import api from '../lib/api'

const BROKER_CONFIGS = {
  angel_one: {
    name: 'Angel One',
    fields: [
      { key: 'api_key', label: 'API Key', type: 'text', required: true, help: 'From SmartAPI developer portal' },
      { key: 'client_id', label: 'Client ID', type: 'text', required: true, help: 'Your Angel One account ID' },
      { key: 'pin', label: 'PIN', type: 'password', required: true, maxLength: 4, help: '4-digit trading PIN' },
      { key: 'totp_secret', label: 'TOTP Secret', type: 'password', required: true, help: 'From authenticator setup' }
    ]
  },
  zerodha: {
    name: 'Zerodha Kite',
    fields: [
      { key: 'api_key', label: 'API Key', type: 'text', required: true, help: 'From Kite Connect developer console' },
      { key: 'api_secret', label: 'API Secret', type: 'password', required: true, help: 'API secret from Kite Connect' },
      { key: 'client_id', label: 'Client ID', type: 'text', required: true, help: 'Your Zerodha client ID (e.g., AB1234)' },
      { key: 'pin', label: 'Request Token', type: 'password', required: false, help: 'Request token from OAuth redirect (leave empty for login URL)' }
    ]
  },
  shoonya: {
    name: 'Shoonya (Finvasia)',
    fields: [
      { key: 'api_key', label: 'Vendor Code', type: 'text', required: true, help: 'Vendor code from Shoonya' },
      { key: 'client_id', label: 'User ID', type: 'text', required: true, help: 'Your Shoonya user ID' },
      { key: 'pin', label: 'Password', type: 'password', required: true, help: 'Trading password' },
      { key: 'totp_secret', label: 'TOTP', type: 'password', required: true, help: '6-digit OTP or TOTP secret' }
    ]
  },
  upstox: {
    name: 'Upstox',
    fields: [
      { key: 'api_key', label: 'API Key', type: 'text', required: true },
      { key: 'api_secret', label: 'API Secret', type: 'password', required: true },
      { key: 'client_id', label: 'Client ID', type: 'text', required: true },
      { key: 'pin', label: 'PIN', type: 'password', required: true }
    ]
  }
}

function MultiBrokerConfig() {
  const [selectedBroker, setSelectedBroker] = useState('angel_one')
  const [config, setConfig] = useState({ broker_name: 'angel_one', api_key: '', api_secret: '', client_id: '', pin: '', totp_secret: '' })
  const [availableBrokers, setAvailableBrokers] = useState([])
  const [configuredBrokers, setConfiguredBrokers] = useState([])
  const [activeBroker, setActiveBroker] = useState(null)
  const [loading, setLoading] = useState(false)
  const [showHelp, setShowHelp] = useState({})

  useEffect(() => {
    fetchAvailableBrokers()
    fetchConfiguredBrokers()
    fetchActiveBroker()
  }, [])

  useEffect(() => {
    setConfig(prev => ({ ...prev, broker_name: selectedBroker }))
  }, [selectedBroker])

  const fetchAvailableBrokers = async () => {
    try {
      const r = await api.get('/broker/brokers')
      setAvailableBrokers(r.data.brokers || [])
    } catch (e) {
      console.error('Failed to fetch brokers:', e)
    }
  }

  const fetchConfiguredBrokers = async () => {
    try {
      const r = await api.get('/broker/brokers/configured')
      setConfiguredBrokers(r.data.brokers || [])
    } catch (e) {
      console.error('Failed to fetch configured brokers:', e)
    }
  }

  const fetchActiveBroker = async () => {
    try {
      const r = await api.get('/broker/brokers/active')
      setActiveBroker(r.data.broker_type)
    } catch (e) {
      console.error('Failed to fetch active broker:', e)
    }
  }

  const handleConfigSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    try {
      await api.post('/broker/config', config)
      alert(`${BROKER_CONFIGS[selectedBroker]?.name || selectedBroker} configuration saved!`)
      fetchConfiguredBrokers()
      setConfig({ broker_name: selectedBroker, api_key: '', api_secret: '', client_id: '', pin: '', totp_secret: '' })
    } catch (e) {
      alert('Error: ' + (e.response?.data?.detail || e.message))
    }
    setLoading(false)
  }

  const handleLogin = async (brokerType) => {
    try {
      const result = await api.post(`/broker/brokers/${brokerType}/login`)
      if (result.data.status === 'pending' && result.data.login_url) {
        // Zerodha manual login flow
        window.open(result.data.login_url, '_blank')
        alert('Please complete login in the new window, then click OK and enter the request token')
        const requestToken = prompt('Enter request token from redirect URL:')
        if (requestToken) {
          // Update config with request token and retry login
          await api.post('/broker/config', { 
            broker_name: brokerType,
            ...configuredBrokers.find(b => b.broker_type === brokerType),
            pin: requestToken 
          })
          await handleLogin(brokerType)
        }
      } else {
        alert(`Connected to ${brokerType}!`)
        fetchConfiguredBrokers()
      }
    } catch (e) {
      alert('Login failed: ' + (e.response?.data?.detail || e.message))
    }
  }

  const handleLogout = async (brokerType) => {
    try {
      await api.post(`/broker/brokers/${brokerType}/logout`)
      alert(`Logged out from ${brokerType}`)
      fetchConfiguredBrokers()
    } catch (e) {
      alert('Logout failed: ' + e.message)
    }
  }

  const handleSetActive = async (brokerType) => {
    try {
      await api.post(`/broker/brokers/active?broker_type=${brokerType}`)
      alert(`Active broker set to ${brokerType}`)
      setActiveBroker(brokerType)
    } catch (e) {
      alert('Failed to set active broker: ' + e.message)
    }
  }

  const brokerConfig = BROKER_CONFIGS[selectedBroker] || BROKER_CONFIGS.angel_one

  return (
    <div>
      <h1 style={{ marginBottom: '2rem' }}>Multi-Broker Configuration</h1>

      <div className="grid grid-2">
        {/* Configuration Panel */}
        <div className="card">
          <h2>Add/Update Broker</h2>
          
          <div className="form-group">
            <label>Select Broker</label>
            <select 
              value={selectedBroker} 
              onChange={e => setSelectedBroker(e.target.value)}
              style={{ width: '100%', padding: '0.5rem', borderRadius: '0.375rem', border: '1px solid #e2e8f0' }}
            >
              {availableBrokers.map(broker => (
                <option key={broker} value={broker}>
                  {BROKER_CONFIGS[broker]?.name || broker}
                </option>
              ))}
            </select>
          </div>

          <form onSubmit={handleConfigSubmit}>
            {brokerConfig.fields.map(field => (
              <div key={field.key} className="form-group">
                <label>
                  {field.label}
                  {field.help && (
                    <button
                      type="button"
                      onClick={() => setShowHelp(prev => ({ ...prev, [field.key]: !prev[field.key] }))}
                      style={{ marginLeft: '0.5rem', background: 'none', border: 'none', color: 'var(--primary-color)', cursor: 'pointer', fontSize: '0.85rem' }}
                    >
                      {showHelp[field.key] ? '▼' : '▶'}
                    </button>
                  )}
                </label>
                {showHelp[field.key] && field.help && (
                  <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
                    {field.help}
                  </div>
                )}
                <input 
                  type={field.type}
                  value={config[field.key] || ''}
                  onChange={e => setConfig({ ...config, [field.key]: e.target.value })}
                  required={field.required}
                  maxLength={field.maxLength}
                />
              </div>
            ))}
            <button type="submit" className="btn btn-primary" disabled={loading} style={{ width: '100%' }}>
              {loading ? 'Saving...' : 'Save Configuration'}
            </button>
          </form>
        </div>

        {/* Configured Brokers Panel */}
        <div className="card">
          <h2>Configured Brokers</h2>
          
          {configuredBrokers.length === 0 ? (
            <p style={{ textAlign: 'center', color: 'var(--text-secondary)', padding: '2rem' }}>
              No brokers configured yet
            </p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {configuredBrokers.map(broker => (
                <div 
                  key={broker.id}
                  style={{
                    padding: '1rem',
                    borderRadius: '0.5rem',
                    border: activeBroker === broker.broker_type ? '2px solid var(--primary-color)' : '1px solid #e2e8f0',
                    backgroundColor: 'var(--bg-color)'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                    <div>
                      <h3 style={{ margin: 0, fontSize: '1.1rem' }}>
                        {BROKER_CONFIGS[broker.broker_type]?.name || broker.broker_type}
                        {activeBroker === broker.broker_type && (
                          <span style={{ marginLeft: '0.5rem', fontSize: '0.75rem', padding: '0.25rem 0.5rem', borderRadius: '0.25rem', backgroundColor: 'var(--primary-color)', color: 'white' }}>
                            ACTIVE
                          </span>
                        )}
                      </h3>
                      <p style={{ margin: '0.25rem 0 0', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                        Client: {broker.client_id}
                      </p>
                    </div>
                    <div style={{
                      width: '50px',
                      height: '50px',
                      borderRadius: '50%',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      backgroundColor: broker.is_logged_in ? 'rgba(16,185,129,0.2)' : 'rgba(239,68,68,0.2)',
                      border: '2px solid ' + (broker.is_logged_in ? 'var(--success-color)' : 'var(--danger-color)')
                    }}>
                      <span style={{ fontSize: '1.25rem' }}>
                        {broker.is_logged_in ? '✓' : '✗'}
                      </span>
                    </div>
                  </div>
                  
                  <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.75rem' }}>
                    {!broker.is_logged_in ? (
                      <button
                        onClick={() => handleLogin(broker.broker_type)}
                        className="btn btn-success"
                        style={{ flex: 1, fontSize: '0.85rem' }}
                      >
                        Connect
                      </button>
                    ) : (
                      <button
                        onClick={() => handleLogout(broker.broker_type)}
                        className="btn btn-danger"
                        style={{ flex: 1, fontSize: '0.85rem' }}
                      >
                        Disconnect
                      </button>
                    )}
                    
                    {activeBroker !== broker.broker_type && (
                      <button
                        onClick={() => handleSetActive(broker.broker_type)}
                        className="btn btn-secondary"
                        style={{ flex: 1, fontSize: '0.85rem' }}
                      >
                        Set Active
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default MultiBrokerConfig
