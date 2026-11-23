@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    py -m pip install --user uv >nul 2>&1
    py -m uv venv --seed .venv >nul 2>&1
)

call ".venv\Scripts\activate.bat"
python -m pip install --upgrade google-genai python-dotenv PySide6 streamlit >nul 2>&1
if errorlevel 1 (
    echo ERROR: No se pudieron instalar las dependencias.
    echo Revisa la conexion a Internet y vuelve a intentarlo.
    exit /b 1
)

if not exist ".env" (
    if exist ".env.example" (
        copy ".env.example" ".env" >nul
        echo Se creo .env desde .env.example. Edita la clave antes de continuar.
    ) else (
        echo ERROR: No existe .env ni .env.example en la carpeta del proyecto.
        exit /b 1
    )
)

python -c "import os; from dotenv import load_dotenv; load_dotenv(); import sys; sys.exit(0 if os.getenv('GOOGLE_API_KEY') else 1)" >nul 2>&1
if errorlevel 1 (
    echo ERROR: Falta GOOGLE_API_KEY en .env.
    echo Sigue la plantilla de .env.example.
    exit /b 1
)

rem Inicia el agente en la interfaz grafica Qt
python gemini_qt_app.py
exit /b %ERRORLEVEL%
