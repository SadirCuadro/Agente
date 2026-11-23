"""
Módulo para la definición, estructuración y formateo de exámenes.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class Pregunta:
    """Representa una pregunta de opción múltiple dentro de una evaluación.

    Attributes:
        id: Identificador numérico de la pregunta (1, 2, 3...).
        enunciado: Texto de la pregunta o problema a resolver.
        opciones: Diccionario con los identificadores de opción y sus textos
          (ej. {'A': '...', 'B': '...'}).
        respuesta_correcta: Clave de la opción correcta (ej. 'A').
        puntaje_peso: Peso relativo de la pregunta para la ponderación
          (predeterminado: 1.0).
    """

    id: int
    enunciado: str
    opciones: Dict[str, str]
    respuesta_correcta: str
    puntaje_peso: float = 1.0

    def __post_init__(self) -> None:
        self.respuesta_correcta = self.respuesta_correcta.strip().upper()
        # Normalizar claves de opciones en mayúsculas
        self.opciones = {k.strip().upper(): v.strip() for k, v in self.opciones.items()}

        if not self.opciones:
            raise ValueError(f"La pregunta #{self.id} debe tener al menos una opción.")
        if self.respuesta_correcta not in self.opciones:
            raise ValueError(
                f"La respuesta correcta '{self.respuesta_correcta}' no coincide con "
                f"las opciones disponibles {list(self.opciones.keys())} en la pregunta #{self.id}."
            )
        if self.puntaje_peso <= 0:
            raise ValueError(f"El peso de la pregunta #{self.id} debe ser mayor que 0.")


@dataclass
class Examen:
    """Estructura de datos integral para un examen de evaluación.

    Attributes:
        id_examen: Código único identificador del examen (ej. 'EXAM-PY-01').
        titulo: Título formal de la prueba.
        descripcion: Instrucciones y contexto para el alumno.
        preguntas: Lista de objetos Pregunta que componen la prueba.
    """

    id_examen: str
    titulo: str
    descripcion: str
    preguntas: List[Pregunta] = field(default_factory=list)

    def agregar_pregunta(self, pregunta: Pregunta) -> None:
        """Agrega una pregunta validando que no se duplique su identificador."""
        if any(p.id == pregunta.id for p in self.preguntas):
            raise ValueError(f"Ya existe una pregunta con ID #{pregunta.id} en este examen.")
        self.preguntas.append(pregunta)

    def obtener_clave_respuestas(self) -> Dict[int, str]:
        """Retorna un diccionario con el mapa {id_pregunta: opcion_correcta}."""
        return {p.id: p.respuesta_correcta for p in self.preguntas}

    def formatear_texto_estudiante(self) -> str:
        """Genera una versión en texto plano del examen, limpia y legible,

        diseñada específicamente para ser enviada por correo electrónico a los
        estudiantes sin revelar las respuestas correctas.
        """
        lineas = [
            "=" * 70,
            f"{self.titulo.upper()} (CÓDIGO: {self.id_examen})",
            "=" * 70,
            f"Instrucciones:\n{self.descripcion.strip()}",
            "-" * 70,
            "PREGUNTAS:",
            "-" * 70,
        ]

        for p in self.preguntas:
            lineas.append(f"\nPregunta #{p.id}: {p.enunciado}")
            for letra in sorted(p.opciones.keys()):
                lineas.append(f"   [{letra}] {p.opciones[letra]}")

        lineas.extend([
            "",
            "=" * 70,
            "INSTRUCCIONES DE RESPUESTA:",
            "Para responder a esta prueba, envía un correo o mensaje indicando tus",
            "respuestas en formato de lista (ejemplo: 1: A, 2: C, 3: B).",
            "=" * 70,
        ])

        return "\n".join(lineas)

    def formatear_clave_profesor(self) -> str:
        """Genera un resumen en texto con la plantilla de corrección oficial."""
        lineas = [
            f"PLANTILLA OFICIAL DE CORRECCIÓN - {self.titulo} ({self.id_examen})",
            "-" * 60,
        ]
        for p in self.preguntas:
            lineas.append(
                f"Pregunta #{p.id}: Opción Correcta [{p.respuesta_correcta}] "
                f"- {p.opciones[p.respuesta_correcta]}"
            )
        return "\n".join(lineas)

    def to_dict(self) -> dict:
        """Serializa el examen a un diccionario estándar."""
        return {
            "id_examen": self.id_examen,
            "titulo": self.titulo,
            "descripcion": self.descripcion,
            "preguntas": [
                {
                    "id": p.id,
                    "enunciado": p.enunciado,
                    "opciones": p.opciones,
                    "respuesta_correcta": p.respuesta_correcta,
                    "puntaje_peso": p.puntaje_peso,
                }
                for p in self.preguntas
            ],
        }

    @classmethod
    def from_dict(cls, data: dict) -> Examen:
        """Reconstruye una instancia de Examen a partir de un diccionario."""
        preguntas = [
            Pregunta(
                id=item["id"],
                enunciado=item["enunciado"],
                opciones=item["opciones"],
                respuesta_correcta=item["respuesta_correcta"],
                puntaje_peso=item.get("puntaje_peso", 1.0),
            )
            for item in data.get("preguntas", [])
        ]
        return cls(
            id_examen=data["id_examen"],
            titulo=data["titulo"],
            descripcion=data.get("descripcion", ""),
            preguntas=preguntas,
        )


def formatear_examen_para_correo(examen: Examen, nombre_estudiante: Optional[str] = None) -> str:
    """Función utilitaria de nivel superior para generar el cuerpo del correo.

    Permite personalizar el saludo según el estudiante.
    """
    saludo = f"Estimado/a {nombre_estudiante},\n\n" if nombre_estudiante else "Estimado/a estudiante,\n\n"
    cuerpo = (
        f"{saludo}"
        "A continuación se presenta el examen asignado. Por favor lee atentamente "
        "cada pregunta y envía tus respuestas antes de la fecha límite.\n\n"
        f"{examen.formatear_texto_estudiante()}\n\n"
        "¡Muchos éxitos en tu evaluación!"
    )
    return cuerpo
