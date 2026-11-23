"""
Motor Proactivo Asíncrono Seguro para PySide6 (Segundo Plano).

Responsabilidades:
- Monitoreo periódico en un hilo independiente (QThread) para no congelar la interfaz Qt.
- Heartbeat eficiente cada 60 segundos con verificación local previa (ahorro de tokens de Gemini).
- Verificación de reuniones en Google Calendar (notificación preventiva 15 min antes).
- Verificación y avance autónomo de tareas vencidas en la cola persistente `agent_tasks`.
- Generación del briefing matutino una vez al día.
- Consolidación nocturna diaria de memoria (resumen en Obsidian y mantenimiento de SQLite).
- Tolerancia a fallos de red con retroceso exponencial (Exponential Backoff).
"""

from __future__ import annotations

import json
import logging
import time
from datetime import date, datetime, timedelta, timezone
from typing import Optional, Set

from PySide6.QtCore import QThread, Signal

from asistente.cerebro_gemini import CerebroGemini

logger = logging.getLogger("MotorProactivo")


class MotorProactivo(QThread):
    """
    Hilo de trabajo en segundo plano para eventos proactivos, alarmas y
    procesamiento asíncrono de tareas del asistente.
    """

    notificacion_solicitada = Signal(str, str)  # (titulo, mensaje)
    briefing_listo = Signal(str)                # texto del briefing generado
    tarea_actualizada = Signal(int, str, str)   # (tarea_id, estado, detalle)
    consolidacion_listo = Signal(str)           # texto de consolidacion nocturna

    def __init__(self, cerebro: CerebroGemini, intervalo_chequeo_segundos: int = 60):
        super().__init__()
        self.cerebro = cerebro
        self.intervalo_segundos = max(10, intervalo_chequeo_segundos)

        self._ejecutando = False
        self._fecha_ultimo_briefing: Optional[str] = None
        self._fecha_ultima_consolidacion: Optional[str] = None
        self._eventos_notificados: Set[str] = set()

        # Control de Exponential Backoff ante caídas de red o cuota de la API
        self._fallos_consecutivos = 0
        self._backoff_hasta: float = 0.0

        # Peticiones manuales inmediatas
        self._briefing_forzado = False
        self._consolidacion_forzada = False

    # -------------------------------------------------------------------------
    # Control del Ciclo de Vida del Hilo
    # -------------------------------------------------------------------------
    def iniciar(self) -> None:
        """Inicia el hilo de ejecución si no está corriendo."""
        if not self.isRunning():
            self._ejecutando = True
            self.start()

    def detener(self) -> None:
        """Detiene de forma limpia el bucle de ejecución."""
        self._ejecutando = False
        self.wait(3000)

    def solicitar_briefing_inmediato(self) -> None:
        """Fuerza la ejecución inmediata del briefing matutino."""
        self._briefing_forzado = True

    def solicitar_consolidacion_inmediata(self) -> None:
        """Fuerza la ejecución inmediata de la consolidación nocturna."""
        self._consolidacion_forzada = True

    # -------------------------------------------------------------------------
    # Bucle Principal de Ejecución (QThread.run)
    # -------------------------------------------------------------------------
    def run(self) -> None:
        """Bucle de heartbeat que corre en el hilo secundario."""
        self._ejecutando = True

        # Reanudación automática de tareas tras inicio de sesión / reinicio de Windows
        self._reanudar_tareas_iniciales()

        while self._ejecutando:
            tiempo_actual = time.time()

            # Comprobar si estamos en período de enfriamiento por backoff de red
            if tiempo_actual < self._backoff_hasta:
                self.msleep(1500)
                continue

            try:
                self._ejecutar_ciclo_heartbeat()
                # Éxito: restablecer contador de fallos consecutivos
                self._fallos_consecutivos = 0
            except Exception as exc:
                self._manejar_error_con_backoff(exc)

            # Espera de 60 segundos fraccionada para responder rápidamente a detener()
            for _ in range(self.intervalo_segundos):
                if not self._ejecutando or self._briefing_forzado or self._consolidacion_forzada:
                    break
                self.msleep(1000)

    # -------------------------------------------------------------------------
    # Tareas de Inicio
    # -------------------------------------------------------------------------
    def _reanudar_tareas_iniciales(self) -> None:
        """Carga tareas incompletas al iniciar el servicio."""
        try:
            pendientes = self.cerebro.memoria.reanudar_tareas_pendientes()
            if pendientes:
                self.notificacion_solicitada.emit(
                    "🔄 Tareas Reanudadas",
                    f"Se reanudaron {len(pendientes)} tarea(s) persistente(s) en segundo plano."
                )
        except Exception as exc:
            logger.error(f"Error al reanudar tareas: {exc}")

    # -------------------------------------------------------------------------
    # Lógica de Heartbeat Eficiente (Ahorro de Tokens)
    # -------------------------------------------------------------------------
    def _ejecutar_ciclo_heartbeat(self) -> None:
        """
        Inspecciona condiciones locales en SQLite y Calendar.
        Solo efectúa llamadas a la API de Gemini si un evento real lo demanda.
        """
        ahora = datetime.now()
        hoy_str = ahora.strftime("%Y-%m-%d")

        # 1. Briefing matutino (manual o automático entre 06:00 y 12:00)
        es_hora_manana = ahora.hour >= 6
        debe_briefing = self._briefing_forzado or (
            es_hora_manana and self._fecha_ultimo_briefing != hoy_str
        )
        if debe_briefing:
            self._briefing_forzado = False
            self._fecha_ultimo_briefing = hoy_str
            self._disparar_briefing_matutino()

        # 2. Reuniones próximas en Google Calendar (Revisión local/cero tokens de IA)
        self._verificar_reuniones_proximas()

        # 3. Tareas persistentes vencidas en agent_tasks (Revisión local previa en SQLite)
        self._procesar_tareas_vencidas()

        # 4. Consolidación nocturna diaria (manual o automática a partir de las 21:00)
        es_hora_noche = ahora.hour >= 21
        debe_consolidar = self._consolidacion_forzada or (
            es_hora_noche and self._fecha_ultima_consolidacion != hoy_str
        )
        if debe_consolidar:
            self._consolidacion_forzada = False
            self._fecha_ultima_consolidacion = hoy_str
            self._ejecutar_consolidacion_nocturna(hoy_str)

    # -------------------------------------------------------------------------
    # Manejadores de Eventos Específicos
    # -------------------------------------------------------------------------
    def _disparar_briefing_matutino(self) -> None:
        """Genera el briefing diario con Gemini y emite señales correspondientes."""
        try:
            briefing = self.cerebro.generar_briefing_matutino()
            self.briefing_listo.emit(briefing)
            self.notificacion_solicitada.emit(
                "☀️ Buenos días - Tu Asistente",
                "Tu agenda y tareas de hoy están listas. Pulsa Ctrl + Espacio para verlas."
            )
            self.cerebro.memoria.registrar_actividad(
                "briefing_matutino",
                "Briefing diario emitido con éxito."
            )
        except Exception as exc:
            logger.error(f"Error generando briefing matutino: {exc}")
            raise exc

    def _verificar_reuniones_proximas(self) -> None:
        """
        Revisa localmente si hay reuniones en los próximos 15 minutos.
        No consume tokens de Gemini.
        """
        if not self.cerebro.calendar.esta_autenticado():
            return

        try:
            ahora_utc = datetime.now(timezone.utc)
            limite_alerta = ahora_utc + timedelta(minutes=15)

            eventos = self.cerebro.calendar.listar_eventos(fecha_inicio=ahora_utc, fecha_fin=limite_alerta)
            for ev in eventos:
                ev_id = ev.get("id")
                if not ev_id or ev_id in self._eventos_notificados:
                    continue

                inicio_str = ev.get("inicio", "")
                if inicio_str:
                    try:
                        dt_inicio = datetime.fromisoformat(inicio_str)
                        diferencia_min = int((dt_inicio - ahora_utc).total_seconds() / 60)
                        if 0 <= diferencia_min <= 15:
                            titulo = ev.get("titulo", "Reunión")
                            msg = f"En {diferencia_min} min: {titulo}"
                            if ev.get("link_meet"):
                                msg += "\nEnlace Google Meet disponible."

                            self.notificacion_solicitada.emit("⏰ Reunión próxima", msg)
                            self._eventos_notificados.add(ev_id)
                            self.cerebro.memoria.registrar_actividad(
                                "alerta_reunion",
                                f"Alerta emitida para: {titulo}"
                            )
                    except Exception:
                        continue
        except Exception as exc:
            logger.warning(f"Error verificando reuniones: {exc}")

    def _procesar_tareas_vencidas(self) -> None:
        """
        Detecta tareas en SQLite cuya fecha de chequeo ya venció y las ejecuta
        usando el cerebro de Gemini con herramientas autónomas.
        """
        try:
            tareas_vencidas = self.cerebro.memoria.obtener_tareas_vencidas(limite=3)
            if not tareas_vencidas:
                return  # Cero tokens gastados si no hay tareas pendientes

            for t in tareas_vencidas:
                t_id = t["id"]
                objetivo = t["objetivo"]

                try:
                    res = self.cerebro.procesar_tarea_automatica(t)
                    resultado_txt = res.get("resultado", "Procesada")
                    self.tarea_actualizada.emit(t_id, "COMPLETADO", resultado_txt)
                    self.notificacion_solicitada.emit(
                        f"✅ Tarea #{t_id} Procesada",
                        f"{objetivo[:60]}..."
                    )
                    self.cerebro.memoria.registrar_actividad(
                        "tarea_procesada",
                        f"Tarea #{t_id} '{objetivo}' procesada con éxito."
                    )
                except Exception as err_tarea:
                    self.tarea_actualizada.emit(t_id, "ERROR", str(err_tarea))
                    logger.error(f"Error procesando tarea #{t_id}: {err_tarea}")
        except Exception as exc:
            logger.error(f"Error al consultar tareas vencidas: {exc}")

    def _ejecutar_consolidacion_nocturna(self, hoy_str: str) -> None:
        """
        Rutina diaria de consolidación:
        1. Resume actividad y conversaciones del día.
        2. Escribe el cierre en la nota diaria de Obsidian.
        3. Limpia y compacta registros antiguos en SQLite.
        """
        try:
            actividades = self.cerebro.memoria.obtener_resumen_actividad_reciente(horas=24)
            mensajes_recientes = self.cerebro.memoria.obtener_ultimos_mensajes(limite=15)

            prompt_consolidacion = f"""Genera una consolidación concisa y reflexiva para el cierre del día {hoy_str}.
Actividades registradas en el sistema (últimas 24 horas):
{json.dumps(actividades, ensure_ascii=False) if actividades else 'Sin registros especiales de actividad.'}

Últimas interacciones de la jornada:
{json.dumps([m['mensaje'] for m in mensajes_recientes[-8:]], ensure_ascii=False) if mensajes_recientes else 'Sin interacciones directas registradas.'}

Estructura el resumen con formato Markdown elegante para guardar en la nota diaria:
- 📌 **Logros y Tareas Completadas**: Puntos clave atendidos hoy.
- 💡 **Aprendizajes y Contexto**: Ideas o preferencias observadas.
- 🎯 **Enfoque Sugerido para Mañana**: Próximas prioridades recomendadas.
"""
            resumen_md = self.cerebro.generar_texto_con_modelo(
                prompt=prompt_consolidacion,
                system_instruction="Eres un asesor reflexivo y organizador personal para consolidación de cierre de jornada."
            )

            # Escribir en la nota diaria de Obsidian
            self.cerebro.obsidian.agregar_bitacora(
                texto=f"🌙 **Consolidación y Cierre del Día:**\n\n{resumen_md}",
                fecha=hoy_str
            )

            # Limpiar registros antiguos de la base de datos (retención: 30 días)
            res_limpieza = self.cerebro.memoria.limpiar_registros_antiguos(dias_retencion=30)

            # Señales
            self.consolidacion_listo.emit(resumen_md)
            self.notificacion_solicitada.emit(
                "🌙 Consolidación Nocturna",
                "Se ha registrado el cierre de jornada en Obsidian y optimizado la memoria persistente."
            )
            self.cerebro.memoria.registrar_actividad(
                "consolidacion_nocturna",
                f"Consolidación completada. Purgados: {res_limpieza['actividades_borradas']} eventos y {res_limpieza['tareas_borradas']} tareas archivadas."
            )
        except Exception as exc:
            logger.error(f"Error en consolidación nocturna: {exc}")
            raise exc

    # -------------------------------------------------------------------------
    # Tolerancia a Fallos y Exponential Backoff
    # -------------------------------------------------------------------------
    def _manejar_error_con_backoff(self, exc: Exception) -> None:
        """
        Calcula el tiempo de retroceso exponencial ante errores de red o servicio.
        Evita que el agente se muera en segundo plano ante caídas temporales de la API.
        """
        self._fallos_consecutivos += 1
        # Fórmula: min(300, 5 * 2^(fallos)) -> 10s, 20s, 40s, 80s, 160s, max 300s (5 min)
        potencia = min(self._fallos_consecutivos, 6)
        segundos_espera = min(300, 5 * (2 ** potencia))
        self._backoff_hasta = time.time() + segundos_espera

        logger.warning(
            f"[MotorProactivo] Fallo en ciclo ({type(exc).__name__}: {exc}). "
            f"Aplicando Exponential Backoff de {segundos_espera}s (Intento consecutivo #{self._fallos_consecutivos})."
        )
