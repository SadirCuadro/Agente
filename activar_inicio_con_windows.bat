@echo off
setlocal
cd /d "%~dp0"

echo ============================================================
echo   Configurando Inicio Automatico con Windows
echo ============================================================

set "VBS_PATH=%~dp0run_asistente_oculto.vbs"
set "STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "SHORTCUT_PATH=%STARTUP_FOLDER%\AsistenteSegundoCerebro.lnk"

powershell -NoProfile -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%SHORTCUT_PATH%'); $s.TargetPath = 'wscript.exe'; $s.Arguments = '\"%VBS_PATH%\"'; $s.WorkingDirectory = '%~dp0'; $s.Description = 'Asistente Persistente Segundo Cerebro'; $s.Save()"

if exist "%SHORTCUT_PATH%" (
    echo.
    echo [EXITO] Se configuro el asistente para iniciar automaticamente al encender tu PC.
    echo Ubicacion: %SHORTCUT_PATH%
    echo Se ejecutara en segundo plano (silencioso) en la bandeja del sistema.
    echo.
) else (
    echo.
    echo [ERROR] No se pudo crear el acceso directo en Startup.
    echo.
)

pause
