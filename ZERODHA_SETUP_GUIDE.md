# Zerodha Kite Connect Setup Guide

## Overview
Zerodha uses OAuth-based authentication which requires a different login flow compared to Angel One. This guide will walk you through the complete setup process **using the web interface**.

## Prerequisites
1. Active Zerodha trading account
2. Kite Connect API access (requires ₹2000/month subscription)
3. API Key and API Secret from Kite Connect developer console

## Step 1: Get Kite Connect API Access

1. Visit [Kite Connect](https://kite.trade/)
2. Subscribe to Kite Connect API (₹2000/month)
3. Create a new app in the [developer console](https://developers.kite.trade/apps)
4. **IMPORTANT:** Configure your app settings:
   - **App name**: Choose any name (e.g., "Telegram Trading Bot")
   - **Redirect URL**: `http://localhost:5173/zerodha-callback.html` ⚠️ **UPDATE YOUR KITE APP WITH THIS URL**
   - **Postback URL**: (optional, can be any valid URL)
   - **Status**: Active
5. Note down your:
   - **API Key** (24-character alphanumeric)
   - **API Secret** (32-character alphanumeric)
   - **Client ID** (Your Zerodha user ID, e.g., AB1234)

## Step 2: Configure via Web Interface

1. **Open the application**: http://localhost:5173
2. **Navigate** to **Multi-Broker Configuration** page
3. **Select Zerodha** from the broker cards
4. **Fill in the configuration form**:
   - **API Key**: Paste your Kite Connect API key
   - **API Secret**: Paste your Kite Connect API secret  
   - **Client ID**: Enter your Zerodha client ID (e.g., VT6072)
5. **Click "Save Zerodha Config"**
6. You'll see a warning note about the redirect URL - make sure it matches!

## Step 3: Connect via OAuth Flow (UI)

After saving the configuration:

1. **Click the "🔌 Connect" button** next to Zerodha in the configured brokers list
2. **A browser window will open** with Zerodha login page
3. **Complete the login**:
   - Enter your Zerodha User ID
   - Enter your Password
   - Enter your PIN
4. **Authorize the app** when prompted
5. **Auto-redirect to success page**: You'll see a green success page with your token
6. **Choose completion method**:
   - **🚀 Automatic (Recommended)**: Click "⚡ Auto-Complete Login" button
     - System automatically completes the login
     - Redirects you back to the app
     - Status shows "Connected" ✅
   - **📋 Manual (Fallback)**: Click "📋 Copy Token" button
     - Token is copied to clipboard
     - Paste into the app prompt
     - Click OK to complete

That's it! Your Zerodha account is now connected and the trading dashboard will display your holdings and funds.
   ```
   http://127.0.0.1/?request_token=XXXXXXXXXXXXXXX&action=login&status=success
   ```
6. **A prompt will appear** with detailed instructions
7. **Copy the request_token value** from the URL:
   - Look for `request_token=` in the address bar
   - Copy ONLY the token value (the random string after `=`)
   - Example: If URL is `http://127.0.0.1/?request_token=abc123xyz&action=login`
   - Copy only: `abc123xyz`
8. **Paste the token** into the prompt and click OK
9. **Success!** You should see "✅ Successfully connected to Zerodha!"
10. The status indicator will turn **green** and show "Connected"

## How It Works

### OAuth Flow
```
1. App requests login URL from Kite Connect API
   ↓
2. User visits login URL in browser
   ↓
3. User logs in and authorizes app
   ↓
4. Zerodha redirects with request_token
   ↓
5. App exchanges request_token + api_secret for access_token
   ↓
6. Access token is stored (encrypted) for future use
```

### API Endpoints
- `GET /broker/zerodha/login-url` - Get OAuth login URL
- `POST /broker/zerodha/complete-login?request_token=XXX` - Complete login with token

## Session Persistence

Once you've successfully logged in once:
- The access token is stored securely (encrypted)
- Future logins will attempt to reuse the stored token
- If the token expires, you'll need to repeat the OAuth flow

## Troubleshooting

### "kiteconnect not installed" Error
**Solution**: The required Python package is missing. Run:
```powershell
.\setup.ps1
```
Or manually install:
```powershell
E:/Trading/Telegram/.venv/Scripts/python.exe -m pip install kiteconnect
```

### "Please complete login via browser" Message
**Solution**: This is NOT an error! It's the expected first step:
1. The message includes a `login_url`
2. Visit that URL in your browser
3. Complete the authorization
4. Copy the `request_token` from the redirect URL
5. Provide it to complete login

### Invalid Request Token
**Causes**:
- Request token expired (they're valid for ~5 minutes)
- Wrong token copied
- Already used token (can only be used once)

**Solution**: Start the OAuth flow again to get a new request token

### API Key/Secret Issues
**Check**:
- API Key and Secret are from the same Kite Connect app
- API Key format: 24-character alphanumeric string
- API Secret format: 32-character alphanumeric string
- Redirect URL in Kite Connect app is set to `http://127.0.0.1`

### Access Token Expired
Zerodha access tokens expire after a certain period. When this happens:
1. You'll get authentication errors
2. Simply repeat the OAuth login flow
3. New access token will be stored

## Differences from Angel One

| Feature | Angel One | Zerodha |
|---------|-----------|---------|
| Auth Method | PIN + TOTP | OAuth (browser-based) |
| Login Flow | Direct API call | 3-step OAuth |
| Session Duration | Until market close | Token-based expiry |
| Auto-login | ✅ Yes (with TOTP) | ❌ Requires manual OAuth |
| Setup Complexity | Easy | Moderate |

## API Reference

### Zerodha Login URL
```bash
GET http://localhost:8000/broker/zerodha/login-url
```

Response:
```json
{
  "status": "success",
  "login_url": "https://kite.zerodha.com/connect/login?api_key=your_api_key",
  "message": "Visit this URL to authorize the app"
}
```

### Complete Login
```bash
POST http://localhost:8000/broker/zerodha/complete-login?request_token=XXX
```

Response:
```json
{
  "status": "success",
  "message": "Successfully logged in to Zerodha!",
  "access_token": "stored"
}
```

## Next Steps

Once connected:
1. Set Zerodha as active broker if needed: Click "Set as Active"
2. View your positions, holdings, and funds in the dashboard
3. Signal parser will now execute trades on Zerodha
4. Monitor trades in the Trade History section

## Support

For issues:
1. Check [Kite Connect API docs](https://kite.trade/docs/connect/v3/)
2. Verify your Kite Connect subscription is active
3. Check backend logs for detailed error messages
4. Ensure all required packages are installed

---

**Note**: Zerodha Kite Connect requires an active API subscription (₹2000/month). Make sure your subscription is active before attempting to connect.
