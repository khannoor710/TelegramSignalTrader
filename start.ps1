# Start script for Telegram Trading Bot

Write-Host "🚀 Starting Telegram Trading Bot..." -ForegroundColor Green
Write-Host "===================================" -ForegroundColor Green
Write-Host ""

# Check if .env exists
if (!(Test-Path ".env")) {
    Write-Host "✗ .env file not found!" -ForegroundColor Red
    Write-Host "  Please run .\setup.ps1 first" -ForegroundColor Yellow
    exit 1
}

# Start backend
Write-Host "Starting backend server..." -ForegroundColor Yellow
$backend = Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD\backend'; Write-Host 'Backend Server - Press Ctrl+C to stop' -ForegroundColor Green; uvicorn main:app --reload --host 0.0.0.0 --port 8000" -PassThru

# Wait a bit for backend to start
Start-Sleep -Seconds 3

# Start frontend
Write-Host "Starting frontend server..." -ForegroundColor Yellow
$frontend = Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD\frontend'; Write-Host 'Frontend Server - Press Ctrl+C to stop' -ForegroundColor Green; npm run dev" -PassThru

Write-Host ""
Write-Host "===================================" -ForegroundColor Green
Write-Host "✅ Application started successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "Access the application:" -ForegroundColor Cyan
Write-Host "  Frontend: http://localhost:5173" -ForegroundColor White
Write-Host "  Backend:  http://localhost:8000" -ForegroundColor White
Write-Host "  API Docs: http://localhost:8000/docs" -ForegroundColor White
Write-Host ""
Write-Host "Press any key to stop all servers..." -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

# Stop servers
Write-Host "Stopping servers..." -ForegroundColor Yellow
Stop-Process -Id $backend.Id -Force -ErrorAction SilentlyContinue
Stop-Process -Id $frontend.Id -Force -ErrorAction SilentlyContinue
Write-Host "✅ Servers stopped" -ForegroundColor Green
