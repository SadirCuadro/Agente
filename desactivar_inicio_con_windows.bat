@echo off
setlocal
cd /d "%~dp0"

echo ============================================================
echo   Desactivando Inicio Automatico con Windows
echo ============================================================

set "STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "SHORTCUT_PATH=%STARTUP_FOLDER%\AsistenteSegundoCerebro.lnk"

if exist "%SHORTCUT_PATH%" (
    del "%SHORTCUT_PATH%"
    echo.
    echo [EXITO] Se elimino el inicio automatico.
    echo El asistente ya no se abrira al encender la PC.
    echo.
) else (
    echo.
    echo [INFO] El asistente no estaba configurado para inicio automatico.
    echo.
)

pause
