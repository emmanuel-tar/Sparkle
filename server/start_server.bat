@echo off
REM Start server in a new window
cd /d "%~dp0"
python -m uvicorn app.main:app --port 8001 --host 127.0.0.1
pause
