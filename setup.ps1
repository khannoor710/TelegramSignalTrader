# Setup script for Telegram Trading Bot

Write-Host "🚀 Telegram Trading Bot - Setup Script" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# Check Python
Write-Host "Checking Python installation..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Python is installed: $pythonVersion" -ForegroundColor Green
} else {
    Write-Host "✗ Python is not installed. Please install Python 3.11+ from https://www.python.org/" -ForegroundColor Red
    exit 1
}

# Check Node.js
Write-Host "Checking Node.js installation..." -ForegroundColor Yellow
$nodeVersion = node --version 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Node.js is installed: $nodeVersion" -ForegroundColor Green
    $npmVersion = npm --version 2>&1
    Write-Host "✓ npm is installed: v$npmVersion" -ForegroundColor Green
} else {
    Write-Host "✗ Node.js is not installed." -ForegroundColor Red
    Write-Host "  Please install Node.js 20+ from https://nodejs.org/" -ForegroundColor Yellow
    Write-Host "  After installation, rerun this script." -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "Installing backend dependencies..." -ForegroundColor Yellow
Set-Location backend
python -m pip install -r requirements.txt --user
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Failed to install backend dependencies" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Backend dependencies installed successfully" -ForegroundColor Green

Write-Host ""
Write-Host "Installing frontend dependencies..." -ForegroundColor Yellow
Set-Location ..\frontend
npm install
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Failed to install frontend dependencies" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Frontend dependencies installed successfully" -ForegroundColor Green

Write-Host ""
Write-Host "Creating environment file..." -ForegroundColor Yellow
Set-Location ..
if (!(Test-Path ".env")) {
    Copy-Item .env.example .env
    Write-Host "✓ Created .env file from template" -ForegroundColor Green
    Write-Host "⚠ Please edit .env file with your credentials" -ForegroundColor Yellow
} else {
    Write-Host "⚠ .env file already exists, skipping" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "✅ Setup completed successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Edit .env file with your Telegram and Angel One credentials" -ForegroundColor White
Write-Host "2. Run .\start.ps1 to start the application" -ForegroundColor White
Write-Host ""
Write-Host "Or start manually:" -ForegroundColor Cyan
Write-Host "  Backend:  cd backend && uvicorn main:app --reload" -ForegroundColor White
Write-Host "  Frontend: cd frontend && npm run dev" -ForegroundColor White
Write-Host ""
