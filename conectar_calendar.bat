@echo off
setlocal
cd /d "%~dp0"
echo ============================================================
echo   Vinculando tu cuenta de Google Calendar
echo ============================================================
call .venv\Scripts\activate.bat
python conectar_calendar.py
pause
