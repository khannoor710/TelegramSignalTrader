# 📊 Telegram Trading Bot

A full-stack web application that reads trading calls from Telegram groups and automatically executes them on your Angel One broker account.

## 🌟 Features

- **Telegram Integration**: Monitor multiple Telegram groups/channels for trading signals
- **Smart Signal Parsing**: Automatically extracts trading information (symbol, action, price, target, stop loss)
- **Angel One Broker**: Seamless integration with Angel One SmartAPI for order execution
- **Manual Approval System**: Review and approve trades before execution
- **Real-time Updates**: WebSocket-based live notifications for new signals and trade execution
- **Trade History**: Complete audit trail of all trades with status tracking
- **Dashboard**: Monitor trading activity, positions, and system status
- **Auto-Trading**: Optional automatic trade execution with configurable risk management

## 🏗️ Architecture

```
telegram-trading-bot/
├── backend/                 # Python FastAPI backend
│   ├── app/
│   │   ├── api/            # API endpoints
│   │   ├── core/           # Database configuration
│   │   ├── models/         # SQLAlchemy models
│   │   ├── schemas/        # Pydantic schemas
│   │   └── services/       # Business logic
│   ├── main.py             # Application entry point
│   ├── requirements.txt    # Python dependencies
│   └── Dockerfile          # Backend container
├── frontend/               # React + Vite frontend
│   ├── src/
│   │   ├── pages/         # Page components
│   │   ├── App.jsx        # Main app component
│   │   └── main.jsx       # Entry point
│   ├── package.json       # Node dependencies
│   └── Dockerfile         # Frontend container
├── .env.example           # Environment variables template
├── docker-compose.yml     # Docker orchestration
└── README.md             # This file
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20+
- Telegram API credentials (from https://my.telegram.org)
- Angel One broker account with API access

### Option 1: Docker (Recommended)

1. **Clone and setup environment**:
```powershell
cd "e:\Trading\Telegram"
Copy-Item .env.example .env
# Edit .env with your credentials
```

2. **Start the application**:
```powershell
docker-compose up -d
```

3. **Access the application**:
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Option 2: Manual Setup

#### Backend Setup

1. **Create virtual environment**:
```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
```

2. **Install dependencies**:
```powershell
pip install -r requirements.txt
```

3. **Run the backend**:
```powershell
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend Setup

1. **Install dependencies**:
```powershell
cd frontend
npm install
```

2. **Run the frontend**:
```powershell
npm run dev
```

## ⚙️ Configuration

### 1. Telegram Setup

1. Get your Telegram API credentials:
   - Visit https://my.telegram.org
   - Login with your phone number
   - Go to "API development tools"
   - Create a new application
   - Note down `api_id` and `api_hash`

2. In the web app:
   - Navigate to "Telegram" page
   - Enter API ID, API Hash, and Phone Number
   - Click "Save Configuration"
   - Enter the verification code sent to your phone
   - Select Telegram groups to monitor

### 2. Angel One Broker Setup

1. Get Angel One API credentials:
   - Login to Angel One
   - Go to API section
   - Generate API Key and get Client ID
   - Optional: Setup TOTP for 2FA

2. In the web app:
   - Navigate to "Broker" page
   - Enter API Key, Client ID, Password
   - Optional: Add TOTP secret
   - Click "Save Configuration"
   - Click "Login" to connect

### 3. Trading Settings

Navigate to "Settings" page and configure:
- **Auto Trading**: Enable/disable automatic trade execution
- **Manual Approval**: Require manual approval before execution
- **Default Quantity**: Default lot size for trades
- **Max Trades Per Day**: Safety limit
- **Risk Percentage**: Risk per trade

## 📱 Usage

### Signal Format

The bot can parse trading signals in various formats:

```
BUY RELIANCE @ 2500
Target: 2550
SL: 2480
Qty: 10
```

```
SELL INFY
Price: 1450
Target 1: 1420
Stop Loss: 1465
```

### Workflow

1. **Monitoring**: Bot monitors configured Telegram groups
2. **Parsing**: Automatically extracts trading signals
3. **Notification**: Real-time notification of new signals
4. **Approval**: (If enabled) Review and approve/reject trades
5. **Execution**: Place orders on Angel One
6. **Tracking**: Monitor execution status and positions

## 🛠️ API Endpoints

### Telegram
- `POST /api/telegram/config` - Configure Telegram
- `POST /api/telegram/initialize` - Initialize client
- `POST /api/telegram/verify-code` - Verify phone code
- `GET /api/telegram/chats` - Get available chats
- `GET /api/telegram/messages` - Get messages

### Broker
- `POST /api/broker/config` - Configure broker
- `POST /api/broker/login` - Login to broker
- `GET /api/broker/status` - Get connection status
- `GET /api/broker/positions` - Get current positions

### Trades
- `POST /api/trades` - Create trade
- `GET /api/trades` - Get all trades
- `POST /api/trades/approve` - Approve/reject trade
- `POST /api/trades/{id}/execute` - Execute trade
- `GET /api/trades/stats/summary` - Get statistics

### Settings
- `GET /api/config/settings` - Get settings
- `POST /api/config/settings` - Update settings

## 🔒 Security

- Passwords are encrypted using Fernet symmetric encryption
- API keys stored securely in database
- CORS configured for frontend access only
- Session-based Telegram authentication
- TOTP support for broker 2FA

## 📊 Database Schema

The application uses SQLite with the following tables:
- `telegram_messages` - Raw Telegram messages
- `telegram_config` - Telegram configuration
- `trades` - Trade records
- `broker_config` - Broker credentials
- `app_settings` - Application settings

## 🐛 Troubleshooting

### Telegram Connection Issues
- Verify API credentials are correct
- Ensure phone number includes country code (+1234567890)
- Check if Telegram account has 2FA enabled

### Broker Connection Issues
- Verify Angel One credentials
- Check if API access is enabled in your account
- Ensure TOTP secret is correct (if using 2FA)

### Trade Execution Failures
- Verify broker is logged in
- Check if you have sufficient balance
- Verify symbol format (use NSE symbols)
- Check market hours

## 🔄 Updates & Maintenance

### Update Dependencies

Backend:
```powershell
cd backend
pip install --upgrade -r requirements.txt
```

Frontend:
```powershell
cd frontend
npm update
```

### Database Migrations

The application automatically creates database tables on first run. To reset:
```powershell
Remove-Item backend/trading_bot.db
# Restart the backend
```

## 📈 Future Enhancements

- [ ] Multi-broker support (Zerodha, Upstox, etc.)
- [ ] Advanced signal parsing with ML
- [ ] Backtesting capabilities
- [ ] Portfolio analytics
- [ ] Mobile app
- [ ] Alert system (Email, SMS)
- [ ] Paper trading mode
- [ ] Strategy builder

## 🚂 Railway Deployment

You can deploy both backend and frontend to Railway as separate services:

### 1. Backend (FastAPI)
- Service root: `backend/`
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Set environment variables in Railway dashboard (copy from `.env.example`)
- SQLite is supported for small projects, but for production use Railway Postgres and update `DATABASE_URL` accordingly.

### 2. Frontend (React + Vite)
- Service root: `frontend/`
- Build command: `npm install && npm run build`
- Start command: `npm run preview -- --host --port $PORT`
- Set any frontend environment variables as needed (e.g., API base URL)

### 3. Multi-Service Setup
- Use the provided `railway.json` for multi-service deployment.
- Each service can be deployed and scaled independently.

### 4. General Steps
1. Push your code to GitHub.
2. Create a new Railway project and link your repo.
3. Add two services: one for `backend/`, one for `frontend/`.
4. Set environment variables for each service.
5. Deploy!

### 🚀 Using Railway Postgres (Production)
- In Railway, add a Postgres plugin to your project.
- Set the `DATABASE_URL` environment variable in the backend service to the value provided by Railway (format: `postgresql+psycopg2://postgres:<password>@<host>:<port>/<db>`).
- The backend will automatically use Postgres if `DATABASE_URL` is set to a Postgres URI.
- No code changes needed—SQLAlchemy handles both SQLite and Postgres.

See [Railway Docs](https://docs.railway.app/) for more details.

## 📝 License

This project is for educational purposes. Use at your own risk. Trading involves financial risk.

## ⚠️ Disclaimer

This software is provided "as is" without warranty of any kind. The authors are not responsible for any trading losses. Always review trades before execution and use appropriate risk management.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## 📞 Support

For issues and questions:
1. Check the troubleshooting section
2. Review API documentation at http://localhost:8000/docs
3. Open an issue on GitHub

## 🙏 Acknowledgments

- FastAPI - Modern Python web framework
- React - Frontend library
- Telethon - Telegram client library
- Angel One SmartAPI - Broker API

---

**Built with ❤️ for traders**
