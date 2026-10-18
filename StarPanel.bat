@echo off
cd /d %~dp0
start "" cmd /k "cd backend && .\venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000 --env-file .env"
start "" cmd /k "cd frontend && npm run dev"
timeout 5 >nul
start "" "http://localhost:3000"
