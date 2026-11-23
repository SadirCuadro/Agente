@echo off
setlocal
cd /d "%~dp0"
echo ============================================================
echo   Iniciando "Foto y Control": Gestor Inteligente de Gastos
echo ============================================================
call .venv\Scripts\activate.bat
streamlit run app_finanzas.py --server.port 8502
pause
