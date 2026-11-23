@echo off
setlocal
cd /d "%~dp0"
echo ============================================================
echo   Iniciando Asistente Persistente: Segundo Cerebro
echo ============================================================
call .venv\Scripts\activate.bat
python run_asistente.py
pause
