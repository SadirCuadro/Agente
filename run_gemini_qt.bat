@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    py -m pip install --user uv >nul 2>&1
    py -m uv venv --seed .venv >nul 2>&1
)

call ".venv\Scripts\activate.bat"
python -m pip install --upgrade google-genai python-dotenv PySide6 >nul 2>&1
python gemini_qt_app.py
exit /b 0
