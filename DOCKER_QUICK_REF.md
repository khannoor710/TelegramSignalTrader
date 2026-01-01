# 🚀 Quick Reference Card

## Start Application
```powershell
docker-compose up -d
```

## Stop Application
```powershell
docker-compose down
```

## View Logs (Live)
```powershell
docker-compose logs -f
```

## Access Application
- **Frontend:** http://localhost:5173
- **API Docs:** http://localhost:8000/docs

## Test Signal Parser
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/paper/test-signal" `
  -Method POST -ContentType "application/json" `
  -Body '{"message": "banknifty 53200 pe buy above 350 tgt 400 sl 290"}' | ConvertTo-Json
```

## Restart Services
```powershell
docker-compose restart
```

## Rebuild & Start
```powershell
docker-compose up --build -d
```

## Check Status
```powershell
docker-compose ps
```

---

📖 **Full documentation:** [DOCKER_COMMANDS.md](DOCKER_COMMANDS.md)
