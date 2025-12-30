import { useState, useEffect, useRef, useCallback } from 'react'
import api from '../lib/api'

// Helper to get WebSocket URL
const getWebSocketUrl = () => {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.hostname
  const port = import.meta.env.VITE_API_PORT || '8000'
  if (host === 'localhost' || host === '127.0.0.1') {
    return `${protocol}//${host}:${port}/ws`
  }
  return `${protocol}//${window.location.host}/ws`
}

function TelegramConfig() {
  // Configuration state
  const [config, setConfig] = useState({
    api_id: '',
    api_hash: '',
    phone_number: '',
    monitored_chats: []
  })
  
  // UI state - Start with config if not set up
  const [activeTab, setActiveTab] = useState('messages') // Will update based on status
  const [availableChats, setAvailableChats] = useState([])
  const [messages, setMessages] = useState([])
  const [verificationCode, setVerificationCode] = useState('')
  const [needsVerification, setNeedsVerification] = useState(false)
  const [loading, setLoading] = useState(false)
  const [connectionStatus, setConnectionStatus] = useState(null)
  const [messageStats, setMessageStats] = useState(null)
  const [initialLoading, setInitialLoading] = useState(true)
  
  // History fetch state
  const [selectedChatForHistory, setSelectedChatForHistory] = useState('')
  const [historyLimit, setHistoryLimit] = useState(100)
  const [historyMessages, setHistoryMessages] = useState([])
  const [fetchingHistory, setFetchingHistory] = useState(false)
  const [saveToDb, setSaveToDb] = useState(true)
  
  // Filters
  const [filterSignalsOnly, setFilterSignalsOnly] = useState(false)
  const [selectedChatFilter, setSelectedChatFilter] = useState('')
  
  // Trade Execution Modal State
  const [showTradeModal, setShowTradeModal] = useState(false)
  const [selectedMessage, setSelectedMessage] = useState(null)
  const [tradeForm, setTradeForm] = useState({
    symbol: '',
    action: 'BUY',
    quantity: 1,
    entry_price: null,
    target_price: null,
    stop_loss: null,
    order_type: 'MARKET',
    exchange: 'NSE',
    product_type: 'INTRADAY'
  })
  const [tradeLoading, setTradeLoading] = useState(false)
  const [brokerStatus, setBrokerStatus] = useState(null)
  const [tradeResult, setTradeResult] = useState(null)
  const [error, setError] = useState(null)
  
  // WebSocket
  const wsRef = useRef(null)
  const reconnectTimeoutRef = useRef(null)

  useEffect(() => {
    const initializeData = async () => {
      await fetchConfig()
      await fetchConnectionStatus()
      await fetchMessageStats()
      await fetchMessages(true) // Show loading on initial fetch
      connectWebSocket()
    }
    
    initializeData()
    
    // Cleanup
    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
    }
  }, [])

  // Determine initial tab based on setup status
  useEffect(() => {
    if (connectionStatus !== null) {
      setInitialLoading(false)
      // If not connected, show config tab first
      if (!connectionStatus.is_connected && !connectionStatus.client_initialized) {
        setActiveTab('config')
      } else if (connectionStatus.is_connected && connectionStatus.monitored_chats_count === 0) {
        // Connected but no channels selected
        setActiveTab('config')
      }
    }
  }, [connectionStatus])

  // Auto-refresh messages every 10 seconds when connected
  useEffect(() => {
    if (!connectionStatus?.is_connected) return
    
    const interval = setInterval(() => {
      fetchMessages(false) // Don't show loading on auto-refresh
      fetchMessageStats()
    }, 10000) // Reduced to 10 seconds for faster updates
    
    return () => clearInterval(interval)
  }, [connectionStatus?.is_connected])

  const connectWebSocket = useCallback(() => {
    try {
      const wsUrl = getWebSocketUrl()
      
      wsRef.current = new WebSocket(wsUrl)
      
      wsRef.current.onopen = () => {
        console.log('WebSocket connected')
      }
      
      wsRef.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          if (data.type === 'new_message') {
            // Add new message to the top of the list
            const newMsg = data.data
            console.log('📨 New message via WebSocket:', newMsg.chat_name, newMsg.message_text?.substring(0, 50))
            
            setMessages(prev => {
              // Check if message already exists to prevent duplicates
              const exists = prev.some(m => m.message_id === newMsg.message_id && m.chat_id === newMsg.chat_id)
              if (exists) return prev
              return [newMsg, ...prev.slice(0, 99)]
            })
            
            fetchMessageStats() // Refresh stats
            
            // Show notification for new message
            if (newMsg.parsed_signal) {
              console.log('🔔 New signal detected!')
            }
          } else if (data.type === 'telegram_status') {
            // Update connection status from WebSocket
            console.log('📊 Status update:', data.data)
            setConnectionStatus(data.data)
          }
        } catch (e) {
          console.error('Error parsing WebSocket message:', e)
        }
      }
      
      wsRef.current.onclose = () => {
        console.log('WebSocket disconnected, reconnecting...')
        reconnectTimeoutRef.current = setTimeout(connectWebSocket, 3000)
      }
      
      wsRef.current.onerror = (error) => {
        console.error('WebSocket error:', error)
      }
    } catch (error) {
      console.error('Failed to connect WebSocket:', error)
    }
  }, [])

  const fetchConfig = async () => {
    try {
      const response = await api.get('/telegram/config')
      setConfig(response.data)
      fetchChats()
    } catch (error) {
      console.log('No config found')
    }
  }

  const fetchConnectionStatus = async () => {
    try {
      const response = await api.get('/telegram/status')
      setConnectionStatus(response.data)
    } catch (error) {
      console.error('Error fetching status:', error)
    }
  }

  const fetchMessageStats = async () => {
    try {
      const response = await api.get('/telegram/messages/stats')
      setMessageStats(response.data)
    } catch (error) {
      console.error('Error fetching stats:', error)
    }
  }

  const fetchChats = async () => {
    try {
      const response = await api.get('/telegram/chats')
      setAvailableChats(response.data.chats)
    } catch (error) {
      console.error('Error fetching chats:', error)
    }
  }

  const fetchMessages = async (showLoading = false) => {
    if (showLoading) setLoading(true)
    try {
      let url = '/telegram/messages?limit=100' // Increased limit
      if (filterSignalsOnly) {
        url += '&unprocessed_only=true'
      }
      const response = await api.get(url)
      const fetchedMessages = response.data || []
      setMessages(fetchedMessages)
      
      // Log for debugging
      console.log(`Fetched ${fetchedMessages.length} messages from backend`)
      
      // Show notification if new messages were found
      if (showLoading && fetchedMessages.length > 0) {
        const latestMsg = fetchedMessages[0]
        console.log('Latest message:', latestMsg?.message_text?.substring(0, 50))
      }
    } catch (error) {
      console.error('Error fetching messages:', error)
      setError('Failed to fetch messages: ' + (error.response?.data?.detail || error.message))
    } finally {
      if (showLoading) setLoading(false)
    }
  }

  const fetchHistoricMessages = async () => {
    if (!selectedChatForHistory) {
      alert('Please select a chat first')
      return
    }
    
    setFetchingHistory(true)
    try {
      const response = await api.get(
        `/telegram/history/${selectedChatForHistory}?limit=${historyLimit}&save_to_db=${saveToDb}`
      )
      
      if (saveToDb) {
        alert(`Saved ${response.data.saved} messages, skipped ${response.data.skipped} duplicates, found ${response.data.signals} signals`)
        fetchMessages()
        fetchMessageStats()
      } else {
        setHistoryMessages(response.data.messages || [])
      }
    } catch (error) {
      alert('Error fetching history: ' + (error.response?.data?.detail || error.message))
    } finally {
      setFetchingHistory(false)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)

    try {
      await api.post('/telegram/config', config)
      const initResponse = await api.post('/telegram/initialize')
      
      if (initResponse.data.status === 'code_sent') {
        setNeedsVerification(true)
        // Don't use alert, the UI shows the verification form
      } else if (initResponse.data.status === 'authorized') {
        setNeedsVerification(false)
        await fetchChats()
        await fetchConnectionStatus()
        alert('✅ Connected to Telegram! Now select channels to monitor.')
      } else if (initResponse.data.status === 'error') {
        alert('❌ ' + (initResponse.data.message || 'Failed to connect'))
      }
    } catch (error) {
      const errorMsg = error.response?.data?.detail || error.response?.data?.message || error.message
      alert('❌ Error: ' + errorMsg)
    } finally {
      setLoading(false)
    }
  }

  const handleVerification = async (e) => {
    e.preventDefault()
    setLoading(true)

    try {
      const response = await api.post('/telegram/verify-code', null, {
        params: { phone: config.phone_number, code: verificationCode }
      })
      
      if (response.data.status === 'success') {
        setNeedsVerification(false)
        setVerificationCode('')
        await fetchChats()
        await fetchConnectionStatus()
        alert('✅ ' + (response.data.message || 'Verification successful! Now select channels to monitor.'))
      } else {
        alert('❌ ' + (response.data.message || 'Verification failed'))
      }
    } catch (error) {
      const errorMsg = error.response?.data?.detail || error.response?.data?.message || error.message
      alert('❌ Verification failed: ' + errorMsg)
    } finally {
      setLoading(false)
    }
  }

  const toggleChat = (chatId) => {
    const chats = config.monitored_chats.includes(chatId)
      ? config.monitored_chats.filter(id => id !== chatId)
      : [...config.monitored_chats, chatId]
    setConfig({ ...config, monitored_chats: chats })
  }

  const updateMonitoredChats = async () => {
    setLoading(true)
    try {
      // First save the config
      await api.post('/telegram/config', config)
      
      // Give the database a moment to commit
      await new Promise(resolve => setTimeout(resolve, 100))
      
      // Then reload Telegram service to pick up new monitored chats
      const reloadRes = await api.post('/telegram/reload')
      
      // Update local connection status
      setConnectionStatus(reloadRes.data)
      
      // Show appropriate message
      const count = reloadRes.data.monitored_chats_count || 0
      if (count > 0) {
        alert(`✅ Now monitoring ${count} channel${count !== 1 ? 's' : ''}! Switching to Live Messages.`)
        setActiveTab('messages')
        // Refresh messages to show any new ones
        fetchMessages()
      } else {
        alert('⚠️ Configuration saved, but no channels are selected. Please select at least one channel.')
      }
      
      // Refresh status to ensure UI is in sync
      await fetchConnectionStatus()
    } catch (error) {
      console.error('Error updating chats:', error)
      alert('❌ Error: ' + (error.response?.data?.detail || error.message))
      // Refresh status even on error
      fetchConnectionStatus()
    } finally {
      setLoading(false)
    }
  }

  const reloadTelegramService = async () => {
    setLoading(true)
    try {
      const response = await api.post('/telegram/reload')
      alert(`Telegram service reloaded! Monitoring ${response.data.monitored_chats_count} chats.`)
      fetchConnectionStatus()
    } catch (error) {
      alert('Error reloading: ' + (error.response?.data?.detail || error.message))
    } finally {
      setLoading(false)
    }
  }

  // Trade execution functions
  const openTradeModal = async (message) => {
    setSelectedMessage(message)
    setTradeResult(null)
    setTradeLoading(true)
    
    try {
      // Fetch signal details with broker status
      const response = await api.get(`/telegram/messages/${message.id}/signal`)
      const signalData = response.data
      
      // Set form values from signal
      setTradeForm({
        symbol: signalData.signal.symbol || '',
        action: signalData.signal.action || 'BUY',
        quantity: signalData.settings.default_quantity || 1,
        entry_price: signalData.signal.entry_price || null,
        target_price: signalData.signal.target_price || null,
        stop_loss: signalData.signal.stop_loss || null,
        order_type: 'MARKET',
        exchange: signalData.token_info?.exchange || 'NSE',
        product_type: 'INTRADAY'
      })
      
      setBrokerStatus(signalData.broker_status)
      setShowTradeModal(true)
    } catch (error) {
      alert('Error loading signal: ' + (error.response?.data?.detail || error.message))
    } finally {
      setTradeLoading(false)
    }
  }

  const closeTradeModal = () => {
    setShowTradeModal(false)
    setSelectedMessage(null)
    setTradeResult(null)
  }

  const executeTrade = async () => {
    if (!selectedMessage) return
    
    setTradeLoading(true)
    setTradeResult(null)
    
    try {
      const response = await api.post(
        `/telegram/messages/${selectedMessage.id}/execute`,
        tradeForm
      )
      
      setTradeResult(response.data)
      
      // Refresh messages to show updated status
      fetchMessages()
      fetchMessageStats()
      
      if (response.data.status === 'executed') {
        // Auto-close after successful execution
        setTimeout(() => {
          closeTradeModal()
        }, 3000)
      }
    } catch (error) {
      setTradeResult({
        status: 'error',
        message: error.response?.data?.detail || error.message
      })
    } finally {
      setTradeLoading(false)
    }
  }

  // Filter messages based on selected chat
  const filteredMessages = messages.filter(msg => {
    if (selectedChatFilter && msg.chat_id !== selectedChatFilter) return false
    if (filterSignalsOnly && !msg.parsed_signal) return false
    return true
  })

  const renderConnectionBadge = () => {
    if (!connectionStatus) return null
    
    // Determine status message and action
    let statusMessage = ''
    let actionText = ''
    
    if (connectionStatus.is_connected) {
      if (connectionStatus.monitored_chats_count > 0) {
        statusMessage = `Connected • Monitoring ${connectionStatus.monitored_chats_count} channels`
      } else {
        statusMessage = 'Connected • No channels selected'
        actionText = 'Select channels below'
      }
    } else if (connectionStatus.error) {
      statusMessage = connectionStatus.error
    } else {
      statusMessage = 'Not configured'
    }
    
    return (
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
        <div style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '0.5rem',
          padding: '0.5rem 1rem',
          borderRadius: '2rem',
          backgroundColor: connectionStatus.is_connected 
            ? connectionStatus.monitored_chats_count > 0 
              ? 'var(--success-color)' 
              : 'var(--warning-color)'
            : 'var(--danger-color)',
          color: 'white',
          fontSize: '0.85rem'
        }}>
          <span style={{
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            backgroundColor: 'white',
            animation: connectionStatus.is_connected ? 'pulse 2s infinite' : 'none'
          }} />
          {statusMessage}
        </div>
        {actionText && (
          <span style={{ color: 'var(--warning-color)', fontSize: '0.85rem' }}>
            ⚠️ {actionText}
          </span>
        )}
        <button 
          onClick={reloadTelegramService} 
          className="btn" 
          style={{ padding: '0.5rem 0.75rem', fontSize: '0.85rem' }}
          disabled={loading}
          title="Reload Telegram connection"
        >
          🔄 Reconnect
        </button>
      </div>
    )
  }

  const renderTabs = () => {
    // Show warning badges on tabs
    const configWarning = !connectionStatus?.is_connected || connectionStatus?.monitored_chats_count === 0
    
    return (
      <div style={{
        display: 'flex',
        gap: '0.5rem',
        marginBottom: '1.5rem',
        borderBottom: '1px solid var(--border-color)',
        paddingBottom: '0.5rem',
        flexWrap: 'wrap'
      }}>
        {[
          { 
            id: 'messages', 
            label: '📨 Live Messages', 
            badge: messages.length,
            disabled: !connectionStatus?.is_connected
          },
          { 
            id: 'history', 
            label: '📜 Fetch History',
            disabled: !connectionStatus?.is_connected
          },
          { 
            id: 'config', 
            label: '⚙️ Configuration',
            warning: configWarning
          }
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => !tab.disabled && setActiveTab(tab.id)}
            style={{
              padding: '0.75rem 1.5rem',
              border: 'none',
              borderRadius: '0.5rem 0.5rem 0 0',
              backgroundColor: activeTab === tab.id ? 'var(--primary-color)' : 'transparent',
              color: activeTab === tab.id ? 'white' : tab.disabled ? 'var(--text-secondary)' : 'var(--text-color)',
              cursor: tab.disabled ? 'not-allowed' : 'pointer',
              fontWeight: activeTab === tab.id ? 'bold' : 'normal',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              opacity: tab.disabled ? 0.5 : 1
            }}
          >
            {tab.label}
            {tab.badge > 0 && (
              <span style={{
                backgroundColor: 'var(--secondary-color)',
                color: 'white',
                padding: '0.1rem 0.5rem',
                borderRadius: '1rem',
                fontSize: '0.75rem'
              }}>{tab.badge}</span>
            )}
            {tab.warning && !tab.disabled && (
              <span style={{
                backgroundColor: 'var(--warning-color)',
                color: 'white',
                padding: '0.1rem 0.4rem',
                borderRadius: '1rem',
                fontSize: '0.7rem'
              }}>!</span>
            )}
          </button>
        ))}
      </div>
    )
  }

  const renderStats = () => {
    if (!messageStats) return null
    return (
      <div className="grid grid-4" style={{ marginBottom: '1.5rem' }}>
        <div className="stat-card">
          <div className="stat-value">{messageStats.total_messages}</div>
          <div className="stat-label">Total Messages</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ color: 'var(--secondary-color)' }}>
            {messageStats.total_signals}
          </div>
          <div className="stat-label">Trading Signals</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ color: 'var(--warning-color)' }}>
            {messageStats.unprocessed_signals}
          </div>
          <div className="stat-label">Pending Signals</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{messageStats.chats?.length || 0}</div>
          <div className="stat-label">Active Chats</div>
        </div>
      </div>
    )
  }

  const renderMessageCard = (msg, isHistoric = false) => {
    const parsedSignal = msg.parsed_signal 
      ? (typeof msg.parsed_signal === 'string' ? JSON.parse(msg.parsed_signal) : msg.parsed_signal)
      : null

    return (
      <div
        key={msg.id || msg.message_id}
        style={{
          padding: '1rem',
          marginBottom: '0.75rem',
          backgroundColor: msg.is_processed ? 'var(--card-bg)' : 'var(--bg-color)',
          borderRadius: '0.5rem',
          borderLeft: parsedSignal 
            ? msg.is_processed 
              ? '4px solid var(--text-secondary)' 
              : '4px solid var(--secondary-color)' 
            : '4px solid transparent',
          transition: 'all 0.2s ease',
          opacity: msg.is_processed ? 0.7 : 1
        }}
      >
        <div style={{ 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'flex-start',
          marginBottom: '0.5rem' 
        }}>
          <div>
            <strong style={{ color: 'var(--primary-color)' }}>{msg.chat_name}</strong>
            <span style={{ 
              marginLeft: '0.5rem', 
              color: 'var(--text-secondary)',
              fontSize: '0.85rem'
            }}>
              @{msg.sender}
            </span>
            {msg.is_processed && (
              <span style={{
                marginLeft: '0.5rem',
                backgroundColor: 'var(--text-secondary)',
                color: 'white',
                padding: '0.1rem 0.4rem',
                borderRadius: '0.25rem',
                fontSize: '0.7rem'
              }}>
                PROCESSED
              </span>
            )}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            {parsedSignal && (
              <span style={{
                backgroundColor: parsedSignal.action === 'BUY' ? 'var(--success-color)' : 'var(--danger-color)',
                color: 'white',
                padding: '0.2rem 0.5rem',
                borderRadius: '0.25rem',
                fontSize: '0.75rem',
                fontWeight: 'bold'
              }}>
                {parsedSignal.action}
              </span>
            )}
            <small style={{ color: 'var(--text-secondary)' }}>
              {new Date(msg.timestamp).toLocaleString()}
            </small>
          </div>
        </div>
        
        <p style={{ 
          margin: '0.5rem 0',
          lineHeight: '1.5',
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-word'
        }}>
          {msg.message_text}
        </p>
        
        {parsedSignal && (
          <div style={{ 
            marginTop: '0.75rem', 
            padding: '0.75rem', 
            backgroundColor: 'var(--card-bg)', 
            borderRadius: '0.5rem'
          }}>
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(100px, 1fr))',
              gap: '0.5rem',
              marginBottom: '0.75rem'
            }}>
              <div>
                <small style={{ color: 'var(--text-secondary)' }}>Symbol</small>
                <div style={{ fontWeight: 'bold' }}>{parsedSignal.symbol}</div>
              </div>
              {parsedSignal.entry_price && (
                <div>
                  <small style={{ color: 'var(--text-secondary)' }}>Entry</small>
                  <div>₹{parsedSignal.entry_price}</div>
                </div>
              )}
              {parsedSignal.target_price && (
                <div>
                  <small style={{ color: 'var(--text-secondary)' }}>Target</small>
                  <div style={{ color: 'var(--success-color)' }}>₹{parsedSignal.target_price}</div>
                </div>
              )}
              {parsedSignal.stop_loss && (
                <div>
                  <small style={{ color: 'var(--text-secondary)' }}>Stop Loss</small>
                  <div style={{ color: 'var(--danger-color)' }}>₹{parsedSignal.stop_loss}</div>
                </div>
              )}
            </div>
            
            {/* Execute Trade Button */}
            {!isHistoric && !msg.is_processed && (
              <button
                onClick={() => openTradeModal(msg)}
                className="btn btn-primary"
                style={{
                  width: '100%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '0.5rem',
                  padding: '0.6rem 1rem',
                  fontSize: '0.9rem'
                }}
              >
                ⚡ Execute Trade
              </button>
            )}
            
            {msg.is_processed && (
              <div style={{ 
                textAlign: 'center', 
                color: 'var(--text-secondary)',
                fontSize: '0.85rem'
              }}>
                ✓ Trade already executed
              </div>
            )}
          </div>
        )}
      </div>
    )
  }

  const renderMessagesTab = () => (
    <>
      {/* Error Banner */}
      {error && (
        <div style={{
          padding: '1rem',
          backgroundColor: 'rgba(239, 68, 68, 0.1)',
          border: '1px solid var(--danger-color)',
          borderRadius: '0.5rem',
          marginBottom: '1.5rem',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between'
        }}>
          <span style={{ color: 'var(--danger-color)' }}>⚠️ {error}</span>
          <button 
            onClick={() => setError(null)} 
            style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '1.2rem', color: 'var(--text-secondary)' }}
          >
            ×
          </button>
        </div>
      )}
    
      {/* Show warning if not properly configured */}
      {(!connectionStatus?.is_connected || connectionStatus?.monitored_chats_count === 0) && (
        <div style={{
          padding: '1.5rem',
          backgroundColor: 'rgba(245, 158, 11, 0.1)',
          border: '1px solid var(--warning-color)',
          borderRadius: '0.5rem',
          marginBottom: '1.5rem',
          display: 'flex',
          alignItems: 'center',
          gap: '1rem'
        }}>
          <span style={{ fontSize: '2rem' }}>⚠️</span>
          <div>
            <strong style={{ color: 'var(--warning-color)' }}>
              {!connectionStatus?.is_connected 
                ? 'Telegram not connected' 
                : 'No channels selected'}
            </strong>
            <p style={{ margin: '0.25rem 0 0', color: 'var(--text-secondary)' }}>
              {!connectionStatus?.is_connected 
                ? 'Go to the Configuration tab to connect your Telegram account.' 
                : 'Go to the Configuration tab to select channels to monitor.'}
            </p>
          </div>
          <button 
            onClick={() => setActiveTab('config')} 
            className="btn btn-primary"
            style={{ marginLeft: 'auto', whiteSpace: 'nowrap' }}
          >
            Configure →
          </button>
        </div>
      )}
    
      {renderStats()}
      
      {/* Filters */}
      <div style={{ 
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
        gap: '1rem',
        marginBottom: '1rem'
      }}>
        <div className="form-group" style={{ margin: 0 }}>
          <label style={{ fontSize: '0.9rem', fontWeight: '600', marginBottom: '0.5rem', display: 'block' }}>
            Filter by Chat
          </label>
          <select
            value={selectedChatFilter}
            onChange={(e) => setSelectedChatFilter(e.target.value)}
            className="form-control"
          >
            <option value="">All Chats</option>
            {messageStats?.chats?.map(chat => (
              <option key={chat.chat_id} value={chat.chat_id}>
                {chat.chat_name} ({chat.message_count})
              </option>
            ))}
          </select>
        </div>
        
        <div className="form-group" style={{ margin: 0 }}>
          <label style={{ 
            fontSize: '0.9rem', 
            fontWeight: '600', 
            marginBottom: '0.5rem', 
            display: 'flex', 
            alignItems: 'center', 
            gap: '0.5rem' 
          }}>
            <input
              type="checkbox"
              checked={filterSignalsOnly}
              onChange={(e) => setFilterSignalsOnly(e.target.checked)}
              style={{ width: 'auto' }}
            />
            Trading Signals Only
            {filterSignalsOnly && (
              <span className="badge" style={{ backgroundColor: 'var(--primary-color)', marginLeft: 'auto' }}>
                {filteredMessages.filter(msg => msg.is_signal).length} of {filteredMessages.length}
              </span>
            )}
          </label>
        </div>
        
        <div className="form-group" style={{ margin: 0 }}>
          <label style={{ fontSize: '0.9rem', fontWeight: '600', marginBottom: '0.5rem', display: 'block', opacity: 0 }}>
            _
          </label>
          <button 
            onClick={() => fetchMessages(true)} 
            className="btn btn-outline"
            disabled={loading}
            style={{ 
              width: '100%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '0.5rem'
            }}
          >
            <span style={{
              display: 'inline-block',
              animation: loading ? 'spin 1s linear infinite' : 'none'
            }}>🔄</span>
            {loading ? 'Fetching...' : 'Refresh Now'}
          </button>
        </div>
      </div>

      {/* Messages List */}
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <h3 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            {connectionStatus?.is_connected ? (
              <>
                <span style={{
                  width: '10px',
                  height: '10px',
                  borderRadius: '50%',
                  backgroundColor: 'var(--success-color)',
                  animation: 'pulse 2s infinite'
                }} />
                Live Messages
                <small style={{ color: 'var(--text-secondary)', fontWeight: 'normal' }}>
                  (Real-time • Auto-refresh: 10s)
                </small>
              </>
            ) : (
              <>
                <span style={{
                  width: '10px',
                  height: '10px',
                  borderRadius: '50%',
                  backgroundColor: 'var(--danger-color)'
                }} />
                Messages
                <small style={{ color: 'var(--text-secondary)', fontWeight: 'normal' }}>
                  (Stored messages)
                </small>
              </>
            )}
          </h3>
          
          {/* Message count badge */}
          <div style={{
            padding: '0.4rem 0.8rem',
            borderRadius: '1rem',
            backgroundColor: 'var(--primary-color)',
            color: 'white',
            fontSize: '0.85rem',
            fontWeight: 'bold'
          }}>
            {filteredMessages.length} messages
          </div>
        </div>
        
        <div style={{ maxHeight: '600px', overflowY: 'auto' }}>
          {filteredMessages.length === 0 ? (
            <div style={{ color: 'var(--text-secondary)', textAlign: 'center', padding: '3rem' }}>
              <p style={{ fontSize: '3rem', marginBottom: '1rem' }}>📭</p>
              <p style={{ fontSize: '1.1rem', marginBottom: '0.5rem' }}>No messages yet</p>
              <p style={{ fontSize: '0.9rem' }}>
                {connectionStatus?.is_connected 
                  ? 'Messages will appear here in real-time when received from your monitored channels.'
                  : 'Connect Telegram and select channels to start receiving messages.'}
              </p>
            </div>
          ) : (
            filteredMessages.map(msg => renderMessageCard(msg))
          )}
        </div>
      </div>
    </>
  )

  const renderHistoryTab = () => (
    <div className="grid grid-2">
      <div className="card">
        <h2>📜 Fetch Historic Messages</h2>
        <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>
          Fetch past messages from Telegram chats and optionally save them to the database.
        </p>
        
        <div className="form-group">
          <label>Select Chat</label>
          <select
            value={selectedChatForHistory}
            onChange={(e) => setSelectedChatForHistory(e.target.value)}
          >
            <option value="">-- Select a chat --</option>
            {availableChats.map(chat => (
              <option key={chat.id} value={chat.id}>
                {chat.name} {chat.username ? `(@${chat.username})` : ''}
              </option>
            ))}
            {messageStats?.chats?.map(chat => (
              !availableChats.find(c => String(c.id) === chat.chat_id) && (
                <option key={chat.chat_id} value={chat.chat_id}>
                  {chat.chat_name} (from DB)
                </option>
              )
            ))}
          </select>
        </div>
        
        <div className="form-group">
          <label>Number of Messages</label>
          <input
            type="number"
            value={historyLimit}
            onChange={(e) => setHistoryLimit(Math.min(500, Math.max(1, parseInt(e.target.value) || 100)))}
            min="1"
            max="500"
          />
          <small style={{ color: 'var(--text-secondary)' }}>Maximum 500 messages</small>
        </div>
        
        <div className="form-group">
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={saveToDb}
              onChange={(e) => setSaveToDb(e.target.checked)}
            />
            Save to database (enables signal detection)
          </label>
        </div>
        
        <button
          onClick={fetchHistoricMessages}
          className="btn btn-primary"
          disabled={fetchingHistory || !selectedChatForHistory}
          style={{ width: '100%' }}
        >
          {fetchingHistory ? '⏳ Fetching...' : '📥 Fetch Messages'}
        </button>
      </div>
      
      <div className="card">
        <h2>Preview</h2>
        {!saveToDb && historyMessages.length > 0 ? (
          <div style={{ maxHeight: '500px', overflowY: 'auto' }}>
            {historyMessages.map(msg => renderMessageCard(msg, true))}
          </div>
        ) : (
          <p style={{ color: 'var(--text-secondary)', textAlign: 'center', padding: '2rem' }}>
            {saveToDb 
              ? 'Messages will be saved directly to database. Uncheck "Save to database" to preview first.'
              : 'Fetched messages will appear here for preview.'}
          </p>
        )}
      </div>
    </div>
  )

  const renderConfigTab = () => {
    // Determine current step
    const step1Complete = config.api_id && config.api_hash && config.phone_number
    const step2Complete = connectionStatus?.is_connected
    const step3Complete = connectionStatus?.monitored_chats_count > 0
    
    return (
      <div>
        {/* Setup Progress */}
        <div className="card" style={{ marginBottom: '1.5rem', borderLeft: '4px solid var(--primary-color)' }}>
          <h3 style={{ marginBottom: '1rem' }}>📋 Setup Progress</h3>
          <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
            <div style={{
              padding: '0.5rem 1rem',
              borderRadius: '0.5rem',
              backgroundColor: step1Complete ? 'rgba(16, 185, 129, 0.2)' : 'var(--bg-color)',
              border: `1px solid ${step1Complete ? 'var(--success-color)' : 'var(--border-color)'}`
            }}>
              {step1Complete ? '✅' : '1️⃣'} Enter API Credentials
            </div>
            <div style={{
              padding: '0.5rem 1rem',
              borderRadius: '0.5rem',
              backgroundColor: step2Complete ? 'rgba(16, 185, 129, 0.2)' : 'var(--bg-color)',
              border: `1px solid ${step2Complete ? 'var(--success-color)' : 'var(--border-color)'}`
            }}>
              {step2Complete ? '✅' : '2️⃣'} Verify Phone Number
            </div>
            <div style={{
              padding: '0.5rem 1rem',
              borderRadius: '0.5rem',
              backgroundColor: step3Complete ? 'rgba(16, 185, 129, 0.2)' : 'var(--bg-color)',
              border: `1px solid ${step3Complete ? 'var(--success-color)' : 'var(--border-color)'}`
            }}>
              {step3Complete ? '✅' : '3️⃣'} Select Channels
            </div>
          </div>
        </div>

        <div className="grid grid-2">
          <div className="card">
            <h2>🔧 Step 1 & 2: Telegram Credentials</h2>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '1rem', fontSize: '0.9rem' }}>
              Get your API credentials from <a href="https://my.telegram.org" target="_blank" rel="noopener noreferrer" style={{ color: 'var(--primary-color)' }}>my.telegram.org</a>
            </p>
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label>API ID</label>
                <input
                  type="text"
                  value={config.api_id}
                  onChange={(e) => setConfig({ ...config, api_id: e.target.value })}
                  placeholder="12345678"
                  required
                />
              </div>

              <div className="form-group">
                <label>API Hash</label>
                <input
                  type="password"
                  value={config.api_hash}
                  onChange={(e) => setConfig({ ...config, api_hash: e.target.value })}
                  placeholder="a1b2c3d4e5f6..."
                  required
                />
              </div>

              <div className="form-group">
                <label>Phone Number (International Format)</label>
                <input
                  type="text"
                  value={config.phone_number}
                  onChange={(e) => setConfig({ ...config, phone_number: e.target.value })}
                  placeholder="+911234567890"
                  required
                />
                <small style={{ color: 'var(--text-secondary)', display: 'block', marginTop: '0.25rem' }}>
                  Include country code (e.g., +91 for India)
                </small>
              </div>

              <button 
                type="submit" 
                className="btn btn-primary" 
                disabled={loading} 
                style={{ width: '100%' }}
              >
                {loading ? '⏳ Processing...' : connectionStatus?.is_connected ? '✅ Connected' : '🔗 Connect & Verify'}
              </button>
            </form>

            {needsVerification && (
              <form onSubmit={handleVerification} style={{ marginTop: '1.5rem', paddingTop: '1.5rem', borderTop: '1px solid var(--border-color)' }}>
                <div style={{ 
                  backgroundColor: 'rgba(37, 99, 235, 0.1)', 
                  padding: '1rem', 
                  borderRadius: '0.5rem',
                  marginBottom: '1rem'
                }}>
                  <strong>📱 Check your Telegram app!</strong>
                  <p style={{ margin: '0.5rem 0 0', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
                    A verification code has been sent to your Telegram account.
                  </p>
                </div>
                <div className="form-group">
                  <label>Verification Code</label>
                  <input
                    type="text"
                    value={verificationCode}
                    onChange={(e) => setVerificationCode(e.target.value)}
                    placeholder="12345"
                    required
                    style={{ fontSize: '1.5rem', textAlign: 'center', letterSpacing: '0.5rem' }}
                    maxLength={6}
                  />
                </div>
                <button type="submit" className="btn btn-success" disabled={loading} style={{ width: '100%' }}>
                  {loading ? '⏳ Verifying...' : '✓ Verify Code'}
                </button>
              </form>
            )}
          </div>

          <div className="card">
            <h2>📡 Step 3: Select Channels to Monitor</h2>
            {!connectionStatus?.is_connected ? (
              <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-secondary)' }}>
                <p style={{ fontSize: '3rem', marginBottom: '1rem' }}>🔒</p>
                <p>Complete Step 1 & 2 to see your Telegram channels</p>
              </div>
            ) : availableChats.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-secondary)' }}>
                <p style={{ fontSize: '3rem', marginBottom: '1rem' }}>📭</p>
                <p>No groups or channels found.</p>
                <p style={{ fontSize: '0.9rem', marginTop: '0.5rem' }}>
                  Make sure you've joined some Telegram groups or channels.
                </p>
                <button onClick={fetchChats} className="btn" style={{ marginTop: '1rem' }}>
                  🔄 Refresh Channels
                </button>
              </div>
            ) : (
              <>
                <p style={{ color: 'var(--text-secondary)', marginBottom: '1rem', fontSize: '0.9rem' }}>
                  Select the channels you want to monitor for trading signals. Click to toggle.
                </p>
                <div style={{ maxHeight: '300px', overflowY: 'auto', marginBottom: '1rem' }}>
                  {availableChats.map((chat) => (
                    <div
                      key={chat.id}
                      style={{
                        padding: '0.75rem 1rem',
                        marginBottom: '0.5rem',
                        backgroundColor: config.monitored_chats.includes(String(chat.id)) 
                          ? 'var(--primary-color)' 
                          : 'var(--bg-color)',
                        color: config.monitored_chats.includes(String(chat.id)) 
                          ? 'white' 
                          : 'var(--text-color)',
                        borderRadius: '0.5rem',
                        cursor: 'pointer',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        transition: 'all 0.2s'
                      }}
                      onClick={() => toggleChat(String(chat.id))}
                    >
                      <div>
                        <strong>{chat.name}</strong>
                        {chat.username && (
                          <small style={{ marginLeft: '0.5rem', opacity: 0.8 }}>
                            @{chat.username}
                          </small>
                        )}
                      </div>
                      {config.monitored_chats.includes(String(chat.id)) && (
                        <span>✓</span>
                      )}
                    </div>
                  ))}
                </div>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <button 
                    onClick={updateMonitoredChats} 
                    className="btn btn-primary" 
                    disabled={loading}
                    style={{ flex: 1 }}
                  >
                    💾 Save & Start Monitoring ({config.monitored_chats.length} selected)
                  </button>
                  <button onClick={fetchChats} className="btn" disabled={loading} title="Refresh channel list">
                    🔄
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    )
  }

  const renderTradeModal = () => {
    if (!showTradeModal || !selectedMessage) return null

    const parsedSignal = selectedMessage.parsed_signal 
      ? (typeof selectedMessage.parsed_signal === 'string' 
          ? JSON.parse(selectedMessage.parsed_signal) 
          : selectedMessage.parsed_signal)
      : null

    return (
      <div style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
        padding: '1rem'
      }}>
        <div style={{
          backgroundColor: 'var(--card-bg)',
          borderRadius: '1rem',
          width: '100%',
          maxWidth: '600px',
          maxHeight: '90vh',
          overflowY: 'auto',
          boxShadow: '0 20px 40px rgba(0, 0, 0, 0.4)'
        }}>
          {/* Modal Header */}
          <div style={{
            padding: '1.5rem',
            borderBottom: '1px solid var(--border-color)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center'
          }}>
            <h2 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              ⚡ Execute Trade
              {parsedSignal && (
                <span style={{
                  backgroundColor: parsedSignal.action === 'BUY' ? 'var(--success-color)' : 'var(--danger-color)',
                  color: 'white',
                  padding: '0.25rem 0.75rem',
                  borderRadius: '0.25rem',
                  fontSize: '0.9rem'
                }}>
                  {parsedSignal.action}
                </span>
              )}
            </h2>
            <button
              onClick={closeTradeModal}
              style={{
                background: 'none',
                border: 'none',
                color: 'var(--text-secondary)',
                fontSize: '1.5rem',
                cursor: 'pointer',
                padding: '0.5rem'
              }}
            >
              ✕
            </button>
          </div>

          {/* Broker Status Warning */}
          {brokerStatus && !brokerStatus.is_logged_in && (
            <div style={{
              margin: '1rem 1.5rem 0',
              padding: '1rem',
              backgroundColor: 'rgba(245, 158, 11, 0.2)',
              border: '1px solid var(--warning-color)',
              borderRadius: '0.5rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.75rem'
            }}>
              <span style={{ fontSize: '1.5rem' }}>⚠️</span>
              <div>
                <strong style={{ color: 'var(--warning-color)' }}>Broker Not Connected</strong>
                <p style={{ margin: '0.25rem 0 0', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
                  Trade will be created as pending. Connect to broker to execute.
                </p>
              </div>
            </div>
          )}

          {/* Original Message */}
          <div style={{
            margin: '1rem 1.5rem',
            padding: '1rem',
            backgroundColor: 'var(--bg-color)',
            borderRadius: '0.5rem',
            borderLeft: '4px solid var(--primary-color)'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
              <strong style={{ color: 'var(--primary-color)' }}>{selectedMessage.chat_name}</strong>
              <small style={{ color: 'var(--text-secondary)' }}>
                {new Date(selectedMessage.timestamp).toLocaleString()}
              </small>
            </div>
            <p style={{ 
              margin: 0, 
              fontSize: '0.9rem',
              maxHeight: '100px',
              overflow: 'auto',
              whiteSpace: 'pre-wrap'
            }}>
              {selectedMessage.message_text}
            </p>
          </div>

          {/* AI Interpretation */}
          {parsedSignal && (
            <div style={{
              margin: '0 1.5rem 1rem',
              padding: '1rem',
              backgroundColor: 'rgba(99, 102, 241, 0.1)',
              borderRadius: '0.5rem',
              border: '1px solid rgba(99, 102, 241, 0.3)'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
                <span style={{ fontSize: '1.2rem' }}>🤖</span>
                <strong style={{ color: 'var(--primary-color)' }}>AI Interpretation</strong>
                {parsedSignal.confidence && (
                  <span style={{
                    marginLeft: 'auto',
                    padding: '0.25rem 0.5rem',
                    borderRadius: '0.25rem',
                    fontSize: '0.85rem',
                    backgroundColor: parsedSignal.confidence > 0.85 ? 'rgba(34, 197, 94, 0.2)' : 'rgba(245, 158, 11, 0.2)',
                    color: parsedSignal.confidence > 0.85 ? 'var(--success-color)' : 'var(--warning-color)',
                    fontWeight: 'bold'
                  }}>
                    {(parsedSignal.confidence * 100).toFixed(0)}% confidence
                  </span>
                )}
              </div>
              
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '0.75rem', marginBottom: '0.75rem' }}>
                <div>
                  <small style={{ color: 'var(--text-secondary)', display: 'block' }}>Symbol</small>
                  <strong style={{ fontSize: '1.1rem' }}>{parsedSignal.symbol}</strong>
                </div>
                <div>
                  <small style={{ color: 'var(--text-secondary)', display: 'block' }}>Action</small>
                  <strong style={{ 
                    fontSize: '1.1rem',
                    color: parsedSignal.action === 'BUY' ? 'var(--success-color)' : 'var(--danger-color)'
                  }}>
                    {parsedSignal.action}
                  </strong>
                </div>
                {parsedSignal.entry_price && (
                  <div>
                    <small style={{ color: 'var(--text-secondary)', display: 'block' }}>Entry</small>
                    <strong>₹{parsedSignal.entry_price}</strong>
                  </div>
                )}
                {parsedSignal.target_price && (
                  <div>
                    <small style={{ color: 'var(--text-secondary)', display: 'block' }}>Target</small>
                    <strong style={{ color: 'var(--success-color)' }}>₹{parsedSignal.target_price}</strong>
                  </div>
                )}
                {parsedSignal.stop_loss && (
                  <div>
                    <small style={{ color: 'var(--text-secondary)', display: 'block' }}>Stop Loss</small>
                    <strong style={{ color: 'var(--danger-color)' }}>₹{parsedSignal.stop_loss}</strong>
                  </div>
                )}
              </div>
              
              {parsedSignal.reasoning && (
                <div style={{
                  marginTop: '0.75rem',
                  padding: '0.75rem',
                  backgroundColor: 'var(--bg-color)',
                  borderRadius: '0.375rem',
                  fontSize: '0.85rem',
                  fontStyle: 'italic',
                  color: 'var(--text-secondary)'
                }}>
                  <strong style={{ fontStyle: 'normal', color: 'var(--text-primary)' }}>AI Analysis:</strong> {parsedSignal.reasoning}
                </div>
              )}
            </div>
          )}

          {/* Trade Form */}
          <div style={{ padding: '0 1.5rem 1.5rem' }}>
            <div className="grid grid-2" style={{ gap: '1rem' }}>
              {/* Symbol */}
              <div className="form-group" style={{ margin: 0 }}>
                <label>Symbol</label>
                <input
                  type="text"
                  value={tradeForm.symbol}
                  onChange={(e) => setTradeForm({ ...tradeForm, symbol: e.target.value.toUpperCase() })}
                  style={{ fontWeight: 'bold', fontSize: '1.1rem' }}
                />
              </div>

              {/* Action */}
              <div className="form-group" style={{ margin: 0 }}>
                <label>Action</label>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <button
                    type="button"
                    onClick={() => setTradeForm({ ...tradeForm, action: 'BUY' })}
                    style={{
                      flex: 1,
                      padding: '0.75rem',
                      border: 'none',
                      borderRadius: '0.5rem',
                      cursor: 'pointer',
                      fontWeight: 'bold',
                      backgroundColor: tradeForm.action === 'BUY' ? 'var(--success-color)' : 'var(--bg-color)',
                      color: tradeForm.action === 'BUY' ? 'white' : 'var(--text-secondary)'
                    }}
                  >
                    BUY
                  </button>
                  <button
                    type="button"
                    onClick={() => setTradeForm({ ...tradeForm, action: 'SELL' })}
                    style={{
                      flex: 1,
                      padding: '0.75rem',
                      border: 'none',
                      borderRadius: '0.5rem',
                      cursor: 'pointer',
                      fontWeight: 'bold',
                      backgroundColor: tradeForm.action === 'SELL' ? 'var(--danger-color)' : 'var(--bg-color)',
                      color: tradeForm.action === 'SELL' ? 'white' : 'var(--text-secondary)'
                    }}
                  >
                    SELL
                  </button>
                </div>
              </div>

              {/* Quantity */}
              <div className="form-group" style={{ margin: 0 }}>
                <label>Quantity</label>
                <input
                  type="number"
                  value={tradeForm.quantity}
                  onChange={(e) => setTradeForm({ ...tradeForm, quantity: parseInt(e.target.value) || 1 })}
                  min="1"
                />
              </div>

              {/* Order Type */}
              <div className="form-group" style={{ margin: 0 }}>
                <label>Order Type</label>
                <select
                  value={tradeForm.order_type}
                  onChange={(e) => setTradeForm({ ...tradeForm, order_type: e.target.value })}
                >
                  <option value="MARKET">Market</option>
                  <option value="LIMIT">Limit</option>
                  <option value="SL">Stop Loss</option>
                  <option value="SL-M">Stop Loss Market</option>
                </select>
              </div>

              {/* Exchange */}
              <div className="form-group" style={{ margin: 0 }}>
                <label>Exchange</label>
                <select
                  value={tradeForm.exchange}
                  onChange={(e) => setTradeForm({ ...tradeForm, exchange: e.target.value })}
                >
                  <option value="NSE">NSE</option>
                  <option value="BSE">BSE</option>
                  <option value="NFO">NFO (F&O)</option>
                </select>
              </div>

              {/* Product Type */}
              <div className="form-group" style={{ margin: 0 }}>
                <label>Product Type</label>
                <select
                  value={tradeForm.product_type}
                  onChange={(e) => setTradeForm({ ...tradeForm, product_type: e.target.value })}
                >
                  <option value="INTRADAY">Intraday (MIS)</option>
                  <option value="DELIVERY">Delivery (CNC)</option>
                  <option value="CARRYFORWARD">Carryforward</option>
                </select>
              </div>

              {/* Entry Price */}
              <div className="form-group" style={{ margin: 0 }}>
                <label>Entry Price {tradeForm.order_type === 'MARKET' && '(Ignored for Market)'}</label>
                <input
                  type="number"
                  value={tradeForm.entry_price || ''}
                  onChange={(e) => setTradeForm({ ...tradeForm, entry_price: parseFloat(e.target.value) || null })}
                  placeholder="0.00"
                  step="0.05"
                  disabled={tradeForm.order_type === 'MARKET'}
                />
              </div>

              {/* Target Price */}
              <div className="form-group" style={{ margin: 0 }}>
                <label>Target Price</label>
                <input
                  type="number"
                  value={tradeForm.target_price || ''}
                  onChange={(e) => setTradeForm({ ...tradeForm, target_price: parseFloat(e.target.value) || null })}
                  placeholder="0.00"
                  step="0.05"
                  style={{ borderColor: tradeForm.target_price ? 'var(--success-color)' : undefined }}
                />
              </div>

              {/* Stop Loss */}
              <div className="form-group" style={{ margin: 0, gridColumn: '1 / -1' }}>
                <label>Stop Loss</label>
                <input
                  type="number"
                  value={tradeForm.stop_loss || ''}
                  onChange={(e) => setTradeForm({ ...tradeForm, stop_loss: parseFloat(e.target.value) || null })}
                  placeholder="0.00"
                  step="0.05"
                  style={{ borderColor: tradeForm.stop_loss ? 'var(--danger-color)' : undefined }}
                />
              </div>
            </div>

            {/* Trade Summary */}
            <div style={{
              marginTop: '1.5rem',
              padding: '1rem',
              backgroundColor: 'var(--bg-color)',
              borderRadius: '0.5rem'
            }}>
              <h4 style={{ margin: '0 0 0.75rem', color: 'var(--text-secondary)' }}>Trade Summary</h4>
              <div style={{ display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
                <div>
                  <strong style={{ fontSize: '1.2rem' }}>{tradeForm.symbol}</strong>
                  <span style={{ 
                    marginLeft: '0.5rem',
                    color: tradeForm.action === 'BUY' ? 'var(--success-color)' : 'var(--danger-color)'
                  }}>
                    {tradeForm.action} × {tradeForm.quantity}
                  </span>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                    {tradeForm.exchange} • {tradeForm.order_type} • {tradeForm.product_type}
                  </div>
                </div>
              </div>
            </div>

            {/* Result Message */}
            {tradeResult && (
              <div style={{
                marginTop: '1rem',
                padding: '1.25rem',
                borderRadius: '0.5rem',
                backgroundColor: tradeResult.status === 'executed' 
                  ? 'rgba(16, 185, 129, 0.2)' 
                  : tradeResult.status === 'error' || tradeResult.status === 'failed'
                    ? 'rgba(239, 68, 68, 0.2)'
                    : 'rgba(245, 158, 11, 0.2)',
                border: `2px solid ${
                  tradeResult.status === 'executed' 
                    ? 'var(--success-color)' 
                    : tradeResult.status === 'error' || tradeResult.status === 'failed'
                      ? 'var(--danger-color)'
                      : 'var(--warning-color)'
                }`
              }}>
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem' }}>
                  <span style={{ fontSize: '1.5rem' }}>
                    {tradeResult.status === 'executed' ? '✅' : 
                     tradeResult.status === 'error' || tradeResult.status === 'failed' ? '❌' : '⏳'}
                  </span>
                  <div style={{ flex: 1 }}>
                    <strong style={{ fontSize: '1.1rem', display: 'block', marginBottom: '0.5rem' }}>
                      {tradeResult.message}
                    </strong>
                    
                    {/* Trade Details */}
                    {tradeResult.trade && (
                      <div style={{ 
                        marginTop: '0.75rem',
                        padding: '0.75rem',
                        backgroundColor: 'var(--bg-color)',
                        borderRadius: '0.375rem',
                        fontSize: '0.9rem'
                      }}>
                        <div style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: '0.5rem' }}>
                          <span style={{ color: 'var(--text-secondary)' }}>Symbol:</span>
                          <strong>{tradeResult.trade.symbol}</strong>
                          
                          <span style={{ color: 'var(--text-secondary)' }}>Action:</span>
                          <strong style={{ 
                            color: tradeResult.trade.action === 'BUY' ? 'var(--success-color)' : 'var(--danger-color)'
                          }}>
                            {tradeResult.trade.action}
                          </strong>
                          
                          <span style={{ color: 'var(--text-secondary)' }}>Quantity:</span>
                          <span>{tradeResult.trade.quantity}</span>
                          
                          <span style={{ color: 'var(--text-secondary)' }}>Status:</span>
                          <span style={{
                            fontWeight: 'bold',
                            color: tradeResult.trade.status === 'EXECUTED' ? 'var(--success-color)' :
                                   tradeResult.trade.status === 'FAILED' ? 'var(--danger-color)' :
                                   'var(--warning-color)'
                          }}>
                            {tradeResult.trade.status}
                          </span>
                          
                          {tradeResult.trade_id && (
                            <>
                              <span style={{ color: 'var(--text-secondary)' }}>Trade ID:</span>
                              <span style={{ fontFamily: 'monospace' }}>{tradeResult.trade_id}</span>
                            </>
                          )}
                          
                          {tradeResult.order_id && (
                            <>
                              <span style={{ color: 'var(--text-secondary)' }}>Order ID:</span>
                              <span style={{ fontFamily: 'monospace' }}>{tradeResult.order_id}</span>
                            </>
                          )}
                          
                          {tradeResult.trade.error && (
                            <>
                              <span style={{ color: 'var(--danger-color)' }}>Error:</span>
                              <span style={{ color: 'var(--danger-color)' }}>{tradeResult.trade.error}</span>
                            </>
                          )}
                        </div>
                      </div>
                    )}
                    
                    {/* Show what AI interpreted if available */}
                    {tradeResult.parsed_signal && (
                      <div style={{ 
                        marginTop: '0.75rem',
                        fontSize: '0.85rem',
                        color: 'var(--text-secondary)',
                        fontStyle: 'italic'
                      }}>
                        ℹ️ Check backend logs for detailed AI interpretation and execution steps
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Action Buttons */}
            <div style={{ 
              display: 'flex', 
              gap: '1rem', 
              marginTop: '1.5rem' 
            }}>
              <button
                onClick={closeTradeModal}
                className="btn"
                style={{ 
                  flex: 1,
                  backgroundColor: 'var(--bg-color)'
                }}
                disabled={tradeLoading}
              >
                Cancel
              </button>
              <button
                onClick={executeTrade}
                className="btn"
                style={{
                  flex: 2,
                  backgroundColor: tradeForm.action === 'BUY' ? 'var(--success-color)' : 'var(--danger-color)',
                  color: 'white',
                  fontWeight: 'bold',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '0.5rem'
                }}
                disabled={tradeLoading || !tradeForm.symbol || tradeResult?.status === 'executed'}
              >
                {tradeLoading ? (
                  <>⏳ Processing...</>
                ) : tradeResult?.status === 'executed' ? (
                  <>✓ Executed</>
                ) : (
                  <>⚡ {tradeForm.action} {tradeForm.symbol}</>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div>
      {initialLoading ? (
        <div className="card" style={{ textAlign: 'center', padding: '3rem' }}>
          <div style={{
            width: '40px',
            height: '40px',
            border: '3px solid var(--border-color)',
            borderTopColor: 'var(--primary-color)',
            borderRadius: '50%',
            animation: 'spin 1s linear infinite',
            margin: '0 auto'
          }} />
          <p style={{ marginTop: '1rem', color: 'var(--text-secondary)' }}>Loading Telegram configuration...</p>
        </div>
      ) : (
        <>
          <div style={{ 
            display: 'flex', 
            justifyContent: 'space-between', 
            alignItems: 'center',
            marginBottom: '1.5rem',
            flexWrap: 'wrap',
            gap: '1rem'
          }}>
            <h1>📱 Telegram</h1>
            {renderConnectionBadge()}
          </div>

          {renderTabs()}

          {activeTab === 'messages' && renderMessagesTab()}
          {activeTab === 'history' && renderHistoryTab()}
          {activeTab === 'config' && renderConfigTab()}

          {/* Trade Execution Modal */}
          {renderTradeModal()}
        </>
      )}

      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
        
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
        
        .grid-4 {
          display: grid;
          grid-template-columns: repeat(4, 1fr);
          gap: 1rem;
        }
        
        @media (max-width: 1200px) {
          .grid-4 {
            grid-template-columns: repeat(2, 1fr);
          }
        }
        
        @media (max-width: 600px) {
          .grid-4 {
            grid-template-columns: 1fr;
          }
        }
      `}</style>
    </div>
  )
}

export default TelegramConfig

