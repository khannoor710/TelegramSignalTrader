# 🐳 Docker Beginner's Guide - Telegram Trading Bot

**Complete step-by-step guide for someone who has never used Docker before**

---

## 📚 Table of Contents

1. [What is Docker?](#what-is-docker)
2. [Why Use Docker?](#why-use-docker)
3. [Installing Docker](#installing-docker)
4. [Running the Project](#running-the-project)
5. [Accessing the Application](#accessing-the-application)
6. [Managing Your Containers](#managing-your-containers)
7. [Troubleshooting](#troubleshooting)
8. [Next Steps](#next-steps)

---

## 🤔 What is Docker?

Docker is like a **virtual shipping container** for software. Just as shipping containers allow goods to be transported anywhere in the world regardless of what's inside, Docker containers allow applications to run anywhere - on your computer, a server, or the cloud - without worrying about different operating systems or installed software.

**In simple terms:**
- You don't need to install Python, Node.js, or any dependencies manually
- Everything runs in isolated "containers" that have everything they need
- It works the same way on Windows, Mac, or Linux
- Easy to start, stop, and remove without leaving traces on your computer

---

## 💡 Why Use Docker?

For this project, Docker means:

✅ **No Complex Setup**: No need to install Python 3.11, Node.js 20, or dozens of libraries  
✅ **Works Instantly**: Just install Docker and run one command  
✅ **Clean System**: All files stay in containers, easy to remove completely  
✅ **No Conflicts**: Won't interfere with other Python or Node.js projects  
✅ **Same Experience**: Works identically on Windows, Mac, and Linux  

---

## 🔧 Installing Docker

### For Windows Users

#### Step 1: Check System Requirements

You need:
- **Windows 10/11** (64-bit) - Pro, Enterprise, or Education editions recommended
- **4GB RAM minimum** (8GB recommended)
- **Virtualization enabled** in BIOS (usually enabled by default on modern PCs)

#### Step 2: Download Docker Desktop

1. Go to: https://www.docker.com/products/docker-desktop/
2. Click **"Download for Windows"**
3. Wait for the installer to download (~500MB)

#### Step 3: Install Docker Desktop

1. **Run the installer** (double-click `Docker Desktop Installer.exe`)
2. Follow the installation wizard:
   - ✅ Check "Use WSL 2 instead of Hyper-V" (recommended)
   - ✅ Click "OK" to proceed
3. Click **"Close and restart"** when installation completes
4. Your computer will restart

#### Step 4: Start Docker Desktop

1. After restart, Docker Desktop will start automatically
2. You'll see a **whale icon** in your system tray (bottom-right)
3. Wait for Docker to finish starting (icon will stop animating)
4. Accept the Docker Subscription Service Agreement if prompted

#### Step 5: Verify Installation

1. Open **PowerShell**:
   - Press `Windows Key + X`
   - Select "Windows PowerShell" or "Terminal"

2. Type this command and press Enter:
   ```powershell
   docker --version
   ```

3. You should see something like:
   ```
   Docker version 27.1.1, build 6312585
   ```

4. Check Docker Compose (comes with Docker Desktop):
   ```powershell
   docker compose version
   ```

5. You should see:
   ```
   Docker Compose version v2.29.1
   ```

✅ **If you see version numbers, Docker is installed correctly!**

---

### For Mac Users

1. Go to: https://www.docker.com/products/docker-desktop/
2. Download **Docker Desktop for Mac** (Intel or Apple Silicon)
3. Open the `.dmg` file
4. Drag Docker to your Applications folder
5. Open Docker from Applications
6. Wait for Docker to start
7. Open Terminal and verify: `docker --version`

---

### For Linux Users

#### Ubuntu/Debian:
```bash
# Update package index
sudo apt-get update

# Install Docker
sudo apt-get install docker.io docker-compose-plugin

# Start Docker service
sudo systemctl start docker
sudo systemctl enable docker

# Add your user to docker group (to run without sudo)
sudo usermod -aG docker $USER

# Log out and back in, then verify
docker --version
```

---

## 🚀 Running the Project

Now that Docker is installed, let's run the Telegram Trading Bot!

### Step 1: Open Project Folder

1. Open **File Explorer**
2. Navigate to: `C:\Personal\TelegramSignalTrader`
3. Right-click in the folder (not on a file)
4. Select **"Open in Terminal"** or **"Open PowerShell window here"**

**Alternative:**
```powershell
# In PowerShell, navigate to the project folder:
cd C:\Personal\TelegramSignalTrader
```

### Step 2: Verify You're in the Right Folder

```powershell
# Check current location
pwd
```

You should see:
```
Path
----
C:\Personal\TelegramSignalTrader
```

### Step 3: Check Docker is Running

Look for the **Docker whale icon** in your system tray. If it's not there:
1. Search for "Docker Desktop" in Start Menu
2. Click to open it
3. Wait for it to start (30-60 seconds)

### Step 4: Start the Application

Run this single command:

```powershell
docker compose up -d
```

**What this does:**
- `docker compose` = Use Docker to manage multiple containers
- `up` = Start the application
- `-d` = Run in background (detached mode)

**First time running?** This will:
- Download required images (Python, Node.js) - takes 2-5 minutes
- Build the application containers
- Start both backend and frontend services

You'll see output like:
```
[+] Running 3/3
 ✔ Network telegram-trading-network     Created
 ✔ Container telegram-trading-backend   Healthy
 ✔ Container telegram-trading-frontend  Started
```

✅ **When you see "Healthy" and "Started" - you're done!**

### Step 5: Verify Containers are Running

```powershell
docker compose ps
```

You should see:
```
NAME                        STATUS
telegram-trading-backend    Up (healthy)
telegram-trading-frontend   Up
```

---

## 🌐 Accessing the Application

### Open Your Web Browser

Once containers are running, open these URLs:

| What | URL | Description |
|------|-----|-------------|
| **Main Dashboard** | http://localhost:5173 | Trading bot interface |
| **Backend API** | http://localhost:8000 | API server |
| **API Documentation** | http://localhost:8000/docs | Interactive API docs |

### What You'll See

1. **First Visit**: Dashboard will open (may show "Connecting..." briefly)
2. **Settings Page**: Configure Telegram and Broker credentials
3. **Dashboard**: Monitor trading signals and executed trades

---

## 🎮 Managing Your Containers

### View Logs (See What's Happening)

**All services:**
```powershell
docker compose logs -f
```
Press `Ctrl + C` to stop viewing logs

**Backend only:**
```powershell
docker compose logs -f backend
```

**Frontend only:**
```powershell
docker compose logs -f frontend
```

### Stop the Application

**Method 1: Stop and keep containers**
```powershell
docker compose stop
```
Containers are stopped but preserved. Use `docker compose start` to resume.

**Method 2: Stop and remove containers**
```powershell
docker compose down
```
Containers are stopped and deleted. Your data (database, sessions) is preserved.

### Start the Application Again

```powershell
docker compose up -d
```

### Restart the Application

```powershell
docker compose restart
```

### Rebuild After Code Changes

If you modify code:
```powershell
docker compose up -d --build
```

### Check Container Status

```powershell
docker compose ps
```

### Remove Everything (Clean Slate)

**⚠️ WARNING: This deletes your database and all data!**

```powershell
# Stop and remove containers, networks, and volumes
docker compose down -v

# Optional: Remove Docker images to free space
docker image prune -a
```

---

## 🐛 Troubleshooting

### Problem: "docker: command not found"

**Solution:**
1. Docker Desktop is not running - open it from Start Menu
2. Restart your terminal/PowerShell window
3. Reinstall Docker Desktop

### Problem: "Cannot connect to the Docker daemon"

**Solution:**
1. Open Docker Desktop from Start Menu
2. Wait 30-60 seconds for it to start
3. Look for whale icon in system tray
4. Try the command again

### Problem: "Port 8000 or 5173 already in use"

**Solution:**
```powershell
# Find what's using the port
netstat -ano | findstr :8000
netstat -ano | findstr :5173

# Stop other instances
docker compose down

# Or kill the process (replace PID with actual number)
taskkill /PID <PID> /F
```

### Problem: Container shows "Unhealthy" status

**Solution:**
```powershell
# Check logs for errors
docker compose logs backend

# Restart the service
docker compose restart backend

# If persists, rebuild
docker compose up -d --build
```

### Problem: Frontend shows "Cannot connect to backend"

**Solution:**
1. Check backend is running: `docker compose ps`
2. Verify health: `curl http://localhost:8000/health`
3. Check logs: `docker compose logs backend`
4. Restart: `docker compose restart`

### Problem: "No space left on device"

**Solution:**
```powershell
# Clean up unused Docker resources
docker system prune -a

# Remove old images
docker image prune -a

# Remove unused volumes (⚠️ careful with data)
docker volume prune
```

### Problem: Changes to code not reflecting

**Solution:**
```powershell
# Rebuild containers
docker compose down
docker compose up -d --build
```

### Problem: Application very slow on Windows

**Solution:**
1. Ensure Docker Desktop is using **WSL 2** (not Hyper-V)
2. Open Docker Desktop → Settings → General
3. Check "Use WSL 2 based engine"
4. Apply & Restart

---

## 🎯 Next Steps

### 1. Configure Your Application

The application is running, but you need to configure it:

#### A. Configure Telegram API

1. Go to https://my.telegram.org
2. Log in with your phone number
3. Go to **"API development tools"**
4. Create a new application
5. Copy your `api_id` and `api_hash`

#### B. Edit Configuration File

1. Open [.env](.env) file in Notepad or any text editor
2. Update these values:
   ```env
   TELEGRAM_API_ID=your_actual_api_id
   TELEGRAM_API_HASH=your_actual_api_hash
   TELEGRAM_PHONE_NUMBER=+1234567890
   ```
3. Save the file

#### C. Restart to Apply Changes

```powershell
docker compose restart
```

#### D. Configure Through Web UI

1. Open http://localhost:5173
2. Go to **Settings** → **Telegram Configuration**
3. Enter your credentials
4. Complete phone verification
5. Select Telegram groups to monitor

### 2. Add Broker Integration (Optional)

1. Go to **Settings** → **Broker Configuration**
2. Choose your broker (Angel One, Zerodha, or Shoonya)
3. Enter API credentials
4. Test connection
5. Enable auto-trading or manual approval mode

### 3. Test Signal Detection

1. Go to **Settings** → **Signal Tester**
2. Paste a sample trading message
3. See how the AI parses it
4. Adjust parsing settings if needed

### 4. Monitor Trading

1. **Dashboard**: View active signals and trades
2. **Trade History**: See all executed trades
3. **Logs**: Monitor system activity

---

## 📖 Understanding Docker Commands

Here's what common commands do:

```powershell
# Start everything
docker compose up -d
# → Starts all services in background

# Stop everything
docker compose down
# → Stops and removes containers

# View running containers
docker compose ps
# → Shows status of all containers

# View logs
docker compose logs -f
# → Shows real-time logs (Ctrl+C to exit)

# Restart a service
docker compose restart backend
# → Restarts only the backend container

# Rebuild containers
docker compose up -d --build
# → Rebuilds images and restarts

# Execute command in container
docker compose exec backend bash
# → Opens shell inside backend container

# Remove all data
docker compose down -v
# → Stops containers and deletes volumes (data)
```

---

## 🔐 Security Best Practices

1. **Never commit `.env` file** to version control
2. **Use strong encryption key** (already generated)
3. **Keep API credentials secure**
4. **Enable manual approval** for trades initially
5. **Test with paper trading** before real money

---

## 💾 Data Persistence

Your data is stored in:

```
C:\Personal\TelegramSignalTrader\
├── data/                  # SQLite database
└── sessions/              # Telegram sessions
```

**Even if you stop containers, this data persists!**

To backup:
```powershell
# Copy these folders to a safe location
Copy-Item -Recurse data, sessions D:\Backups\TelegramBot\
```

---

## 🆘 Getting Help

### Check Logs First
```powershell
docker compose logs -f
```
Logs show errors and status messages.

### Common Error Messages

| Error | Meaning | Solution |
|-------|---------|----------|
| `sqlite3.OperationalError: no such table` | Database not initialized | Normal on first run, will auto-create |
| `Failed to restore broker session` | No broker configured yet | Configure through web UI |
| `No active Telegram configuration` | Telegram not set up | Configure in .env or web UI |
| `Port already in use` | Another app using same port | Stop other apps or change ports |

### Documentation

- [Docker Deployment Guide](DOCKER_DEPLOYMENT_GUIDE.md) - Advanced Docker usage
- [Setup Guide](SETUP_GUIDE.md) - Manual installation
- [Quick Start](QUICK_START.md) - Quick reference
- [Project Summary](PROJECT_SUMMARY.md) - Architecture overview

---

## 🎓 Docker Concepts Explained

### What's a Container?

A **container** is like a lightweight virtual machine:
- Has its own filesystem
- Runs isolated from your main computer
- Can be started, stopped, deleted instantly
- Multiple containers can run simultaneously

### What's an Image?

An **image** is the blueprint for a container:
- Contains the application code and all dependencies
- Think of it as a template
- Stored on your computer or downloaded from Docker Hub

### What's Docker Compose?

**Docker Compose** manages multiple containers:
- Our project has 2 containers: backend + frontend
- One command (`docker compose up`) starts both
- Handles networking between containers automatically

### What's a Volume?

A **volume** is persistent storage:
- Data survives even if containers are deleted
- Located in `data/` and `sessions/` folders
- Mounted into containers at runtime

---

## 🏁 Quick Reference

### Essential Commands

```powershell
# Start
docker compose up -d

# Stop
docker compose down

# Logs
docker compose logs -f

# Status
docker compose ps

# Restart
docker compose restart
```

### File Locations

```
Project Files:       C:\Personal\TelegramSignalTrader\
Configuration:       .env
Database:            data/trading_bot.db
Telegram Sessions:   sessions/
```

### URLs

```
Dashboard:    http://localhost:5173
API:          http://localhost:8000
API Docs:     http://localhost:8000/docs
```

---

## 🎉 Congratulations!

You've successfully learned how to:
- ✅ Install Docker
- ✅ Run a multi-container application
- ✅ Manage containers with Docker Compose
- ✅ View logs and troubleshoot issues
- ✅ Configure and use the trading bot

**You're now ready to use the Telegram Trading Bot!** 🚀

---

## 📝 Notes

- **First run** takes 2-5 minutes (downloading images)
- **Subsequent runs** take only 5-10 seconds
- **Data persists** across container restarts
- **Logs help** diagnose any issues
- **Docker Desktop** must be running for containers to work

---

**Need Help?** Check the logs first: `docker compose logs -f`

**Happy Trading!** 📈
