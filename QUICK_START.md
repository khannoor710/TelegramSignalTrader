# 🎯 Quick Reference Card

## 🚀 Get Started in 3 Steps

```powershell
# 1. Setup (one time)
.\setup.ps1

# 2. Configure
notepad .env

# 3. Start
.\start.ps1
```

## 📍 Access Points

| Service | URL | Description |
|---------|-----|-------------|
| 🌐 Frontend | http://localhost:5173 | Web Interface |
| 🔧 Backend API | http://localhost:8000 | REST API |
| 📚 API Docs | http://localhost:8000/docs | Interactive Documentation |

## 🗂️ Project Layout

```
Telegram/
├── backend/      → Python FastAPI + Telegram + Broker
├── frontend/     → React UI
├── setup.ps1     → Install dependencies
├── start.ps1     → Run application
└── .env          → Your credentials
```

## 📄 Documentation Files

| File | Purpose |
|------|---------|
| `README.md` | Complete documentation |
| `SETUP_GUIDE.md` | Step-by-step setup |
| `PROJECT_SUMMARY.md` | What was built |
| `COMMANDS.md` | Command reference |

## 🔑 Required Credentials

### Telegram API
- Get from: https://my.telegram.org
- Need: `api_id`, `api_hash`, phone number

### Angel One
- Get from: Angel One dashboard → API
- Need: `api_key`, `client_id`, `password`
- Optional: `totp_secret` for 2FA

## ⚙️ Key Features

✅ Monitor Telegram groups  
✅ Parse trading signals  
✅ Execute on Angel One  
✅ Manual approval system  
✅ Real-time notifications  
✅ Trade history tracking  

## 🔧 Common Commands

```powershell
# Start
.\start.ps1

# Stop
Press any key in start.ps1 window

# Reset database
Remove-Item backend\trading_bot.db

# View logs
Check PowerShell windows
```

## 🆘 Troubleshooting

| Issue | Solution |
|-------|----------|
| Port in use | `netstat -ano \| findstr :8000` then `taskkill /PID <id> /F` |
| Module not found | `cd backend && pip install -r requirements.txt` |
| Node issues | `cd frontend && npm install` |

## 📞 Support

- 📖 Full docs: `README.md`
- 🚀 Setup guide: `SETUP_GUIDE.md`
- 💻 Commands: `COMMANDS.md`
- 🔧 API docs: http://localhost:8000/docs

---

**🎉 Ready to trade? Run `.\start.ps1`**
