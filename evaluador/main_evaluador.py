"""
Script principal de demostración y CLI del Módulo de Evaluación de Exámenes.

Ejecuta el ciclo de vida completo de una evaluación:
1. Creación y estructuración del examen (preguntas y plantilla de respuestas).
2. Formateo del examen para los estudiantes.
3. Envío por correo electrónico a una lista de estudiantes (simulación o SMTP real).
4. Registro de respuestas en almacenamiento local (data/respuestas.json).
5. Calificación automática (escala 0.0 a 5.0).
6. Generación del informe comparativo (nota máxima, mínima, promedio y ranking).
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Cargar automáticamente .env si dotenv está disponible
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Permitir ejecutar directamente `python evaluador/main_evaluador.py`
if __name__ == "__main__" and __package__ is None:
    ruta_raiz = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(ruta_raiz))

from evaluador.almacenamiento import GestorAlmacenamiento, RespuestaEstudiante
from evaluador.evaluador_notas import EvaluadorNotas, generar_tabla_comparativa
from evaluador.generador_examen import Examen, Pregunta, formatear_examen_para_correo
from evaluador.gestor_correo import ConfiguracionSMTP, GestorCorreo


def construir_examen_demostracion() -> Examen:
    """Crea un examen de prueba con preguntas de opción múltiple sobre Python y Algoritmos."""
    examen = Examen(
        id_examen="EXAM-PYTHON-2026",
        titulo="Evaluación de Fundamentos de Python y Algoritmos",
        descripcion=(
            "Examen de selección múltiple con única respuesta válida.\n"
            "Lee cada pregunta con atención. Dispones de un único intento."
        ),
    )

    examen.agregar_pregunta(
        Pregunta(
            id=1,
            enunciado="¿Cuál de las siguientes estructuras de datos en Python es mutable?",
            opciones={
                "A": "Tupla (tuple)",
                "B": "Lista (list)",
                "C": "Cadena de caracteres (str)",
                "D": "Entero (int)",
            },
            respuesta_correcta="B",
        )
    )

    examen.agregar_pregunta(
        Pregunta(
            id=2,
            enunciado="¿Cuál es la complejidad temporal promedio de búsqueda en un diccionario (dict) de Python?",
            opciones={
                "A": "O(n)",
                "B": "O(log n)",
                "C": "O(1)",
                "D": "O(n^2)",
            },
            respuesta_correcta="C",
        )
    )

    examen.agregar_pregunta(
        Pregunta(
            id=3,
            enunciado="¿Qué palabra clave se usa para definir un generador en Python?",
            opciones={
                "A": "return",
                "B": "yield",
                "C": "generate",
                "D": "produce",
            },
            respuesta_correcta="B",
        )
    )

    examen.agregar_pregunta(
        Pregunta(
            id=4,
            enunciado="¿Qué excepción se lanza al intentar abrir un archivo inexistente en modo lectura con open()?",
            opciones={
                "A": "KeyError",
                "B": "IndexError",
                "C": "FileNotFoundError",
                "D": "ValueError",
            },
            respuesta_correcta="C",
        )
    )

    examen.agregar_pregunta(
        Pregunta(
            id=5,
            enunciado="¿Cuál es la salida de: bool('False') en Python?",
            opciones={
                "A": "False",
                "B": "True",
                "C": "None",
                "D": "TypeError",
            },
            respuesta_correcta="B",
        )
    )

    return examen


def obtener_estudiantes_demostracion() -> list[tuple[str, str, str]]:
    """Retorna una lista de estudiantes de prueba: (id, nombre, correo)."""
    return [
        ("EST-001", "Valentina Gómez", "valentina.gomez@universidad.edu.co"),
        ("EST-002", "Mateo Rodríguez", "mateo.rodriguez@universidad.edu.co"),
        ("EST-003", "Camila Restrepo", "camila.restrepo@universidad.edu.co"),
        ("EST-004", "Santiago Herrera", "santiago.herrera@universidad.edu.co"),
        ("EST-005", "Daniela Morales", "daniela.morales@universidad.edu.co"),
        ("EST-006", "Andrés Castro", "andres.castro@universidad.edu.co"),
    ]


def generar_respuestas_simuladas(
    examen: Examen, estudiantes: list[tuple[str, str, str]]
) -> list[RespuestaEstudiante]:
    """Genera respuestas realistas con diferentes niveles de acierto para probar

    el ranking, notas máximas, mínimas y promedios.
    Clave oficial: 1: B, 2: C, 3: B, 4: C, 5: B
    """
    patrones_respuestas = [
        # Valentina Gómez: 5 de 5 aciertos -> Nota 5.0
        {1: "B", 2: "C", 3: "B", 4: "C", 5: "B"},
        # Mateo Rodríguez: 4 de 5 aciertos (falló la 2) -> Nota 4.0
        {1: "B", 2: "A", 3: "B", 4: "C", 5: "B"},
        # Camila Restrepo: 4 de 5 aciertos (falló la 5) -> Nota 4.0
        {1: "B", 2: "C", 3: "B", 4: "C", 5: "A"},
        # Santiago Herrera: 3 de 5 aciertos (falló la 2 y la 5) -> Nota 3.0
        {1: "B", 2: "B", 3: "B", 4: "C", 5: "A"},
        # Daniela Morales: 2 de 5 aciertos (falló 1, 2, 4) -> Nota 2.0
        {1: "A", 2: "A", 3: "B", 4: "A", 5: "B"},
        # Andrés Castro: 1 de 5 aciertos, 3 incorrectas y 1 sin responder (la 5) -> Nota 1.0
        {1: "C", 2: "B", 3: "A", 4: "C", 5: ""},
    ]

    respuestas_guardadas: list[RespuestaEstudiante] = []
    for (est_id, nombre, correo), patron in zip(estudiantes, patrones_respuestas):
        respuestas_guardadas.append(
            RespuestaEstudiante(
                estudiante_id=est_id,
                nombre=nombre,
                correo=correo,
                id_examen=examen.id_examen,
                respuestas=patron,
            )
        )
    return respuestas_guardadas


def ejecutar_demostracion(
    modo_correo_real: bool = False, destinatario_real: Optional[str] = None
) -> None:
    """Ejecuta el flujo completo de prueba mostrando cada fase en consola."""
    # Configurar salida de terminal para soportar UTF-8 de forma segura si la consola lo permite
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    print("\n" + "=" * 80)
    print(" INICIANDO FLUJO COMPLETO: MODULO DE GESTION Y EVALUACION DE EXAMENES ".center(80, "="))
    print("=" * 80 + "\n")

    # -------------------------------------------------------------------------
    # FASE 1: Creación del Examen
    # -------------------------------------------------------------------------
    print("[FASE 1] Creando y estructurando examen...")
    examen = construir_examen_demostracion()
    print(f"   -> Examen ID: {examen.id_examen}")
    print(f"   -> Titulo   : {examen.titulo}")
    print(f"   -> Total preguntas configuradas: {len(examen.preguntas)}")
    print("\n" + examen.formatear_clave_profesor())

    # -------------------------------------------------------------------------
    # FASE 2: Formateo y Envío por Correo Electrónico
    # -------------------------------------------------------------------------
    print("\n" + "-" * 80)
    print("[FASE 2] Formateando y enviando examen a los estudiantes...")
    estudiantes = obtener_estudiantes_demostracion()

    servidor_smtp = os.getenv("SMTP_SERVER") or os.getenv("SMTP_HOST") or "smtp.gmail.com"
    puerto_smtp = int(os.getenv("SMTP_PORT") or "587")
    usuario_smtp = os.getenv("SMTP_USER", "").strip()
    pass_smtp = (os.getenv("SMTP_PASS") or os.getenv("SMTP_PASSWORD") or "").strip()
    remitente_nombre = os.getenv("EMAIL_FROM") or "Profesor - Evaluacion de Programacion"

    config_smtp = ConfiguracionSMTP(
        servidor=servidor_smtp,
        puerto=puerto_smtp,
        usuario=usuario_smtp,
        password=pass_smtp,
        remitente_nombre=remitente_nombre,
    )

    usar_simulacion = not modo_correo_real or not config_smtp.usuario
    gestor_correo = GestorCorreo(config=config_smtp, modo_simulacion=usar_simulacion)

    if usar_simulacion:
        print("   [INFO] Modo de envio: SIMULACION SEGURA (dry-run sin enviar correos reales).")
    else:
        print(f"   [INFO] Modo de envio: REAL mediante {config_smtp.servidor}:{config_smtp.puerto}.")

    # Demostrar el formato de correo con el primer alumno
    primer_alumno = estudiantes[0]
    cuerpo_muestra = formatear_examen_para_correo(examen, primer_alumno[1])
    print(f"\n--- [VISTA PREVIA DEL CORREO PARA {primer_alumno[1]}] ---")
    lineas_muestra = cuerpo_muestra.splitlines()
    for linea in lineas_muestra[:15]:
        print(f"   | {linea}")
    print(f"   | ... [{len(lineas_muestra) - 15} lineas adicionales de examen] ...\n")

    # Enviar examen
    if modo_correo_real and config_smtp.usuario:
        destino_real = destinatario_real or config_smtp.usuario
        print(f"   [INFO] Enviando correo real a la bandeja de: {destino_real} ...")
        cuerpo_real = formatear_examen_para_correo(examen, "Estudiante")
        exito_envio = gestor_correo.enviar_examen(
            destinatario=destino_real,
            asunto=f"Evaluacion Asignada: {examen.titulo} ({examen.id_examen})",
            cuerpo_texto=cuerpo_real,
        )
        if exito_envio:
            print(f"   [+] Correo real enviado exitosamente a: {destino_real}")
        else:
            print(f"   [-] Fallo el envio real a: {destino_real}")
    else:
        asunto = f"Asignacion de Evaluacion: {examen.titulo} ({examen.id_examen})"
        for _, nombre_est, correo_est in estudiantes:
            cuerpo = formatear_examen_para_correo(examen, nombre_est)
            gestor_correo.enviar_examen(
                destinatario=correo_est,
                asunto=asunto,
                cuerpo_texto=cuerpo,
            )

    # -------------------------------------------------------------------------
    # FASE 3: Registro de Respuestas en Almacenamiento Local (data/respuestas.json)
    # -------------------------------------------------------------------------
    print("\n" + "-" * 80)
    print("[FASE 3] Guardando respuestas de los estudiantes en almacenamiento local...")
    ruta_datos = Path("data") / "respuestas.json"
    almacenamiento = GestorAlmacenamiento(str(ruta_datos))

    respuestas_simuladas = generar_respuestas_simuladas(examen, estudiantes)
    almacenamiento.guardar_respuestas_masivas(respuestas_simuladas)

    print(f"   -> Archivo de almacenamiento: {ruta_datos.resolve()}")
    print(f"   -> Respuestas registradas exitosamente: {len(respuestas_simuladas)}")

    # Verificar lectura desde almacenamiento
    respuestas_cargadas = almacenamiento.obtener_respuestas_por_examen(examen.id_examen)
    print(f"   -> Respuestas verificadas y recuperadas desde disco: {len(respuestas_cargadas)}")

    # -------------------------------------------------------------------------
    # FASE 4: Calificación Automática y Generación de Tabla Comparativa Detallada
    # -------------------------------------------------------------------------
    print("\n" + "-" * 80)
    print("[FASE 4] Calificando y generando tabla comparativa detallada de resultados...")
    evaluador = EvaluadorNotas(escala_maxima=5.0, escala_minima=0.0)
    informe = evaluador.generar_informe_comparativo(examen, respuestas_cargadas)

    # 1. Visualización en consola con tabla ASCII y resumen
    print("\n" + informe.generar_reporte_texto())

    # 2. Demostración de exportación en formato Markdown (listo para correos o reportes web)
    print("\n" + "-" * 80)
    print("[EXPORTACIÓN ALTERNATIVA: FORMATO MARKDOWN]")
    print("-" * 80)
    tabla_markdown = generar_tabla_comparativa(informe.ranking, formato="markdown", escala_maxima=5.0)
    print(tabla_markdown)

    # -------------------------------------------------------------------------
    # FASE 5: Verificaciones Clave Solicitadas
    # -------------------------------------------------------------------------
    print("\n" + "-" * 80)
    print("[VERIFICACIÓN DE MÉTRICAS INDIVIDUALES]:")
    for r in informe.ranking:
        print(
            f"   * {r.nombre:<24} | Correctas: {r.correctas} | Incorrectas: {r.incorrectas} "
            f"| Sin Responder: {r.sin_responder} | Nota: {r.nota:.2f}/5.0"
        )
    print("\n" + "=" * 80 + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="CLI del Módulo de Gestión y Evaluación de Exámenes."
    )
    parser.add_argument(
        "--real-smtp",
        action="store_true",
        help="Realizar envío real utilizando credenciales SMTP configuradas en .env o variables de entorno.",
    )
    parser.add_argument(
        "--destinatario",
        type=str,
        default=None,
        help="Correo de destino para la prueba real (por defecto el mismo SMTP_USER).",
    )
    args = parser.parse_args()

    ejecutar_demostracion(modo_correo_real=args.real_smtp, destinatario_real=args.destinatario)


if __name__ == "__main__":
    main()
