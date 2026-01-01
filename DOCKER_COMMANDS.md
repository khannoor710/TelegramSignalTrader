# Docker Commands Reference

## Quick Start

### Start the Application
```powershell
docker-compose up -d
```

### Start with Fresh Build
```powershell
docker-compose up --build -d
```

### Stop the Application
```powershell
docker-compose down
```

### Stop and Remove Volumes (Clean Start)
```powershell
docker-compose down -v
```

## Monitoring

### View Container Status
```powershell
docker-compose ps
```

### View Backend Logs
```powershell
docker-compose logs backend -f
```

### View Frontend Logs
```powershell
docker-compose logs frontend -f
```

### View All Logs
```powershell
docker-compose logs -f
```

### View Last 50 Lines of Logs
```powershell
docker-compose logs backend --tail=50
docker-compose logs frontend --tail=50
```

## Container Management

### Restart Services
```powershell
docker-compose restart
```

### Restart Specific Service
```powershell
docker-compose restart backend
docker-compose restart frontend
```

### Execute Commands in Container
```powershell
# Backend shell
docker-compose exec backend bash

# Frontend shell
docker-compose exec frontend sh

# Run Python script in backend
docker-compose exec backend python script.py

# Check database
docker-compose exec backend python check_database.py
```

## Development

### Rebuild After Code Changes
```powershell
# Rebuild specific service
docker-compose up --build backend -d

# Rebuild all services
docker-compose up --build -d
```

### View Resource Usage
```powershell
docker stats
```

## Testing

### Test Signal Parser (via API)
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/paper/test-signal" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"message": "banknifty 53200 pe buy above 350 tgt 400 sl 290"}' | ConvertTo-Json
```

### Check Health Status
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/health"
```

## Troubleshooting

### View Detailed Container Info
```powershell
docker inspect telegram-trading-backend
docker inspect telegram-trading-frontend
```

### Check Network
```powershell
docker network inspect telegram-trading-network
```

### Remove Orphaned Containers
```powershell
docker-compose down --remove-orphans
```

### Clean Docker System (Caution!)
```powershell
# Remove unused images
docker image prune -a

# Remove all stopped containers
docker container prune

# Remove all unused volumes
docker volume prune
```

## Access Points

- **Frontend:** http://localhost:5173
- **Backend API:** http://localhost:8000
- **API Documentation:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/health

## Important Notes

1. **Hot Reload:** Both backend and frontend support hot reload - code changes are automatically detected
2. **Data Persistence:** Database and Telegram sessions are persisted in volumes
3. **Environment Variables:** Make sure your `.env` file is properly configured before starting
4. **First Run:** Initial startup may take longer as dependencies are installed

## Common Issues

### Port Already in Use
```powershell
# Find and kill process using port 8000
Get-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess | Stop-Process -Force

# Find and kill process using port 5173
Get-Process -Id (Get-NetTCPConnection -LocalPort 5173).OwningProcess | Stop-Process -Force
```

### Container Won't Start
```powershell
# Check logs for errors
docker-compose logs backend --tail=100
docker-compose logs frontend --tail=100

# Remove and rebuild
docker-compose down -v
docker-compose up --build -d
```

### Database Locked
```powershell
# Stop all containers
docker-compose down

# Remove volumes
docker volume rm telegramsignaltrader_data

# Start fresh
docker-compose up -d
```
