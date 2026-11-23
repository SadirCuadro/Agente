# Gemini Agent

Aplicación de chat con Gemini usando Python.

## Requisitos

- Python 3.10+
- entorno virtual `.venv`
- archivo `.env` con:

```env
GOOGLE_API_KEY=tu_clave
GOOGLE_MODEL_ID=gemini-3.6-flash
```

## Ejecutar desde terminal

```powershell
cd "C:\Users\User\Downloads\gemmini"
.\.venv\Scripts\python.exe simple_google_agent.py
```

```powershell
cd "C:\Users\User\Downloads\gemmini"
.\.venv\Scripts\python.exe gemini_qt_app.py
```

## Ejecutar desde VS Code

- Pulsa `F5`
- o usa `Terminal > Run Task`
- selecciona `Run Gemini Console` o `Run Gemini Qt`

## Verificación

Se ha comprobado que la llamada real a Gemini responde correctamente con `OK`.
