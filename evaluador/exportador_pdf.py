"""
Módulo para exportar exámenes en formato PDF con diseño visual profesional.

Utiliza PySide6 (QPdfWriter y QTextDocument) para generar documentos PDF
nativos a partir de HTML/CSS estructurado, sin requerir librerías adicionales.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

if __name__ == "__main__" and __package__ is None:
    ruta_raiz = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(ruta_raiz))
    from evaluador.generador_examen import Examen, Pregunta
else:
    from .generador_examen import Examen, Pregunta


def generar_html_examen(examen: Examen) -> str:
    """Genera el contenido HTML/CSS con diseño profesional para el examen en PDF."""
    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
    body {{
        font-family: Arial, Helvetica, sans-serif;
        color: #1f2937;
        margin: 20px;
        line-height: 1.4;
    }}
    .encabezado {{
        border-bottom: 3px solid #2563eb;
        padding-bottom: 12px;
        margin-bottom: 18px;
    }}
    .titulo {{
        font-size: 22px;
        font-weight: bold;
        color: #1e3a8a;
        margin: 0 0 6px 0;
    }}
    .subtitulo {{
        font-size: 13px;
        color: #4b5563;
        margin: 0;
    }}
    .caja-datos {{
        background-color: #f3f4f6;
        border: 1px solid #d1d5db;
        border-radius: 6px;
        padding: 10px 14px;
        margin-bottom: 18px;
        font-size: 12px;
    }}
    .fila-datos {{
        margin-bottom: 4px;
    }}
    .caja-instrucciones {{
        background-color: #eff6ff;
        border-left: 4px solid #3b82f6;
        padding: 10px 14px;
        margin-bottom: 20px;
        font-size: 12px;
        color: #1e40af;
    }}
    .pregunta-bloque {{
        background-color: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 6px;
        padding: 12px 16px;
        margin-bottom: 16px;
        page-break-inside: avoid;
    }}
    .pregunta-titulo {{
        font-size: 13px;
        font-weight: bold;
        color: #111827;
        margin-bottom: 10px;
    }}
    .opcion {{
        margin-left: 14px;
        margin-bottom: 6px;
        font-size: 12px;
        color: #374151;
    }}
    .badge {{
        font-weight: bold;
        color: #2563eb;
    }}
    .pie-pagina {{
        margin-top: 30px;
        text-align: center;
        font-size: 10px;
        color: #9ca3af;
        border-top: 1px solid #e5e7eb;
        padding-top: 8px;
    }}
</style>
</head>
<body>

<div class="encabezado">
    <div class="titulo">{examen.titulo}</div>
    <div class="subtitulo">Código de Evaluación: <b>{examen.id_examen}</b> | Sistema de Evaluación Automatizada</div>
</div>

<div class="caja-datos">
    <div class="fila-datos"><b>Nombre del Estudiante / Candidato:</b> __________________________________________________</div>
    <div class="fila-datos"><b>Correo Electrónico:</b> ___________________________  <b>Fecha:</b> _______________________</div>
</div>

<div class="caja-instrucciones">
    <b>INSTRUCCIONES GENERALES:</b><br>
    {examen.descripcion.replace('\n', '<br>')}
</div>
"""

    for p in examen.preguntas:
        html += f"""
<div class="pregunta-bloque">
    <div class="pregunta-titulo">Pregunta #{p.id}: {p.enunciado}</div>
"""
        for letra in sorted(p.opciones.keys()):
            texto_opcion = p.opciones[letra]
            html += f"""    <div class="opcion"><span class="badge">[{letra}]</span> &nbsp; {texto_opcion}</div>\n"""
        html += "</div>\n"

    html += f"""
<div class="pie-pagina">
    Documento oficial generado por el Módulo de Evaluación | {examen.id_examen}
</div>
</body>
</html>
"""
    return html


def exportar_examen_pdf(examen: Examen, ruta_salida: str | Path) -> Path:
    """Exporta una instancia de Examen a un archivo PDF estructurado y estilizado.

    Args:
        examen: Objeto Examen a procesar.
        ruta_salida: Ruta de destino donde se guardará el archivo PDF.

    Returns:
        Path del archivo PDF generado.
    """
    # Forzar ejecución offscreen (headless) para compatibilidad sin interfaz gráfica
    os.environ["QT_QPA_PLATFORM"] = "offscreen"

    from PySide6.QtGui import QGuiApplication, QPageLayout, QPageSize, QPdfWriter, QTextDocument

    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication([])

    ruta_pdf = Path(ruta_salida).resolve()
    ruta_pdf.parent.mkdir(parents=True, exist_ok=True)

    html_contenido = generar_html_examen(examen)

    doc = QTextDocument()
    doc.setHtml(html_contenido)

    writer = QPdfWriter(str(ruta_pdf))
    writer.setPageSize(QPageSize(QPageSize.A4))
    writer.setPageMargins(QPageLayout().margins())
    writer.setResolution(150)

    doc.print_(writer)

    return ruta_pdf


def crear_examen_para_agente() -> Examen:
    """Crea un examen completo y riguroso de Python e Inteligencia Artificial,

    ideal para poner a prueba las capacidades de análisis y resolución del
    agente Gemini.
    """
    examen = Examen(
        id_examen="EVAL-IA-AGENTE-2026",
        titulo="Evaluación Integral: Fundamentos de Python, Algoritmos e Inteligencia Artificial",
        descripcion=(
            "Responde cada una de las siguientes preguntas seleccionando la opción correcta.\n"
            "Este examen evalúa conceptos de estructuras de datos, complejidad temporal (Big O),\n"
            "arquitectura de Modelos de Lenguaje (LLMs), tokenización y gestión de errores en Python."
        ),
    )

    examen.agregar_pregunta(
        Pregunta(
            id=1,
            enunciado="¿Cuál es la diferencia fundamental entre una lista (list) y un generador (generator expression) en Python respecto al uso de memoria?",
            opciones={
                "A": "Las listas son inmutables mientras que los generadores son mutables.",
                "B": "Las listas cargan todos los elementos en memoria inmediatamente, mientras que los generadores producen elementos bajo demanda (lazy evaluation).",
                "C": "Los generadores ocupan el doble de memoria porque guardan el estado de iteración en disco.",
                "D": "No existe ninguna diferencia en el consumo de memoria; ambos reservan punteros contiguos.",
            },
            respuesta_correcta="B",
        )
    )

    examen.agregar_pregunta(
        Pregunta(
            id=2,
            enunciado="En el contexto de Procesamiento de Lenguaje Natural (NLP) y Grandes Modelos de Lenguaje (LLMs), ¿qué es la 'Tokenización'?",
            opciones={
                "A": "El proceso de cifrado de contraseñas mediante tokens JWT.",
                "B": "La conversión de texto en unidades numéricas o subpalabras que el modelo puede procesar.",
                "C": "El almacenamiento persistente de pesos en la memoria VRAM de la GPU.",
                "D": "La técnica de aumentar la temperatura de muestreo para generar respuestas creativas.",
            },
            respuesta_correcta="B",
        )
    )

    examen.agregar_pregunta(
        Pregunta(
            id=3,
            enunciado="En la arquitectura Transformer utilizada por Gemini, ¿cuál es el mecanismo principal que le permite al modelo ponderar la relevancia de diferentes palabras en una secuencia?",
            opciones={
                "A": "Mecanismo de Auto-Atención (Self-Attention).",
                "B": "Redes Neuronales Recurrentes Bidireccionales (BiLSTM).",
                "C": "Convolución Espacial Discreta 2D.",
                "D": "Descenso de Gradiente Estocástico con Momentum.",
            },
            respuesta_correcta="A",
        )
    )

    examen.agregar_pregunta(
        Pregunta(
            id=4,
            enunciado="¿Cuál es la complejidad temporal promedio para buscar una clave en un diccionario (hash map) de Python?",
            opciones={
                "A": "O(log n)",
                "B": "O(n)",
                "C": "O(1)",
                "D": "O(n log n)",
            },
            respuesta_correcta="C",
        )
    )

    examen.agregar_pregunta(
        Pregunta(
            id=5,
            enunciado="¿Qué bloque de código se ejecuta SIEMPRE en una estructura try/except/finally en Python, independientemente de si ocurre una excepción o no?",
            opciones={
                "A": "El bloque except.",
                "B": "El bloque else.",
                "C": "El bloque finally.",
                "D": "Ningún bloque si la excepción no fue capturada.",
            },
            respuesta_correcta="C",
        )
    )

    return examen


def generar_html_clave_respuestas(examen: Examen, justificaciones: Optional[dict[int, dict]] = None) -> str:
    """Genera el contenido HTML/CSS profesional para la plantilla oficial de respuestas."""
    if justificaciones is None:
        justificaciones = {
            1: {
                "tema": "Python & Estructuras de Datos (Generadores vs Listas)",
                "correcta": "B",
                "justificacion": (
                    "Las listas en Python almacenan todos sus elementos de forma contigua en memoria (eager evaluation), "
                    "mientras que los generadores implementan el protocolo iterador con ejecución diferida (lazy evaluation), "
                    "produciendo cada valor bajo demanda con rendimiento de memoria O(1)."
                ),
                "distractores": (
                    "[A] Falso: las tuplas son inmutables, pero las listas son mutables. "
                    "[C] Falso: los generadores retienen su estado en marcos de pila (stack frames) en RAM, no en disco. "
                    "[D] Falso: el consumo de memoria en generadores es sustancialmente menor ante colecciones extensas."
                ),
            },
            2: {
                "tema": "NLP y Arquitectura de LLMs (Tokenización)",
                "correcta": "B",
                "justificacion": (
                    "Los modelos de lenguaje procesan representaciones numéricas. La tokenización (ej. BPE, WordPiece, SentencePiece) "
                    "fracciona el texto crudo en subpalabras y asigna a cada una un ID entero del vocabulario antes de la capa de embeddings."
                ),
                "distractores": (
                    "[A] Distractor: confunde tokens de autenticación web (JWT/OAuth) con tokens lingüísticos de LLMs. "
                    "[C] Falso: la memoria VRAM almacena parámetros y tensores de activación, no es la definición de tokenización. "
                    "[D] Falso: la temperatura es un hiperparámetro de decodificación/muestreo (softmax temperature)."
                ),
            },
            3: {
                "tema": "Arquitectura Transformer (Auto-Atención / Self-Attention)",
                "correcta": "A",
                "justificacion": (
                    "El mecanismo de Auto-Atención (Self-Attention / Multi-Head Attention) calcula matrices de Query (Q), Key (K) y Value (V), "
                    "permitiendo calcular dependencias globales y relaciones semánticas entre todos los tokens en paralelo."
                ),
                "distractores": (
                    "[B] Falso: las BiLSTMs procesan secuencias paso a paso de forma recurrente, no son la base de los Transformers. "
                    "[C] Falso: las convoluciones 2D son predominantes en visión computacional (CNNs). "
                    "[D] Falso: el optimizador estocástico entrena los pesos, pero no es el mecanismo de ponderación secuencial del modelo."
                ),
            },
            4: {
                "tema": "Algoritmos y Estructuras de Datos (Complejidad de Hash Maps)",
                "correcta": "C",
                "justificacion": (
                    "Los diccionarios en Python están implementados como tablas hash dispersas compactas con direccionamiento abierto. "
                    "El cálculo de la función hash del objeto permite acceder a la entrada directamente en tiempo constante O(1) promedio."
                ),
                "distractores": (
                    "[A] O(log n) corresponde a estructuras jerárquicas como árboles de búsqueda binaria balanceados (AVL, Red-Black). "
                    "[B] O(n) es la complejidad de búsqueda lineal en listas no ordenadas o el peor caso de colisiones masivas en hash maps. "
                    "[D] O(n log n) es la cota asintótica de algoritmos óptimos de ordenación (MergeSort, Timsort)."
                ),
            },
            5: {
                "tema": "Python y Manejo Robusto de Excepciones (Bloque finally)",
                "correcta": "C",
                "justificacion": (
                    "La cláusula `finally` en Python está garantizada por el intérprete para ejecutarse siempre al salir del bloque try/except, "
                    "incluso si ocurre una excepción no capturada, un return anticipado o una llamada a sys.exit(), siendo idónea para liberación de recursos."
                ),
                "distractores": (
                    "[A] Falso: el bloque `except` únicamente se dispara si se produce una excepción coincidente. "
                    "[B] Falso: el bloque `else` se ejecuta únicamente si el bloque `try` finalizó sin lanzar excepciones. "
                    "[D] Falso: `finally` se ejecuta incluso frente a excepciones no interceptadas antes de propagarlas al invocador."
                ),
            },
        }

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
    body {{
        font-family: Arial, Helvetica, sans-serif;
        color: #1f2937;
        margin: 20px;
        line-height: 1.4;
    }}
    .encabezado {{
        border-bottom: 3px solid #059669;
        padding-bottom: 12px;
        margin-bottom: 16px;
    }}
    .titulo {{
        font-size: 20px;
        font-weight: bold;
        color: #065f46;
        margin: 0 0 6px 0;
    }}
    .subtitulo {{
        font-size: 12px;
        color: #4b5563;
        margin: 0;
    }}
    .caja-info {{
        background-color: #ecfdf5;
        border-left: 4px solid #10b981;
        padding: 10px 14px;
        margin-bottom: 18px;
        font-size: 11px;
        color: #064e3b;
    }}
    table {{
        width: 100%;
        border-collapse: collapse;
        margin-bottom: 20px;
        font-size: 11px;
    }}
    th {{
        background-color: #065f46;
        color: #ffffff;
        padding: 8px 10px;
        text-align: left;
    }}
    td {{
        border: 1px solid #d1d5db;
        padding: 7px 10px;
    }}
    tr:nth-child(even) {{
        background-color: #f9fafb;
    }}
    .badge-verde {{
        display: inline-block;
        background-color: #10b981;
        color: #ffffff;
        font-weight: bold;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 11px;
    }}
    .pregunta-item {{
        background-color: #ffffff;
        border: 1px solid #e5e7eb;
        border-left: 4px solid #059669;
        border-radius: 4px;
        padding: 10px 14px;
        margin-bottom: 14px;
        page-break-inside: avoid;
    }}
    .pregunta-titulo {{
        font-size: 12px;
        font-weight: bold;
        color: #111827;
        margin-bottom: 6px;
    }}
    .explicacion {{
        font-size: 11px;
        color: #374151;
        margin-top: 4px;
    }}
    .distractores {{
        font-size: 10px;
        color: #6b7280;
        margin-top: 4px;
        background-color: #f9fafb;
        padding: 6px 8px;
        border-radius: 4px;
    }}
    .pie-pagina {{
        margin-top: 24px;
        text-align: center;
        font-size: 10px;
        color: #9ca3af;
        border-top: 1px solid #e5e7eb;
        padding-top: 6px;
    }}
</style>
</head>
<body>

<div class="encabezado">
    <div class="titulo">PLANTILLA OFICIAL DE CORRECCIÓN Y RÚBRICA DE EVALUACIÓN</div>
    <div class="subtitulo">Examen: <b>{examen.titulo}</b> | Código: <b>{examen.id_examen}</b></div>
</div>

<div class="caja-info">
    <b>USO DEL DOCUMENTO:</b> Esta plantilla contiene la matriz oficial de respuestas correctas, ponderaciones y justificaciones técnicas rigurosas. 
    Permite al <b>agente de inteligencia artificial</b> o evaluador comparar de forma automatizada las respuestas del alumno, 
    calcular la nota exacta sobre la escala 0.0 a 5.0 y ofrecer retroalimentación constructiva.
</div>

<h3>TABLA RESUMEN DE RESPUESTAS OFICIALES</h3>
<table>
    <thead>
        <tr>
            <th style="width: 12%;">Ítem</th>
            <th style="width: 15%;">Opción Correcta</th>
            <th style="width: 48%;">Tema / Competencia Evaluada</th>
            <th style="width: 13%;">Puntaje Peso</th>
            <th style="width: 12%;">Equivalencia</th>
        </tr>
    </thead>
    <tbody>
"""

    for p in examen.preguntas:
        datos = justificaciones.get(p.id, {"tema": "Fundamentos", "correcta": p.respuesta_correcta})
        html += f"""
        <tr>
            <td><b>Pregunta #{p.id}</b></td>
            <td><span class="badge-verde">Opción [{p.respuesta_correcta}]</span></td>
            <td>{datos.get('tema', 'Evaluación Técnica')}</td>
            <td>1.0 pt</td>
            <td>20% (1.0 / 5.0)</td>
        </tr>
"""

    html += """
    </tbody>
</table>

<h3>JUSTIFICACIÓN TÉCNICA DETALLADA Y ANÁLISIS DE OPCIONES</h3>
"""

    for p in examen.preguntas:
        datos = justificaciones.get(p.id, {})
        just_texto = datos.get("justificacion", f"La opción [{p.respuesta_correcta}] es la respuesta correcta conforme a la especificación estándar.")
        dist_texto = datos.get("distractores", "")

        html += f"""
<div class="pregunta-item">
    <div class="pregunta-titulo">Pregunta #{p.id}: {p.enunciado}</div>
    <div><b>Respuesta Correcta Oficial:</b> <span class="badge-verde">[{p.respuesta_correcta}] {p.opciones[p.respuesta_correcta]}</span></div>
    <div class="explicacion"><b>Justificación Técnica:</b> {just_texto}</div>
"""
        if dist_texto:
            html += f"""    <div class="distractores"><b>Análisis de opciones incorrectas:</b><br>{dist_texto}</div>\n"""
        html += "</div>\n"

    html += f"""
<div class="pie-pagina">
    Plantilla de Calificación y Rúbrica Oficial | Módulo de Evaluación | {examen.id_examen}
</div>
</body>
</html>
"""
    return html


def exportar_clave_respuestas_pdf(examen: Examen, ruta_salida: str | Path) -> Path:
    """Exporta la plantilla oficial de respuestas con justificaciones a PDF."""
    os.environ["QT_QPA_PLATFORM"] = "offscreen"

    from PySide6.QtGui import QGuiApplication, QPageLayout, QPageSize, QPdfWriter, QTextDocument

    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication([])

    ruta_pdf = Path(ruta_salida).resolve()
    ruta_pdf.parent.mkdir(parents=True, exist_ok=True)

    html_contenido = generar_html_clave_respuestas(examen)

    doc = QTextDocument()
    doc.setHtml(html_contenido)

    writer = QPdfWriter(str(ruta_pdf))
    writer.setPageSize(QPageSize(QPageSize.A4))
    writer.setPageMargins(QPageLayout().margins())
    writer.setResolution(150)

    doc.print_(writer)

    return ruta_pdf


if __name__ == "__main__":
    examen_prueba = crear_examen_para_agente()

    # 1. Exportar Examen para Estudiantes/Agente
    ruta_examen = Path("examen_evaluacion_agente.pdf")
    pdf_examen = exportar_examen_pdf(examen_prueba, ruta_examen)
    print(f"[OK] 1. Examen para estudiante generado: {pdf_examen}")

    # 2. Exportar Plantilla Oficial de Corrección con Opciones Buenas
    ruta_clave = Path("plantilla_respuestas_correctas.pdf")
    pdf_clave = exportar_clave_respuestas_pdf(examen_prueba, ruta_clave)
    print(f"[OK] 2. Plantilla oficial de corrección generada: {pdf_clave}")

