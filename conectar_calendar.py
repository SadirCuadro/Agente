import sys
from pathlib import Path

ruta_raiz = Path(__file__).resolve().parent
if str(ruta_raiz) not in sys.path:
    sys.path.insert(0, str(ruta_raiz))

from asistente.conector_calendar import ConectorCalendar

print("=" * 60)
print("  Conexión y Autenticación con Google Calendar")
print("=" * 60)

cal = ConectorCalendar()
if not cal.ruta_credenciales.exists():
    print("\n[ERROR] No se encontró credentials.json en la raíz del proyecto.")
    sys.exit(1)

print("\nAbriendo el navegador web para iniciar sesión...")
print("------------------------------------------------------------")
print("Instrucciones en el navegador:")
print("1. Selecciona tu cuenta de Gmail.")
print("2. Si ves la pantalla 'Google no ha verificado esta app':")
print("   - Haz clic en 'Configuración avanzada' (o 'Advanced').")
print("   - Haz clic en 'Ir a Asistente Personal (no seguro)' abajo.")
print("3. Marca la casilla de permisos para ver/administrar tus calendarios.")
print("4. Pulsa 'Continuar'.")
print("------------------------------------------------------------\n")

try:
    servicio = cal._obtener_servicio(interactivo=True)
    if servicio:
        print("\n" + "=" * 60)
        print("  ¡ÉXITO! Google Calendar conectado al 100%.")
        print(f"  Token persistente guardado en: {cal.ruta_token.name}")
        eventos = cal.listar_eventos(max_resultados=5)
        print(f"  Próximos eventos encontrados en tu calendario: {len(eventos)}")
        for ev in eventos:
            print(f"   • [{ev.get('inicio', 'Sin fecha')}] {ev.get('titulo', 'Sin título')}")
        print("=" * 60)
    else:
        print("[ERROR] No se pudo obtener el servicio de Google Calendar.")
except Exception as exc:
    print(f"\n[ERROR durante la autenticación]: {exc}")
