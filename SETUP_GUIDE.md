# 🚀 Quick Start Guide

## Prerequisites Installation

### 1. Install Python 3.11+
- Download from: https://www.python.org/downloads/
- During installation, check "Add Python to PATH"
- Verify: Open PowerShell and run `python --version`

### 2. Install Node.js 20+
- Download from: https://nodejs.org/
- Install LTS version
- Verify: Open PowerShell and run `node --version` and `npm --version`

## Application Setup

### Option 1: Automated Setup (Recommended)

1. **Open PowerShell in the project directory**:
```powershell
cd "e:\Trading\Telegram"
```

2. **Run setup script**:
```powershell
.\setup.ps1
```

This will:
- Check Python and Node.js installations
- Install all backend dependencies
- Install all frontend dependencies
- Create .env file from template

3. **Configure your credentials**:
- Edit `.env` file with your Telegram and Angel One credentials
- See "Getting Credentials" section below

4. **Start the application**:
```powershell
.\start.ps1
```

5. **Access the application**:
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

### Option 2: Manual Setup

#### Backend
```powershell
cd backend
python -m pip install -r requirements.txt --user
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend (in a new terminal)
```powershell
cd frontend
npm install
npm run dev
```

## Getting Credentials

### Telegram API Credentials

1. Visit https://my.telegram.org
2. Login with your phone number
3. Go to "API development tools"
4. Create a new application
5. Copy `api_id` and `api_hash`

### Angel One Broker Credentials

1. Login to your Angel One account
2. Go to API section in settings
3. Generate API Key
4. Note your Client ID
5. (Optional) Setup TOTP for 2FA:
   - Install Google Authenticator
   - Scan QR code
   - Save the secret key shown

## First Time Configuration

1. **Open the web application**: http://localhost:5173

2. **Configure Telegram**:
   - Go to "Telegram" page
   - Enter API ID, API Hash, Phone Number
   - Click "Save Configuration"
   - Enter verification code from Telegram
   - Select groups to monitor

3. **Configure Broker**:
   - Go to "Broker" page
   - Enter API Key, Client ID, Password
   - (Optional) Add TOTP secret
   - Click "Save Configuration"
   - Click "Login"

4. **Configure Settings**:
   - Go to "Settings" page
   - Enable/disable auto trading
   - Set manual approval requirement
   - Configure default quantity and risk

## Troubleshooting

### Backend won't start
- Ensure Python is installed: `python --version`
- Check if port 8000 is available
- Review backend terminal for error messages

### Frontend won't start
- Ensure Node.js is installed: `node --version`
- Check if port 5173 is available
- Try: `cd frontend && npm install`

### Telegram connection fails
- Verify API credentials are correct
- Ensure phone number includes country code (+91xxxxxxxxxx)
- Check internet connection

### Broker login fails
- Verify credentials in Angel One portal
- Check if API access is enabled
- Ensure TOTP token is correct

## Project Structure

```
e:\Trading\Telegram\
├── backend/              # Python FastAPI backend
│   ├── app/
│   │   ├── api/         # API routes
│   │   ├── services/    # Business logic
│   │   ├── models/      # Database models
│   │   └── core/        # Configuration
│   ├── main.py          # Entry point
│   └── requirements.txt
├── frontend/            # React frontend
│   ├── src/
│   │   ├── pages/      # UI pages
│   │   └── App.jsx
│   └── package.json
├── .env                 # Your credentials (create from .env.example)
├── setup.ps1           # Setup script
├── start.ps1           # Start script
└── README.md           # Full documentation
```

## Usage

1. **Monitor Signals**: Bot automatically monitors configured Telegram groups
2. **Review Trades**: Check Dashboard for new trading signals
3. **Approve/Reject**: In "Trades" page, approve or reject pending trades
4. **View History**: See all past trades and their status

## Signal Format Examples

The bot can parse various signal formats:

```
BUY RELIANCE @ 2500
Target: 2550
SL: 2480
```

```
SELL INFY
Entry: 1450
Target: 1420
Stop Loss: 1465
Qty: 10
```

## Support

- Full Documentation: See README.md
- API Documentation: http://localhost:8000/docs
- Issues: Check troubleshooting section

---

**Ready to trade? Run `.\start.ps1` to begin!** 🎯
