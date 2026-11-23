"""
Módulo para el almacenamiento local y persistente de respuestas de estudiantes.

Gestiona las respuestas en formato JSON (`data/respuestas.json`) de forma
estructurada, ligera y sin dependencias externas.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class RespuestaEstudiante:
    """Modela la respuesta formal enviada por un alumno para un examen dado.

    Attributes:
        estudiante_id: Identificador único del estudiante (cédula, carnet, o
          código).
        nombre: Nombre completo del estudiante.
        correo: Dirección de correo electrónico.
        id_examen: Identificador del examen que está respondiendo.
        respuestas: Diccionario {id_pregunta (int): opcion_elegida (str)}.
        fecha_registro: Marca de tiempo ISO de la entrega.
    """

    estudiante_id: str
    nombre: str
    correo: str
    id_examen: str
    respuestas: Dict[int, str]
    fecha_registro: str = ""

    def __post_init__(self) -> None:
        if not self.fecha_registro:
            self.fecha_registro = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Asegurar que las claves de respuesta sean enteras y las letras mayúsculas
        normalizadas: Dict[int, str] = {}
        for k, v in self.respuestas.items():
            try:
                clave_int = int(k)
                normalizadas[clave_int] = str(v).strip().upper()
            except (ValueError, TypeError):
                continue
        self.respuestas = normalizadas

    def to_dict(self) -> Dict[str, Any]:
        """Convierte la respuesta a formato serializable en JSON."""
        return {
            "estudiante_id": self.estudiante_id,
            "nombre": self.nombre,
            "correo": self.correo,
            "id_examen": self.id_examen,
            "respuestas": {str(k): v for k, v in self.respuestas.items()},
            "fecha_registro": self.fecha_registro,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> RespuestaEstudiante:
        """Crea una instancia desde un diccionario."""
        raw_resp = data.get("respuestas", {})
        resp_int = {int(k): str(v) for k, v in raw_resp.items()}
        return cls(
            estudiante_id=data["estudiante_id"],
            nombre=data["nombre"],
            correo=data["correo"],
            id_examen=data["id_examen"],
            respuestas=resp_int,
            fecha_registro=data.get("fecha_registro", ""),
        )


class GestorAlmacenamiento:
    """Controlador de lectura y escritura para el repositorio JSON local de respuestas."""

    def __init__(self, ruta_archivo: Optional[str] = None):
        """Inicializa el repositorio.

        Args:
            ruta_archivo: Ruta al archivo JSON (predeterminado:
              `data/respuestas.json`).
        """
        if ruta_archivo is None:
            # Colocar 'data' en la raíz de trabajo o adyacente al paquete
            self.ruta_archivo = Path("data") / "respuestas.json"
        else:
            self.ruta_archivo = Path(ruta_archivo)

        self._asegurar_directorio()

    def _asegurar_directorio(self) -> None:
        """Crea la carpeta contenedora si no existe."""
        self.ruta_archivo.parent.mkdir(parents=True, exist_ok=True)
        if not self.ruta_archivo.exists():
            with open(self.ruta_archivo, "w", encoding="utf-8") as f:
                json.dump([], f, indent=2, ensure_ascii=False)

    def _cargar_todos(self) -> List[Dict[str, Any]]:
        """Carga la lista sin procesar de diccionarios desde el archivo JSON."""
        self._asegurar_directorio()
        try:
            with open(self.ruta_archivo, "r", encoding="utf-8") as f:
                contenido = f.read().strip()
                if not contenido:
                    return []
                return json.loads(contenido)
        except (json.JSONDecodeError, OSError):
            return []

    def _guardar_todos(self, registros: List[Dict[str, Any]]) -> None:
        """Guarda atómicamente la lista de registros en el archivo JSON."""
        self._asegurar_directorio()
        archivo_temporal = self.ruta_archivo.with_suffix(".tmp")
        with open(archivo_temporal, "w", encoding="utf-8") as f:
            json.dump(registros, f, indent=2, ensure_ascii=False)
        # Reemplazo atómico para evitar corrupción en caso de cierre abrupto
        os.replace(archivo_temporal, self.ruta_archivo)

    def guardar_respuesta(self, respuesta: RespuestaEstudiante) -> None:
        """Guarda o actualiza la respuesta de un estudiante.

        Si el estudiante ya había enviado una respuesta para este examen, se
        actualiza con la más reciente.
        """
        registros = self._cargar_todos()
        nuevo_dict = respuesta.to_dict()

        # Buscar si ya existe para actualizarlo
        indice_existente = -1
        for i, reg in enumerate(registros):
            if (
                reg.get("estudiante_id") == respuesta.estudiante_id
                and reg.get("id_examen") == respuesta.id_examen
            ):
                indice_existente = i
                break

        if indice_existente >= 0:
            registros[indice_existente] = nuevo_dict
        else:
            registros.append(nuevo_dict)

        self._guardar_todos(registros)

    def guardar_respuestas_masivas(self, respuestas: List[RespuestaEstudiante]) -> None:
        """Guarda múltiples respuestas en una sola transacción."""
        for resp in respuestas:
            self.guardar_respuesta(resp)

    def obtener_respuestas_por_examen(self, id_examen: str) -> List[RespuestaEstudiante]:
        """Obtiene todas las respuestas entregadas para un examen específico."""
        registros = self._cargar_todos()
        return [
            RespuestaEstudiante.from_dict(r)
            for r in registros
            if r.get("id_examen") == id_examen
        ]

    def obtener_todas_las_respuestas(self) -> List[RespuestaEstudiante]:
        """Obtiene todas las respuestas almacenadas en la base de datos local."""
        registros = self._cargar_todos()
        return [RespuestaEstudiante.from_dict(r) for r in registros]

    def limpiar_respuestas(self, id_examen: Optional[str] = None) -> None:
        """Elimina respuestas de un examen dado, o vacía la base de datos si no se especifica."""
        if id_examen is None:
            self._guardar_todos([])
        else:
            registros = self._cargar_todos()
            filtrados = [r for r in registros if r.get("id_examen") != id_examen]
            self._guardar_todos(filtrados)
