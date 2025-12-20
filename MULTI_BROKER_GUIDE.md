# Multi-Broker Integration Guide

## Overview
The Telegram Trading Bot now supports multiple broker integrations simultaneously. You can configure and use different brokers (Angel One, Zerodha, Upstox, etc.) from a single dashboard.

## Architecture

### Core Components

1. **BrokerInterface** (`backend/app/services/broker_interface.py`)
   - Abstract base class defining broker operations
   - All brokers must implement 15 standard methods
   - Ensures consistent API across brokers

2. **BrokerRegistry** (`backend/app/services/broker_registry.py`)
   - Factory pattern for creating broker instances
   - Manages broker registration and caching
   - Handles active broker selection

3. **Broker Implementations**
   - `AngelOneBrokerService` - Angel One SmartAPI
   - `ZerodhaBrokerService` - Zerodha Kite Connect
   - Additional brokers can be added easily

### Database Schema Updates

**BrokerConfig Table:**
```sql
- id: Integer (Primary Key)
- broker_name: String (angel_one, zerodha, upstox, fyers) [INDEXED]
- api_key: String
- api_secret: String (nullable) - For Zerodha, Upstox
- client_id: String
- password_encrypted: String - Trading PIN/password (encrypted)
- totp_secret: String (nullable) - For Angel One TOTP (encrypted)
- is_active: Boolean
- last_login: DateTime
```

**Trade Table:**
```sql
- broker_type: String [INDEXED] - Tracks which broker executed the trade
```

**AppSettings Table:**
```sql
- active_broker_type: String - Currently active broker for new trades
```

## Supported Brokers

### 1. Angel One SmartAPI
**Required Credentials:**
- API Key: From SmartAPI developer portal
- Client ID: Your Angel One account ID
- PIN: 4-digit trading PIN
- TOTP Secret: From Google Authenticator setup

**Features:**
- Auto TOTP generation
- Instant login
- Full order management
- Symbol search with token mapping

### 2. Zerodha Kite Connect
**Required Credentials:**
- API Key: From Kite Connect developer console
- API Secret: From Kite Connect
- Client ID: Your Zerodha client ID (e.g., AB1234)
- Request Token: From OAuth redirect (manual login flow)

**Features:**
- OAuth-based authentication
- Positions, holdings, orders
- Margin information
- Symbol search

**Note:** Zerodha uses OAuth flow:
1. Get login URL from API
2. User logs in via browser
3. Get request token from redirect
4. Generate access token

### 3. Upstox (Coming Soon)
**Required Credentials:**
- API Key
- API Secret
- Client ID
- PIN

## API Endpoints

### Broker Management

#### List Available Brokers
```http
GET /api/broker/brokers
```
Response:
```json
{
  "brokers": ["angel_one", "zerodha", "upstox"],
  "default": "angel_one"
}
```

#### List Configured Brokers
```http
GET /api/broker/brokers/configured
```
Response:
```json
{
  "brokers": [
    {
      "id": 1,
      "broker_type": "angel_one",
      "client_id": "A123456",
      "is_active": true,
      "is_logged_in": true,
      "last_login": "2025-12-20T10:30:00"
    }
  ]
}
```

#### Get Active Broker
```http
GET /api/broker/brokers/active
```

#### Set Active Broker
```http
POST /api/broker/brokers/active?broker_type=zerodha
```

### Broker Configuration

#### Create/Update Broker Config
```http
POST /api/broker/config
Content-Type: application/json

{
  "broker_name": "angel_one",
  "api_key": "your_api_key",
  "client_id": "A123456",
  "pin": "1234",
  "totp_secret": "your_totp_secret"
}
```

For Zerodha:
```json
{
  "broker_name": "zerodha",
  "api_key": "your_api_key",
  "api_secret": "your_api_secret",
  "client_id": "AB1234",
  "pin": ""
}
```

#### Get Broker Configs
```http
GET /api/broker/config
GET /api/broker/config?broker_type=zerodha
```

### Broker-Specific Operations

#### Login to Specific Broker
```http
POST /api/broker/brokers/{broker_type}/login
```

#### Logout from Specific Broker
```http
POST /api/broker/brokers/{broker_type}/logout
```

#### Get Broker Status
```http
GET /api/broker/brokers/{broker_type}/status
```

## Frontend Integration

### Multi-Broker Configuration Page
Location: `/multi-broker`

Features:
- Dropdown to select broker type
- Dynamic form based on broker requirements
- List of configured brokers with status indicators
- One-click login/logout per broker
- Active broker selection
- Visual indicators for connection status

### Using the UI

1. **Add a New Broker:**
   - Select broker from dropdown
   - Fill in required credentials
   - Click "Save Configuration"

2. **Login to Broker:**
   - Click "Connect" on configured broker
   - For Zerodha: Follow OAuth flow in new window

3. **Set Active Broker:**
   - Click "Set Active" on desired broker
   - All new trades will use this broker

4. **Multiple Active Connections:**
   - You can be logged into multiple brokers simultaneously
   - Only one broker is "active" for new trades
   - Useful for comparing execution quality

## Adding a New Broker

### Step 1: Create Broker Service
```python
# backend/app/services/upstox_broker_service.py

from app.services.broker_interface import BrokerInterface

class UpstoxBrokerService(BrokerInterface):
    def __init__(self):
        self._is_logged_in = False
        self._client_id = None
    
    @property
    def is_logged_in(self) -> bool:
        return self._is_logged_in
    
    @property
    def client_id(self) -> Optional[str]:
        return self._client_id
    
    def login(self, api_key, client_id, password, totp_secret=None):
        # Implement Upstox login
        pass
    
    # Implement all 15 BrokerInterface methods
    ...
```

### Step 2: Register Broker
```python
# backend/main.py

from app.services.upstox_broker_service import UpstoxBrokerService

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Register brokers
    broker_registry.register("angel_one", AngelOneBrokerService)
    broker_registry.register("zerodha", ZerodhaBrokerService)
    broker_registry.register("upstox", UpstoxBrokerService)  # NEW
    
    yield
    ...
```

### Step 3: Add Frontend Config
```javascript
// frontend/src/pages/MultiBrokerConfig.jsx

const BROKER_CONFIGS = {
  upstox: {
    name: 'Upstox',
    fields: [
      { key: 'api_key', label: 'API Key', type: 'text', required: true },
      { key: 'api_secret', label: 'API Secret', type: 'password', required: true },
      { key: 'client_id', label: 'Client ID', type: 'text', required: true },
      { key: 'pin', label: 'PIN', type: 'password', required: true }
    ]
  },
  ...
}
```

### Step 4: Install Dependencies
```bash
# Add to requirements.txt
upstox-python-sdk>=1.0.0

# Install
pip install upstox-python-sdk
```

## Migration Guide

### From Single Broker to Multi-Broker

**Database Migration:**
```sql
-- Add new columns (already in models.py)
ALTER TABLE broker_config ADD COLUMN api_secret VARCHAR;
ALTER TABLE broker_config ADD COLUMN broker_name_index;
ALTER TABLE trades ADD COLUMN broker_type VARCHAR DEFAULT 'angel_one';
ALTER TABLE app_settings ADD COLUMN active_broker_type VARCHAR DEFAULT 'angel_one';

-- Create indexes
CREATE INDEX idx_broker_config_broker_name ON broker_config(broker_name);
CREATE INDEX idx_trades_broker_type ON trades(broker_type);
```

**Existing Code:**
```python
# OLD: Direct broker service import
from app.services.broker_service import broker_service

if broker_service.is_logged_in:
    broker_service.place_order(...)
```

**New Code:**
```python
# NEW: Use broker registry
from app.services.broker_registry import broker_registry

# Get active broker
broker = broker_registry.get_active_broker(db)
if broker and broker.is_logged_in:
    broker.place_order(...)

# Or get specific broker
zerodha = broker_registry.create_broker("zerodha")
zerodha.place_order(...)
```

## Best Practices

### 1. Credential Security
- All sensitive data encrypted using Fernet
- Environment variable for encryption key
- Never log decrypted credentials

### 2. Error Handling
```python
try:
    broker = broker_registry.create_broker("zerodha")
    result = broker.place_order(...)
except ValueError as e:
    # Broker not registered
    logger.error(f"Broker not available: {e}")
except Exception as e:
    # Order placement failed
    logger.error(f"Order failed: {e}")
```

### 3. Connection Management
- Use cached instances for performance
- Clear instances on shutdown
- Handle connection timeouts

### 4. Broker Selection
- Set default broker for automated trading
- Allow per-trade broker override
- Track broker performance metrics

## Testing

### Test Broker Registration
```python
from app.services.broker_registry import broker_registry
from app.services.broker_interface import BrokerInterface

# Check registration
assert broker_registry.is_registered("angel_one")
assert broker_registry.is_registered("zerodha")

# Get broker class
BrokerClass = broker_registry.get_broker_class("angel_one")
assert issubclass(BrokerClass, BrokerInterface)

# Create instance
broker = broker_registry.create_broker("angel_one")
assert isinstance(broker, BrokerInterface)
```

### Test Multi-Broker Login
```bash
# Terminal
curl -X POST http://localhost:8000/api/broker/config \
  -H "Content-Type: application/json" \
  -d '{
    "broker_name": "zerodha",
    "api_key": "test_key",
    "api_secret": "test_secret",
    "client_id": "AB1234",
    "pin": ""
  }'

curl -X POST http://localhost:8000/api/broker/brokers/zerodha/login
```

## Troubleshooting

### Issue: Broker not found
**Solution:** Ensure broker is registered in `main.py` lifespan function

### Issue: Login fails for Zerodha
**Cause:** Missing request token (OAuth flow)
**Solution:** 
1. Call login endpoint to get login URL
2. Complete OAuth in browser
3. Extract request_token from redirect URL
4. Update config with request_token as "pin"
5. Retry login

### Issue: Can't switch active broker
**Check:** 
- Broker is configured
- Broker is logged in
- AppSettings exists in database

## Performance Considerations

### Broker Instance Caching
- Singleton pattern per broker type
- Reduces initialization overhead
- Maintains login sessions

### Connection Pooling
- Reuse HTTP sessions
- Keep WebSocket connections alive
- Implement connection timeout handling

## Roadmap

### Phase 1: Core (✅ Complete)
- [x] Broker interface abstraction
- [x] Broker registry with factory pattern
- [x] Angel One implementation
- [x] Zerodha implementation
- [x] Multi-broker API endpoints
- [x] Frontend multi-broker UI

### Phase 2: Enhancement
- [ ] Upstox broker implementation
- [ ] Fyers broker implementation
- [ ] Per-trade broker selection in UI
- [ ] Broker performance comparison dashboard
- [ ] Automatic broker fallback on failure

### Phase 3: Advanced
- [ ] Smart order routing (choose best broker per trade)
- [ ] Broker-specific analytics
- [ ] Cost analysis (brokerage comparison)
- [ ] Multi-broker position aggregation

## Resources

### Documentation
- Angel One SmartAPI: https://smartapi.angelbroking.com/docs
- Zerodha Kite Connect: https://kite.trade/docs/connect/v3/
- Upstox API: https://upstox.com/developer/api-documentation/

### Support
- Issues: GitHub repository
- Community: Discord/Telegram group
- Email: support@yourdomain.com

---

**Last Updated:** December 20, 2025
**Version:** 2.0.0
