# Session Persistence Issues - Troubleshooting Guide

## Current Status
The database tables don't exist, which means the backend hasn't initialized properly.

## Steps to Fix

### 1. Start the Application Properly
```powershell
# From E:\Trading\Telegram directory
.\start.ps1
```

**IMPORTANT:** Don't press any key! Let the servers run. The script opens two windows:
- Backend window (Python/FastAPI)
- Frontend window (React/Vite)

### 2. Verify Backend is Running
Open browser to: http://localhost:8000/docs
You should see the FastAPI documentation.

### 3. Verify Frontend is Running  
Open browser to: http://localhost:5173
You should see the Trading Bot dashboard.

### 4. Complete Initial Setup

#### Telegram Setup:
1. Go to Telegram page
2. Enter API credentials (from my.telegram.org)
3. Click "Save & Initialize"
4. Enter verification code from Telegram app
5. Select channels to monitor
6. Click "Save & Update"

**Expected:** Session string should be saved in database

#### Broker Setup:
1. Go to Multi-Broker Config page (or Broker Config)
2. Enter Angel One credentials
3. Click "Save Configuration"
4. Click "Connect to Angel One"

**Expected:** Auth token should be saved in database

### 5. Test Session Persistence
```powershell
# Run the test script
python backend\test_session_persistence.py
```

**Expected Output:**
- ✅ Session string present for Telegram
- ✅ Auth token present for Broker

### 6. Test Restart
1. Close both backend and frontend windows (Ctrl+C)
2. Run `.\start.ps1` again
3. Check Dashboard - should show:
   - Telegram: Connected
   - Broker: Connected

**NO RE-AUTHENTICATION SHOULD BE NEEDED!**

## Debugging Tips

### If Telegram session is lost:
```powershell
# Check database
python -c "import sqlite3; c=sqlite3.connect('trading_bot.db').cursor(); c.execute('SELECT id, phone_number, LENGTH(session_string), monitored_chats FROM telegram_config'); print(c.fetchall())"
```

Look for:
- Multiple configs with same phone number → Old fix not applied
- NULL session_string → Verification not completed
- Different monitored_chats between configs → Config was recreated

**Fix:** The `/api/telegram/config` endpoint should UPDATE, not CREATE new configs.

### If Broker session is lost:
```powershell
# Check if migration ran
python backend\migrate_broker_session.py
```

Then check database:
```powershell
python -c "import sqlite3; c=sqlite3.connect('trading_bot.db').cursor(); c.execute('SELECT id, client_id, LENGTH(auth_token), session_expiry FROM broker_config'); print(c.fetchall())"
```

Look for:
- NULL auth_token → Login not completed or migration not run
- Past session_expiry → Session expired (login again)

### If Broker page shows nothing after connecting:
1. Open browser console (F12)
2. Look for errors in Console tab
3. Look for failed requests in Network tab

Common issues:
- 401/403 errors → Session expired, re-login
- 500 errors → Backend error, check backend terminal
- 404 errors → Backend not running or wrong URL

## Files Modified for Session Persistence

### Backend:
1. `backend/app/models/models.py` - Added session fields to BrokerConfig
2. `backend/app/services/broker_service.py` - Auto-restore on startup, save on login
3. `backend/app/api/telegram.py` - UPDATE instead of CREATE config
4. `backend/migrate_broker_session.py` - Database migration

### Frontend:
1. `frontend/src/pages/BrokerConfig.jsx` - Better error handling, Running Trades tab
2. `frontend/src/pages/Dashboard.jsx` - Already fetches broker status correctly

## Expected Behavior After Fix

### On First Run:
1. Complete Telegram setup → Session saved to DB
2. Complete Broker login → Auth token saved to DB

### On Subsequent Runs:
1. Backend starts → Restores Telegram session automatically
2. Backend starts → Restores Broker session automatically  
3. Dashboard shows both as connected
4. No re-authentication needed!

### When Updating Channels:
1. Change monitored channels in Telegram page
2. Click "Save & Update"
3. Session string PRESERVED (not deleted)
4. No re-verification needed

## If Nothing Works:

1. Delete database and start fresh:
```powershell
Remove-Item trading_bot.db -Force
python backend\migrate_broker_session.py  # Will say "not found" - that's OK
.\start.ps1
```

2. Complete full setup from scratch
3. Check session persistence with test script
4. Restart and verify no re-authentication needed
