# Docker Deployment Guide 🐳

This guide provides comprehensive instructions for deploying the Telegram Trading Bot using Docker.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Development Mode](#development-mode)
- [Production Mode](#production-mode)
- [Environment Variables](#environment-variables)
- [Common Commands](#common-commands)
- [SSL/TLS Setup](#ssltls-setup)
- [Troubleshooting](#troubleshooting)
- [Backup & Restore](#backup--restore)
- [Architecture](#architecture)

---

## Prerequisites

### Required Software

1. **Docker Engine** (v20.10+)
   - [Install Docker for Windows](https://docs.docker.com/desktop/install/windows-install/)
   - [Install Docker for Linux](https://docs.docker.com/engine/install/)
   - [Install Docker for macOS](https://docs.docker.com/desktop/install/mac-install/)

2. **Docker Compose** (v2.0+)
   - Usually included with Docker Desktop
   - For Linux: `sudo apt install docker-compose-plugin`

### Verify Installation

```bash
# Check Docker version
docker --version

# Check Docker Compose version
docker compose version

# Verify Docker is running
docker info
```

---

## Quick Start

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd Telegram
```

### 2. Configure Environment Variables

```bash
# Copy the example environment file
cp .env.example .env

# Edit with your credentials
# Windows: notepad .env
# Linux/macOS: nano .env
```

### 3. Generate Encryption Key

```bash
# Generate a new encryption key
docker run --rm python:3.11-slim python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Copy the output and paste it as your `ENCRYPTION_KEY` in `.env`.

### 4. Start the Application

```bash
# Development mode (with hot reload)
docker compose up --build

# Or in detached mode (background)
docker compose up -d --build
```

### 5. Access the Application

| Service | URL |
|---------|-----|
| Frontend | http://localhost:5173 (dev) / http://localhost (prod) |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |

---

## Development Mode

Development mode features:
- ✅ Hot reload for both frontend and backend
- ✅ Source code mounted as volumes
- ✅ Debug-friendly logging
- ✅ Vite dev server for frontend

### Start Development Environment

```bash
# Build and start
docker compose up --build

# Start in background
docker compose up -d --build

# View logs
docker compose logs -f

# View specific service logs
docker compose logs -f backend
docker compose logs -f frontend
```

### Rebuild After Changes

```bash
# Force rebuild without cache
docker compose build --no-cache

# Rebuild specific service
docker compose build --no-cache backend
```

---

## Production Mode

Production mode features:
- ✅ Gunicorn WSGI server with multiple workers
- ✅ Nginx for static file serving & reverse proxy
- ✅ Optimized multi-stage builds
- ✅ Resource limits
- ✅ Health checks
- ✅ Log rotation
- ✅ Non-root user for security

### Start Production Environment

```bash
# Build and start production containers
docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d

# Verify containers are running
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps

# View logs
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f
```

### Stop Production Environment

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml down
```

---

## Environment Variables

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `ENCRYPTION_KEY` | Fernet key for encrypting sensitive data | `YWJjZGVmZ2...` |
| `TELEGRAM_API_ID` | Telegram API ID from my.telegram.org | `12345678` |
| `TELEGRAM_API_HASH` | Telegram API Hash from my.telegram.org | `abc123def456...` |
| `TELEGRAM_PHONE_NUMBER` | Your Telegram phone number | `+911234567890` |

### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./data/trading_bot.db` | Database connection string |
| `GEMINI_API_KEY` | - | Google Gemini API key for AI parsing |
| `GEMINI_MODEL` | `gemini-2.0-flash` | Gemini model to use |
| `AUTO_TRADE_ENABLED` | `false` | Enable automatic trade execution |
| `REQUIRE_MANUAL_APPROVAL` | `true` | Require approval before trades |
| `DEFAULT_QUANTITY` | `1` | Default trade quantity |
| `MAX_TRADES_PER_DAY` | `10` | Maximum trades per day |
| `RISK_PERCENTAGE` | `1.0` | Risk percentage per trade |

### Broker Variables (Add as needed)

**Angel One:**
```env
ANGEL_ONE_API_KEY=your_api_key
ANGEL_ONE_CLIENT_ID=your_client_id
ANGEL_ONE_PASSWORD=your_password
ANGEL_ONE_TOTP_SECRET=your_totp_secret
```

**Zerodha:**
```env
ZERODHA_API_KEY=your_api_key
ZERODHA_API_SECRET=your_api_secret
```

---

## Common Commands

### Container Management

```bash
# Start services
docker compose up -d

# Stop services
docker compose down

# Restart services
docker compose restart

# Restart specific service
docker compose restart backend

# View running containers
docker compose ps

# View all containers (including stopped)
docker compose ps -a
```

### Logs

```bash
# View all logs
docker compose logs

# Follow logs in real-time
docker compose logs -f

# View last 100 lines
docker compose logs --tail=100

# View specific service logs
docker compose logs -f backend
```

### Debugging

```bash
# Execute command in running container
docker compose exec backend bash
docker compose exec frontend sh

# View container resource usage
docker stats

# Inspect container
docker inspect telegram-trading-backend
```

### Cleanup

```bash
# Remove containers and networks
docker compose down

# Remove containers, networks, and volumes
docker compose down -v

# Remove unused images
docker image prune

# Full cleanup (use with caution!)
docker system prune -a
```

---

## SSL/TLS Setup

### Using Traefik (Recommended for Production)

Create `docker-compose.traefik.yml`:

```yaml
version: '3.8'

services:
  traefik:
    image: traefik:v2.10
    container_name: traefik
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./traefik/acme.json:/acme.json
    command:
      - "--api.insecure=false"
      - "--providers.docker=true"
      - "--entrypoints.web.address=:80"
      - "--entrypoints.websecure.address=:443"
      - "--certificatesresolvers.letsencrypt.acme.httpchallenge=true"
      - "--certificatesresolvers.letsencrypt.acme.httpchallenge.entrypoint=web"
      - "--certificatesresolvers.letsencrypt.acme.email=your@email.com"
      - "--certificatesresolvers.letsencrypt.acme.storage=/acme.json"

  frontend:
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.frontend.rule=Host(`yourdomain.com`)"
      - "traefik.http.routers.frontend.entrypoints=websecure"
      - "traefik.http.routers.frontend.tls.certresolver=letsencrypt"
```

---

## Troubleshooting

### Common Issues

#### 1. Port Already in Use

```bash
# Check what's using the port
netstat -ano | findstr :8000  # Windows
lsof -i :8000                  # Linux/macOS

# Kill the process or change the port in docker-compose.yml
```

#### 2. Container Won't Start

```bash
# Check logs for errors
docker compose logs backend

# Check container status
docker compose ps

# Rebuild from scratch
docker compose down -v
docker compose build --no-cache
docker compose up
```

#### 3. Database Connection Issues

```bash
# Check if database file exists
docker compose exec backend ls -la /app/data/

# Check database permissions
docker compose exec backend ls -la /app/data/trading_bot.db
```

#### 4. Permission Denied Errors

```bash
# Fix data directory permissions on Linux
sudo chown -R 1000:1000 ./data
sudo chown -R 1000:1000 ./sessions
```

#### 5. Memory Issues

```bash
# Check container memory usage
docker stats

# Increase Docker memory limit in Docker Desktop settings
```

### Health Check Failures

```bash
# Check backend health
curl http://localhost:8000/api/health

# Check container health status
docker inspect --format='{{.State.Health.Status}}' telegram-trading-backend
```

---

## Backup & Restore

### Backup

```bash
# Create backup directory
mkdir -p backups

# Backup database
docker compose exec backend cp /app/data/trading_bot.db /app/data/trading_bot.db.backup
cp ./data/trading_bot.db ./backups/trading_bot_$(date +%Y%m%d_%H%M%S).db

# Backup sessions
cp -r ./sessions ./backups/sessions_$(date +%Y%m%d_%H%M%S)

# Backup environment
cp .env ./backups/.env_$(date +%Y%m%d_%H%M%S)
```

### Restore

```bash
# Stop services
docker compose down

# Restore database
cp ./backups/trading_bot_YYYYMMDD_HHMMSS.db ./data/trading_bot.db

# Restore sessions
cp -r ./backups/sessions_YYYYMMDD_HHMMSS/* ./sessions/

# Restart services
docker compose up -d
```

### Automated Backup Script

Create `backup.sh`:

```bash
#!/bin/bash
BACKUP_DIR="./backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Backup database
cp ./data/trading_bot.db "$BACKUP_DIR/"

# Backup sessions
cp -r ./sessions "$BACKUP_DIR/"

# Backup environment
cp .env "$BACKUP_DIR/"

# Keep only last 7 days of backups
find ./backups -type d -mtime +7 -exec rm -rf {} +

echo "Backup completed: $BACKUP_DIR"
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Docker Network                            │
│  ┌─────────────────────┐    ┌─────────────────────────────┐ │
│  │   Frontend (Nginx)  │    │     Backend (Gunicorn)      │ │
│  │   Port: 80          │───▶│     Port: 8000              │ │
│  │                     │    │                             │ │
│  │  - Static files     │    │  - FastAPI                  │ │
│  │  - Reverse proxy    │    │  - WebSocket                │ │
│  │  - Gzip compression │    │  - Database                 │ │
│  └─────────────────────┘    └──────────────┬──────────────┘ │
│                                            │                 │
│                              ┌─────────────▼──────────────┐ │
│                              │        Volumes             │ │
│                              │  - ./data (database)       │ │
│                              │  - ./sessions (telegram)   │ │
│                              └────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Service Ports

| Service | Development | Production |
|---------|-------------|------------|
| Frontend | 5173 | 80 |
| Backend | 8000 | 8000 |

---

## Support

If you encounter issues:

1. Check the [Troubleshooting](#troubleshooting) section
2. Review container logs: `docker compose logs -f`
3. Ensure all environment variables are set correctly
4. Verify Docker has enough resources allocated

---

*Happy Trading! 📈*
