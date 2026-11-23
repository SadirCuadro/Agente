"""
Sistema de Memoria Persistente para el Asistente de Escritorio.

Utiliza SQLite para mantener:
- Perfil y preferencias del usuario (hechos aprendidos, metas, proyectos).
- Historial de interacciones y conversaciones pasadas.
- Registro de actividad y bitácora de eventos.
- Cola y máquina de estados de tareas persistentes del agente (agent_tasks).
- Optimización de concurrencia con PRAGMA journal_mode=WAL y timeout=30.0.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

ESTADOS_VALIDOS_TAREA = ("PENDIENTE", "EN_PROGRESO", "ESPERANDO_USUARIO", "COMPLETADO", "FALLIDO")


class MemoriaPersistente:
    """Maneja la base de datos relacional, episódica y de tareas del asistente."""

    def __init__(self, ruta_db: Optional[str | Path] = None):
        if ruta_db:
            self.ruta_db = Path(ruta_db).resolve()
        else:
            raiz_proyecto = Path(__file__).resolve().parent.parent
            dir_data = raiz_proyecto / "data"
            dir_data.mkdir(parents=True, exist_ok=True)
            self.ruta_db = dir_data / "memoria_asistente.db"

        self._inicializar_tablas()

    def _conectar(self) -> sqlite3.Connection:
        """Crea una conexión SQLite segura para concurrencia con timeout=30s y modo WAL."""
        conn = sqlite3.connect(str(self.ruta_db), timeout=30.0)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.row_factory = sqlite3.Row
        return conn

    def _inicializar_tablas(self) -> None:
        """Crea el esquema inicial si no existe, garantizando persistencia segura."""
        with self._conectar() as conn:
            cursor = conn.cursor()

            # Tabla de Perfil y Hechos
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS hechos_usuario (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    clave TEXT UNIQUE NOT NULL,
                    valor TEXT NOT NULL,
                    categoria TEXT DEFAULT 'general',
                    fecha_actualizacion TEXT NOT NULL
                )
            """)

            # Tabla de Conversaciones e Interacciones
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS historial_interacciones (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rol TEXT NOT NULL,
                    mensaje TEXT NOT NULL,
                    metadatos TEXT,
                    fecha_hora TEXT NOT NULL
                )
            """)

            # Tabla de Registro de Actividades / Proactividad
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS registro_actividad (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tipo_evento TEXT NOT NULL,
                    detalle TEXT NOT NULL,
                    fecha_hora TEXT NOT NULL
                )
            """)

            # Tabla de Tareas Persistentes del Agente (Máquina de Estados)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS agent_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    objetivo TEXT NOT NULL,
                    estado TEXT NOT NULL DEFAULT 'PENDIENTE',
                    contexto_json TEXT,
                    proximo_chequeo TEXT NOT NULL,
                    intentos INTEGER DEFAULT 0,
                    resultado TEXT,
                    creado_en TEXT NOT NULL,
                    actualizado_en TEXT NOT NULL
                )
            """)

            # Índices de aceleración
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_agent_tasks_estado_proximo 
                ON agent_tasks(estado, proximo_chequeo)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_registro_actividad_fecha 
                ON registro_actividad(fecha_hora)
            """)

            conn.commit()

    # -------------------------------------------------------------------------
    # Hechos y Preferencias del Usuario
    # -------------------------------------------------------------------------
    def guardar_hecho(self, clave: str, valor: str, categoria: str = "general") -> None:
        """Guarda o actualiza un hecho sobre el usuario."""
        ahora = datetime.now().isoformat()
        with self._conectar() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO hechos_usuario (clave, valor, categoria, fecha_actualizacion)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(clave) DO UPDATE SET
                    valor = excluded.valor,
                    categoria = excluded.categoria,
                    fecha_actualizacion = excluded.fecha_actualizacion
            """, (clave.strip().lower(), valor.strip(), categoria, ahora))
            conn.commit()

    def obtener_hecho(self, clave: str) -> Optional[str]:
        """Obtiene un hecho por su clave."""
        with self._conectar() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT valor FROM hechos_usuario WHERE clave = ?", (clave.strip().lower(),))
            fila = cursor.fetchone()
            return fila["valor"] if fila else None

    def obtener_todos_los_hechos(self) -> Dict[str, str]:
        """Devuelve un diccionario con todos los hechos y preferencias conocidas."""
        with self._conectar() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT clave, valor FROM hechos_usuario ORDER BY categoria, clave")
            filas = cursor.fetchall()
            return {fila["clave"]: fila["valor"] for fila in filas}

    # -------------------------------------------------------------------------
    # Historial de Conversaciones
    # -------------------------------------------------------------------------
    def registrar_mensaje(self, rol: str, mensaje: str, metadatos: Optional[Dict[str, Any]] = None) -> None:
        """Registra un mensaje en el historial."""
        ahora = datetime.now().isoformat()
        meta_str = json.dumps(metadatos, ensure_ascii=False) if metadatos else None
        with self._conectar() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO historial_interacciones (rol, mensaje, metadatos, fecha_hora)
                VALUES (?, ?, ?, ?)
            """, (rol, mensaje, meta_str, ahora))
            conn.commit()

    def obtener_ultimos_mensajes(self, limite: int = 10) -> List[Dict[str, Any]]:
        """Recupera los últimos N mensajes para contexto de conversación."""
        with self._conectar() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT rol, mensaje, metadatos, fecha_hora
                FROM historial_interacciones
                ORDER BY id DESC
                LIMIT ?
            """, (limite,))
            filas = cursor.fetchall()
            mensajes = []
            for f in reversed(filas):
                mensajes.append({
                    "rol": f["rol"],
                    "mensaje": f["mensaje"],
                    "metadatos": json.loads(f["metadatos"]) if f["metadatos"] else None,
                    "fecha_hora": f["fecha_hora"]
                })
            return mensajes

    def buscar_en_historial(self, termino: str, limite: int = 5) -> List[Dict[str, Any]]:
        """Busca interacciones pasadas que contengan el término."""
        with self._conectar() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT rol, mensaje, fecha_hora
                FROM historial_interacciones
                WHERE mensaje LIKE ?
                ORDER BY id DESC
                LIMIT ?
            """, (f"%{termino}%", limite))
            filas = cursor.fetchall()
            return [{"rol": f["rol"], "mensaje": f["mensaje"], "fecha_hora": f["fecha_hora"]} for f in filas]

    # -------------------------------------------------------------------------
    # Registro de Actividades / Eventos
    # -------------------------------------------------------------------------
    def registrar_actividad(self, tipo_evento: str, detalle: str) -> None:
        """Registra un evento proactivo o de sistema."""
        ahora = datetime.now().isoformat()
        with self._conectar() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO registro_actividad (tipo_evento, detalle, fecha_hora)
                VALUES (?, ?, ?)
            """, (tipo_evento, detalle, ahora))
            conn.commit()

    def obtener_resumen_actividad_reciente(self, horas: int = 24) -> List[Dict[str, str]]:
        """Recupera las actividades ocurridas en las últimas horas."""
        limite_tiempo = (datetime.now() - timedelta(hours=horas)).isoformat()
        with self._conectar() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT tipo_evento, detalle, fecha_hora
                FROM registro_actividad
                WHERE fecha_hora >= ?
                ORDER BY id DESC
            """, (limite_tiempo,))
            filas = cursor.fetchall()
            return [{"tipo": f["tipo_evento"], "detalle": f["detalle"], "fecha_hora": f["fecha_hora"]} for f in filas]

    # -------------------------------------------------------------------------
    # Máquina de Estados y Cola de Tareas Persistentes (agent_tasks)
    # -------------------------------------------------------------------------
    def crear_tarea(
        self,
        objetivo: str,
        contexto: Optional[Dict[str, Any]] = None,
        minutos_espera: int = 0
    ) -> int:
        """
        Crea una nueva tarea persistente en la cola del agente.
        
        Args:
            objetivo: Descripción clara de lo que el agente debe hacer o monitorear.
            contexto: Metadatos o estado previo serializable.
            minutos_espera: Tiempo a esperar antes de que la tarea sea elegible para ejecución.
        """
        ahora_dt = datetime.now()
        ahora = ahora_dt.isoformat()
        proximo_dt = ahora_dt + timedelta(minutes=max(0, minutos_espera))
        proximo_chequeo = proximo_dt.isoformat()
        contexto_str = json.dumps(contexto or {}, ensure_ascii=False)

        with self._conectar() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO agent_tasks (
                    objetivo, estado, contexto_json, proximo_chequeo,
                    intentos, resultado, creado_en, actualizado_en
                )
                VALUES (?, 'PENDIENTE', ?, ?, 0, NULL, ?, ?)
            """, (objetivo.strip(), contexto_str, proximo_chequeo, ahora, ahora))
            conn.commit()
            return int(cursor.lastrowid)

    def obtener_tarea(self, tarea_id: int) -> Optional[Dict[str, Any]]:
        """Recupera una tarea persistente específica por su identificador."""
        with self._conectar() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, objetivo, estado, contexto_json, proximo_chequeo, intentos,
                       resultado, creado_en, actualizado_en
                FROM agent_tasks
                WHERE id = ?
            """, (tarea_id,))
            fila = cursor.fetchone()
            if not fila:
                return None
            return {
                "id": fila["id"],
                "objetivo": fila["objetivo"],
                "estado": fila["estado"],
                "contexto": json.loads(fila["contexto_json"]) if fila["contexto_json"] else {},
                "proximo_chequeo": fila["proximo_chequeo"],
                "intentos": fila["intentos"],
                "resultado": fila["resultado"],
                "creado_en": fila["creado_en"],
                "actualizado_en": fila["actualizado_en"],
            }

    def obtener_tareas(
        self,
        estado: Optional[str] = None,
        limite: int = 20
    ) -> List[Dict[str, Any]]:
        """Consulta la lista de tareas persistentes, opcionalmente filtradas por estado."""
        with self._conectar() as conn:
            cursor = conn.cursor()
            if estado:
                cursor.execute("""
                    SELECT id, objetivo, estado, contexto_json, proximo_chequeo, intentos,
                           resultado, creado_en, actualizado_en
                    FROM agent_tasks
                    WHERE estado = ?
                    ORDER BY id DESC
                    LIMIT ?
                """, (estado.strip().upper(), limite))
            else:
                cursor.execute("""
                    SELECT id, objetivo, estado, contexto_json, proximo_chequeo, intentos,
                           resultado, creado_en, actualizado_en
                    FROM agent_tasks
                    ORDER BY id DESC
                    LIMIT ?
                """, (limite,))

            filas = cursor.fetchall()
            resultado = []
            for f in filas:
                resultado.append({
                    "id": f["id"],
                    "objetivo": f["objetivo"],
                    "estado": f["estado"],
                    "contexto": json.loads(f["contexto_json"]) if f["contexto_json"] else {},
                    "proximo_chequeo": f["proximo_chequeo"],
                    "intentos": f["intentos"],
                    "resultado": f["resultado"],
                    "creado_en": f["creado_en"],
                    "actualizado_en": f["actualizado_en"],
                })
            return resultado

    def actualizar_estado_tarea(
        self,
        tarea_id: int,
        estado: str,
        resultado: Optional[str] = None,
        minutos_proximo_chequeo: Optional[int] = None
    ) -> bool:
        """
        Actualiza el estado de una tarea y registra su resultado o nueva fecha de chequeo.
        Estados válidos: PENDIENTE, EN_PROGRESO, ESPERANDO_USUARIO, COMPLETADO, FALLIDO.
        """
        estado_normalizado = estado.strip().upper()
        if estado_normalizado not in ESTADOS_VALIDOS_TAREA:
            raise ValueError(f"Estado inválido: {estado}. Debe ser uno de {ESTADOS_VALIDOS_TAREA}")

        ahora_dt = datetime.now()
        ahora = ahora_dt.isoformat()

        with self._conectar() as conn:
            cursor = conn.cursor()
            if minutos_proximo_chequeo is not None:
                proximo = (ahora_dt + timedelta(minutes=max(0, minutos_proximo_chequeo))).isoformat()
                cursor.execute("""
                    UPDATE agent_tasks
                    SET estado = ?, resultado = COALESCE(?, resultado), proximo_chequeo = ?, actualizado_en = ?
                    WHERE id = ?
                """, (estado_normalizado, resultado, proximo, ahora, tarea_id))
            else:
                cursor.execute("""
                    UPDATE agent_tasks
                    SET estado = ?, resultado = COALESCE(?, resultado), actualizado_en = ?
                    WHERE id = ?
                """, (estado_normalizado, resultado, ahora, tarea_id))
            conn.commit()
            return cursor.rowcount > 0

    def posponer_tarea(self, tarea_id: int, minutos_demora: int = 15, razon: Optional[str] = None) -> bool:
        """Pospone una tarea N minutos sin marcarla como fallida."""
        ahora_dt = datetime.now()
        proximo = (ahora_dt + timedelta(minutes=max(1, minutos_demora))).isoformat()
        ahora = ahora_dt.isoformat()

        with self._conectar() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE agent_tasks
                SET estado = 'PENDIENTE',
                    proximo_chequeo = ?,
                    resultado = COALESCE(?, resultado),
                    actualizado_en = ?
                WHERE id = ?
            """, (proximo, f"Pospuesta: {razon}" if razon else None, ahora, tarea_id))
            conn.commit()
            return cursor.rowcount > 0

    def incrementar_intentos_tarea(self, tarea_id: int) -> int:
        """Incrementa el contador de intentos de una tarea."""
        ahora = datetime.now().isoformat()
        with self._conectar() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE agent_tasks
                SET intentos = intentos + 1, actualizado_en = ?
                WHERE id = ?
            """, (ahora, tarea_id))
            conn.commit()
            cursor.execute("SELECT intentos FROM agent_tasks WHERE id = ?", (tarea_id,))
            fila = cursor.fetchone()
            return fila["intentos"] if fila else 0

    def obtener_tareas_vencidas(self, limite: int = 10) -> List[Dict[str, Any]]:
        """Recupera tareas en estado PENDIENTE o EN_PROGRESO cuya fecha de chequeo ya venció."""
        ahora = datetime.now().isoformat()
        with self._conectar() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, objetivo, estado, contexto_json, proximo_chequeo, intentos,
                       resultado, creado_en, actualizado_en
                FROM agent_tasks
                WHERE estado IN ('PENDIENTE', 'EN_PROGRESO')
                  AND proximo_chequeo <= ?
                ORDER BY proximo_chequeo ASC
                LIMIT ?
            """, (ahora, limite))
            filas = cursor.fetchall()
            resultado = []
            for f in filas:
                resultado.append({
                    "id": f["id"],
                    "objetivo": f["objetivo"],
                    "estado": f["estado"],
                    "contexto": json.loads(f["contexto_json"]) if f["contexto_json"] else {},
                    "proximo_chequeo": f["proximo_chequeo"],
                    "intentos": f["intentos"],
                    "resultado": f["resultado"],
                    "creado_en": f["creado_en"],
                    "actualizado_en": f["actualizado_en"],
                })
            return resultado

    def reanudar_tareas_pendientes(self) -> List[Dict[str, Any]]:
        """
        Recupera automáticamente todas las tareas PENDIENTE o EN_PROGRESO al iniciar
        el asistente tras un reinicio de Windows o arranque de la aplicación.
        """
        with self._conectar() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, objetivo, estado, contexto_json, proximo_chequeo, intentos,
                       resultado, creado_en, actualizado_en
                FROM agent_tasks
                WHERE estado IN ('PENDIENTE', 'EN_PROGRESO')
                ORDER BY proximo_chequeo ASC
            """)
            filas = cursor.fetchall()
            tareas = []
            for f in filas:
                tareas.append({
                    "id": f["id"],
                    "objetivo": f["objetivo"],
                    "estado": f["estado"],
                    "contexto": json.loads(f["contexto_json"]) if f["contexto_json"] else {},
                    "proximo_chequeo": f["proximo_chequeo"],
                    "intentos": f["intentos"],
                    "resultado": f["resultado"],
                    "creado_en": f["creado_en"],
                    "actualizado_en": f["actualizado_en"],
                })

            if tareas:
                self.registrar_actividad(
                    "reanudacion_tareas",
                    f"Se reanudaron {len(tareas)} tarea(s) persistente(s) pendiente(s) al arrancar el sistema."
                )
            return tareas

    def limpiar_registros_antiguos(self, dias_retencion: int = 30) -> Dict[str, int]:
        """
        Rutina de mantenimiento nocturno: purga bitácoras de actividad y tareas completadas/fallidas
        con antigüedad mayor a dias_retencion días para mantener la base de datos óptima y compacta.
        """
        limite = (datetime.now() - timedelta(days=max(1, dias_retencion))).isoformat()
        with self._conectar() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM registro_actividad WHERE fecha_hora < ?", (limite,))
            actividades_borradas = cursor.rowcount

            cursor.execute("""
                DELETE FROM agent_tasks
                WHERE estado IN ('COMPLETADO', 'FALLIDO')
                  AND actualizado_en < ?
            """, (limite,))
            tareas_borradas = cursor.rowcount

            conn.commit()
            return {
                "actividades_borradas": actividades_borradas,
                "tareas_borradas": tareas_borradas
            }
