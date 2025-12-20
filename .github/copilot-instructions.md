# Telegram Trading Bot - Project Instructions

## Project Overview
Full-stack web application for reading trading calls from Telegram groups and executing them on Angel One broker account.

## Technology Stack
- Backend: Python FastAPI + Telethon + Angel One SmartAPI
- Frontend: React + Vite
- Database: SQLite
- Real-time: WebSockets

## Setup Status ✅
- [x] Create copilot-instructions.md file
- [x] Scaffold backend structure (FastAPI + Services + Models)
- [x] Scaffold frontend structure (React + Pages + Components)
- [x] Create configuration files (Docker, .env, requirements.txt, package.json)
- [x] Create documentation (README.md, SETUP_GUIDE.md, PROJECT_SUMMARY.md)
- [x] Install dependencies (Python packages installed, Node.js required)

## Quick Start
1. Install Node.js from https://nodejs.org/ (if not already installed)
2. Run: `.\setup.ps1` (installs all dependencies)
3. Edit: `.env` file with your credentials
4. Run: `.\start.ps1` (starts backend + frontend)
5. Open: http://localhost:5173

## Project Structure
- `backend/` - Python FastAPI backend with Telegram & Angel One integration
- `frontend/` - React frontend with dashboard and trade management
- `setup.ps1` - Automated setup script
- `start.ps1` - Start application script
- See PROJECT_SUMMARY.md for complete file listing
