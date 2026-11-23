"""
Módulo de Gestión y Evaluación de Exámenes.

Proporciona componentes autónomos y desacoplados para:
- Estructuración y formateo de exámenes de opción múltiple.
- Envío de evaluaciones por correo mediante SMTP.
- Almacenamiento local persistente de respuestas de estudiantes.
- Calificación automática y generación de informes estadísticos comparativos.
"""

from .generador_examen import Examen, Pregunta
from .gestor_correo import GestorCorreo, ConfiguracionSMTP
from .almacenamiento import GestorAlmacenamiento, RespuestaEstudiante
from .evaluador_notas import (
    EvaluadorNotas,
    ResultadoEvaluacion,
    InformeComparativo,
    generar_tabla_comparativa,
)
from .exportador_pdf import exportar_examen_pdf, exportar_clave_respuestas_pdf, crear_examen_para_agente

__all__ = [
    "Examen",
    "Pregunta",
    "GestorCorreo",
    "ConfiguracionSMTP",
    "GestorAlmacenamiento",
    "RespuestaEstudiante",
    "EvaluadorNotas",
    "ResultadoEvaluacion",
    "InformeComparativo",
    "generar_tabla_comparativa",
    "exportar_examen_pdf",
    "exportar_clave_respuestas_pdf",
    "crear_examen_para_agente",
]

__version__ = "1.0.0"
