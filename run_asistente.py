"""
Punto de Entrada del Asistente Persistente de Escritorio (Segundo Cerebro).

Lanza la aplicación con System Tray, interfaz Spotlight (Ctrl + Espacio) y
conexión con Obsidian y Google Calendar.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Asegurar que el directorio raíz del proyecto esté en sys.path
ruta_raiz = Path(__file__).resolve().parent
if str(ruta_raiz) not in sys.path:
    sys.path.insert(0, str(ruta_raiz))

from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

from asistente.interfaz_spotlight import AplicacionAsistente


def main():
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("\n[ERROR] Falta configurar GOOGLE_API_KEY en el archivo .env")
        print("Por favor, abre el archivo .env y coloca tu clave de Google Gemini.\n")
        sys.exit(1)

    print("============================================================")
    print("  Iniciando Asistente Persistente: Segundo Cerebro")
    print("  - Atajo Global: Ctrl + Espacio")
    print("  - Icono residente en la Bandeja del Sistema (System Tray)")
    print("  - Presiona 'Esc' para ocultar la ventana en cualquier momento")
    print("============================================================")

    app = AplicacionAsistente()
    sys.exit(app.ejecutar())


if __name__ == "__main__":
    main()
