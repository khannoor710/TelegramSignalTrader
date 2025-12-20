# 🔧 Development Commands Reference

## 🚀 Quick Start Commands

### First Time Setup
```powershell
# Run automated setup (installs dependencies, creates .env)
.\setup.ps1

# Edit credentials
notepad .env

# Start application
.\start.ps1
```

## 🔄 Development Workflow

### Start Development Servers

**Option 1: Using start script (recommended)**
```powershell
.\start.ps1
```

**Option 2: Manual start**
```powershell
# Terminal 1 - Backend
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 - Frontend
cd frontend
npm run dev
```

### Stop Servers
- Press any key when using `.\start.ps1`
- Or press `Ctrl+C` in each terminal

## 📦 Dependency Management

### Backend (Python)
```powershell
cd backend

# Install/Update all dependencies
pip install -r requirements.txt --user

# Add new dependency
pip install package-name
pip freeze > requirements.txt

# Create virtual environment (optional)
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### Frontend (Node.js)
```powershell
cd frontend

# Install dependencies
npm install

# Add new dependency
npm install package-name

# Update dependencies
npm update

# Remove dependency
npm uninstall package-name
```

## 🗄️ Database Commands

### Reset Database
```powershell
# Stop backend first, then:
Remove-Item backend\trading_bot.db
# Database will be recreated on next backend start
```

### View Database
```powershell
# Install SQLite browser
# Open: backend\trading_bot.db
```

## 🐳 Docker Commands

### Build and Run with Docker
```powershell
# Build and start containers
docker-compose up -d

# View logs
docker-compose logs -f

# Stop containers
docker-compose down

# Rebuild after code changes
docker-compose up -d --build
```

### Individual Container Commands
```powershell
# Backend only
docker-compose up backend

# Frontend only
docker-compose up frontend

# Remove all containers and volumes
docker-compose down -v
```

## 🧪 Testing & Debugging

### Check Backend Status
```powershell
# Health check
curl http://localhost:8000/health

# API Documentation
# Open: http://localhost:8000/docs
```

### Check Frontend Status
```powershell
# Open: http://localhost:5173
```

### View Logs
```powershell
# Backend logs (if using .\start.ps1)
# Check the backend PowerShell window

# Frontend logs (if using .\start.ps1)
# Check the frontend PowerShell window
```

## 🔍 Common Issues & Solutions

### Port Already in Use
```powershell
# Find process using port 8000 (backend)
netstat -ano | findstr :8000
# Kill process
taskkill /PID <process_id> /F

# Find process using port 5173 (frontend)
netstat -ano | findstr :5173
# Kill process
taskkill /PID <process_id> /F
```

### Python Module Not Found
```powershell
cd backend
pip install -r requirements.txt --user --force-reinstall
```

### Node Modules Issues
```powershell
cd frontend
Remove-Item -Recurse -Force node_modules
Remove-Item package-lock.json
npm install
```

### Clear Cache
```powershell
# Backend
cd backend
Remove-Item -Recurse -Force __pycache__

# Frontend
cd frontend
Remove-Item -Recurse -Force node_modules\.vite
npm run build
```

## 📝 Configuration Files

### Edit Environment Variables
```powershell
notepad .env
```

### Edit Backend Configuration
```powershell
notepad backend\main.py
```

### Edit Frontend Configuration
```powershell
notepad frontend\vite.config.js
```

## 🔐 Security

### Generate Encryption Key
```powershell
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### Update .env with new key
```powershell
notepad .env
# Update ENCRYPTION_KEY with generated key
```

## 📊 Monitoring

### Watch Backend Logs
```powershell
cd backend
Get-Content -Path ".\logs\app.log" -Wait
```

### Monitor Database Size
```powershell
Get-Item backend\trading_bot.db | Select-Object Name, Length
```

## 🔄 Update Project

### Pull Latest Changes (if using Git)
```powershell
git pull origin main
.\setup.ps1  # Reinstall dependencies
```

### Backup Data
```powershell
# Backup database
Copy-Item backend\trading_bot.db "backup_$(Get-Date -Format 'yyyyMMdd_HHmmss').db"

# Backup .env
Copy-Item .env .env.backup
```

## 🎯 Production Deployment

### Using Docker (Recommended)
```powershell
# Build production images
docker-compose -f docker-compose.yml build

# Start in production mode
docker-compose up -d

# Check status
docker-compose ps
```

### Manual Deployment
```powershell
# Backend
cd backend
pip install -r requirements.txt
gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# Frontend
cd frontend
npm run build
# Serve dist/ folder with nginx or similar
```

## 📞 Get Help

### Check API Documentation
```
http://localhost:8000/docs
```

### View Full Documentation
```powershell
notepad README.md
notepad SETUP_GUIDE.md
notepad PROJECT_SUMMARY.md
```

---

**Pro Tip**: Bookmark this file for quick reference! 📌
