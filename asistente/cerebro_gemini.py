"""
Cerebro y Orquestador del Asistente Persistente con Google Gemini.

Conecta el modelo de lenguaje de Google con el Bus Unificado de Herramientas:
- Bóveda de Obsidian (notas diarias, tareas, capturas rápidas, bitácora).
- Google Calendar (agenda, eventos, reuniones Meet).
- Memoria Persistente SQLite (hechos del usuario, preferencias, historial y agent_tasks).
- Finanzas Personales (presupuestos, alertas y registro de gastos).
- Evaluador Docente (calificaciones, notas y estadísticas).
- Tolerancia a fallos: reintento y alternancia automática de modelos ante picos de demanda 503 UNAVAILABLE.
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import date, datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

from dotenv import load_dotenv
from google import genai
from google.genai import types

from asistente.conector_calendar import ConectorCalendar
from asistente.conector_obsidian import ConectorObsidian
from asistente.memoria_persistente import MemoriaPersistente
from core.tools_registry import ToolsRegistry

load_dotenv()
logger = logging.getLogger("CerebroGemini")


class CerebroGemini:
    """Orquestador cognitivo con integración de herramientas nativas de Google GenAI y resiliencia."""

    def __init__(
        self,
        conector_obsidian: Optional[ConectorObsidian] = None,
        conector_calendar: Optional[ConectorCalendar] = None,
        memoria: Optional[MemoriaPersistente] = None,
        tools_registry: Optional[ToolsRegistry] = None,
    ):
        self.obsidian = conector_obsidian or ConectorObsidian()
        self.calendar = conector_calendar or ConectorCalendar()
        self.memoria = memoria or MemoriaPersistente()

        self.tools_registry = tools_registry or ToolsRegistry(
            obsidian=self.obsidian,
            calendar=self.calendar,
            memoria=self.memoria,
        )

        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("Falta GOOGLE_API_KEY en el archivo .env")

        self.model_id = os.getenv("GOOGLE_MODEL_ID", "gemini-3-flash-preview").strip()
        self.cliente = genai.Client(api_key=self.api_key)

    def _obtener_modelos_candidatos(self) -> List[str]:
        """
        Retorna la lista ordenada de modelos a intentar ante errores 503 (alta demanda)
        o 429 (límite de cuota).
        """
        candidatos = [self.model_id]
        respaldos = [
            "gemini-3.1-flash-lite-preview",
            "gemini-3.5-flash-lite",
            "gemini-3-flash-preview",
            "gemini-3.8-flash",
            "gemini-3.7-flash",
            "gemini-3.6-flash"
        ]
        for r in respaldos:
            if r not in candidatos:
                candidatos.append(r)
        return candidatos

    # -------------------------------------------------------------------------
    # Generador de Instrucción del Sistema
    # -------------------------------------------------------------------------
    def _construir_system_instruction(self) -> str:
        ahora = datetime.now()
        fecha_actual = ahora.strftime("%Y-%m-%d")
        dia_semana = ahora.strftime("%A")
        hora_actual = ahora.strftime("%H:%M")

        hechos = self.memoria.obtener_todos_los_hechos()
        hechos_str = "\n".join([f"- {k}: {v}" for k, v in hechos.items()]) if hechos else "Ninguno registrado aún."

        return f"""Eres Antigravity Assistant, un agente de ejecución autónomo y segundo cerebro ejecutivo de escritorio.
Vives en el sistema del usuario (Windows), conectado con su Vault de Obsidian, Google Calendar, memoria persistente SQLite, gestión de Finanzas Personales y módulo Evaluador Docente.

FECHA Y HORA ACTUAL: {fecha_actual} ({dia_semana}), {hora_actual}.
PERFIL Y PREFERENCIAS DEL USUARIO:
{hechos_str}

CAPACIDADES Y HERRAMIENTAS DISPONIBLES:
1. Obsidian:
   - 'consultar_tareas_obsidian': Tareas de hoy o de todo el Vault.
   - 'agregar_tarea_obsidian': Registrar nuevas tareas pendientes.
   - 'marcar_tarea_obsidian': Marcar tareas completadas [x] o pendientes [ ].
   - 'guardar_apunte_obsidian': Guardar ideas o capturas rápidas en 'Capturas/'.
   - 'leer_nota_diaria_obsidian': Leer contenido de una nota diaria específica.
2. Google Calendar:
   - 'consultar_eventos_calendario': Consultar reuniones y compromisos.
   - 'crear_evento_calendario': Agendar citas con duración y opción de Google Meet.
3. Finanzas Personales:
   - 'consultar_resumen_finanzas': Consultar presupuesto mensual, gastos por categoría y alertas.
   - 'registrar_nuevo_gasto': Registrar transacciones con monto, categoría, comercio y método de pago.
4. Evaluador Docente:
   - 'consultar_estado_evaluaciones': Consultar entregas y respuestas de exámenes.
   - 'consultar_ranking_examen': Consultar estudiantes evaluados por examen.
5. Memoria Persistente:
   - 'guardar_hecho_usuario': Recordar datos duraderos sobre gustos, reglas o perfil del usuario.
   - 'buscar_memoria_pasada': Buscar en el historial de interacciones anteriores.
6. Tareas Autónomas Persistentes:
   - 'crear_tarea_persistente': Programar tareas para ejecución diferida o monitoreo en segundo plano.
   - 'consultar_tareas_persistentes': Consultar el estado de la cola de tareas del agente.
   - 'posponer_tarea_persistente': Posponer una tarea si requiere esperar tiempo o condiciones externas.
   - 'completar_tarea_persistente': Cerrar una tarea con su resultado de ejecución.

REGLAS DE COMPORTAMIENTO:
1. Respuestas concisas, ejecutivas, elegantes y enfocadas en la productividad.
2. Si el usuario te pide agendar, registrar gastos, anotar tareas o recordar algo, invoca de inmediato la herramienta adecuada.
3. Formatea tu respuesta con Markdown limpio (listas, negritas, emojis discretos).
4. Si Google Calendar devuelve que no está conectado o no autenticado, informa amablemente que puede conectarlo ejecutando 'conectar_calendar.bat' en su carpeta sin bloquear las otras funciones.
"""

    def _construir_historial_valido(self, limite: int = 6) -> List[types.Content]:
        """
        Construye un historial de conversación que respeta la alternancia estricta
        'user' -> 'model' requerida por la API de Google Gemini.
        """
        mensajes = self.memoria.obtener_ultimos_mensajes(limite=limite)
        if not mensajes or len(mensajes) <= 1:
            return []

        # Excluir el último mensaje ya que se enviará en chat.send_message
        mensajes_previos = mensajes[:-1]
        historial_valido: List[types.Content] = []
        esperando_rol = "user"

        for m in mensajes_previos:
            rol = "user" if m["rol"] == "user" else "model"
            if rol == esperando_rol:
                historial_valido.append(
                    types.Content(
                        role=rol,
                        parts=[types.Part.from_text(text=m["mensaje"])]
                    )
                )
                esperando_rol = "model" if esperando_rol == "user" else "user"

        # Si el historial termina en 'user', eliminarlo para que el próximo mensaje sea 'user'
        if historial_valido and historial_valido[-1].role == "user":
            historial_valido.pop()

        return historial_valido

    # -------------------------------------------------------------------------
    # Procesamiento Principal de Consultas del Usuario
    # -------------------------------------------------------------------------
    def procesar_mensaje(self, mensaje_usuario: str) -> Dict[str, Any]:
        """
        Procesa el mensaje del usuario con reintentos y tolerancia a fallos 503 (alta demanda).
        """
        self.memoria.registrar_mensaje("user", mensaje_usuario)

        # Contexto de mensajes recientes válido y alternado
        historial_para_modelo = self._construir_historial_valido(limite=6)

        config = types.GenerateContentConfig(
            system_instruction=self._construir_system_instruction(),
            tools=self.tools_registry.obtener_herramientas(),
            temperature=0.4,
        )

        modelos = self._obtener_modelos_candidatos()
        ultimo_error = None

        for modelo in modelos:
            for intento in range(2):
                try:
                    chat = self.cliente.chats.create(model=modelo, config=config, history=historial_para_modelo)
                    respuesta = chat.send_message(mensaje_usuario)

                    texto_respuesta = respuesta.text or "Acción completada con éxito."
                    self.memoria.registrar_mensaje("model", texto_respuesta)

                    # Si un modelo de respaldo funcionó, actualizar modelo actual para siguientes turnos
                    if modelo != self.model_id:
                        self.model_id = modelo

                    return {
                        "exito": True,
                        "respuesta": texto_respuesta,
                        "modelo": modelo,
                    }
                except Exception as exc:
                    ultimo_error = exc
                    err_str = str(exc)
                    if "503" in err_str or "UNAVAILABLE" in err_str or "high demand" in err_str:
                        time.sleep(1.0)
                        continue
                    elif "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "Too Many Requests" in err_str:
                        time.sleep(2.0)
                        continue
                    elif "404" in err_str:
                        break
                    else:
                        break

        error_msg = f"Error al procesar con Gemini ({type(ultimo_error).__name__}): {ultimo_error}"
        return {
            "exito": False,
            "respuesta": error_msg,
            "error": str(ultimo_error)
        }

    # -------------------------------------------------------------------------
    # Procesamiento Autónomo de Tareas Persistentes (Segundo Plano)
    # -------------------------------------------------------------------------
    def procesar_tarea_automatica(self, tarea: Dict[str, Any]) -> Dict[str, Any]:
        """
        Procesa una tarea persistente vencida con alternancia de modelos ante 503.
        """
        tarea_id = tarea["id"]
        objetivo = tarea["objetivo"]
        contexto = tarea.get("contexto", {})

        self.memoria.actualizar_estado_tarea(tarea_id, "EN_PROGRESO")
        self.memoria.incrementar_intentos_tarea(tarea_id)

        prompt = f"""Debes procesar y dar seguimiento autónomo a la siguiente tarea persistente en segundo plano:
ID DE TAREA: {tarea_id}
OBJETIVO: {objetivo}
CONTEXTO PREVIO: {json.dumps(contexto, ensure_ascii=False)}

Instrucciones:
1. Usa las herramientas necesarias para avanzar o verificar el cumplimiento de este objetivo.
2. Si la tarea se completó, llama a 'completar_tarea_persistente'.
3. Si la tarea requiere esperar más tiempo o un nuevo chequeo, llama a 'posponer_tarea_persistente'.
4. Brinda una síntesis clara del estado y acciones ejecutadas.
"""

        config = types.GenerateContentConfig(
            system_instruction=self._construir_system_instruction(),
            tools=self.tools_registry.obtener_herramientas(),
            temperature=0.3,
        )

        modelos = self._obtener_modelos_candidatos()
        ultimo_error = None

        for modelo in modelos:
            for intento in range(2):
                try:
                    chat = self.cliente.chats.create(model=modelo, config=config)
                    respuesta = chat.send_message(prompt)
                    texto_resultado = respuesta.text or "Tarea procesada."

                    tarea_actual = self.memoria.obtener_tarea(tarea_id)
                    if tarea_actual and tarea_actual["estado"] == "EN_PROGRESO":
                        self.memoria.actualizar_estado_tarea(
                            tarea_id,
                            estado="COMPLETADO",
                            resultado=texto_resultado
                        )

                    return {
                        "exito": True,
                        "tarea_id": tarea_id,
                        "resultado": texto_resultado,
                        "modelo": modelo
                    }
                except Exception as exc:
                    ultimo_error = exc
                    err_str = str(exc)
                    if "503" in err_str or "UNAVAILABLE" in err_str or "high demand" in err_str:
                        time.sleep(1.0)
                        continue
                    elif "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "Too Many Requests" in err_str:
                        time.sleep(2.0)
                        continue
                    elif "404" in err_str:
                        break
                    else:
                        break

        self.memoria.actualizar_estado_tarea(
            tarea_id,
            estado="FALLIDO",
            resultado=f"Error en ejecución: {ultimo_error}"
        )
        raise ultimo_error

    # -------------------------------------------------------------------------
    # Generador de Texto Directo (Helper Ligero)
    # -------------------------------------------------------------------------
    def generar_texto_con_modelo(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperatura: float = 0.5
    ) -> str:
        """Helper directo para resúmenes, briefings y consolidaciones con fallback."""
        config = types.GenerateContentConfig(
            system_instruction=system_instruction or "Eres un asistente ejecutivo perspicaz y conciso.",
            temperature=temperatura,
        )

        modelos = self._obtener_modelos_candidatos()
        ultimo_error = None

        for modelo in modelos:
            for intento in range(2):
                try:
                    res = self.cliente.models.generate_content(
                        model=modelo,
                        contents=prompt,
                        config=config,
                    )
                    return res.text or ""
                except Exception as exc:
                    ultimo_error = exc
                    err_str = str(exc)
                    if "503" in err_str or "UNAVAILABLE" in err_str or "high demand" in err_str:
                        time.sleep(1.0)
                        continue
                    elif "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "Too Many Requests" in err_str:
                        time.sleep(2.0)
                        continue
                    elif "404" in err_str:
                        break
                    else:
                        break

        raise ultimo_error

    # -------------------------------------------------------------------------
    # Briefing Matutino Unificado
    # -------------------------------------------------------------------------
    def generar_briefing_matutino(self) -> str:
        """Genera un resumen proactivo combinando calendario de hoy y tareas de Obsidian."""
        datos_obsidian = self.obsidian.leer_nota_diaria()
        pendientes = datos_obsidian["tareas_pendientes"]

        eventos_cal = []
        if self.calendar.esta_autenticado():
            try:
                eventos_cal = self.calendar.obtener_resumen_hoy()
            except Exception:
                pass

        prompt_briefing = f"""Genera un briefing matutino breve, motivador y estructurado para el usuario.
Fecha: {datos_obsidian['fecha']} ({datos_obsidian['dia']}).

Eventos de hoy en Google Calendar:
{json.dumps(eventos_cal, ensure_ascii=False) if eventos_cal else 'No hay eventos agendados hoy o Calendar no está conectado aún.'}

Tareas pendientes de hoy en Obsidian:
{json.dumps(pendientes, ensure_ascii=False) if pendientes else 'No hay tareas registradas para hoy aún.'}

Estructúralo con:
1. Saludo cálido matutino.
2. Compromisos con horario (si los hay).
3. Tareas prioritarias a completar.
4. Una frase breve de enfoque para el día.
"""
        try:
            return self.generar_texto_con_modelo(
                prompt=prompt_briefing,
                system_instruction="Eres un asistente personal ejecutivo. Mantén el tono profesional, enérgico y conciso."
            )
        except Exception:
            # Fallback manual sin conexión
            lineas = [f"☀️ **Buenos días - {datos_obsidian['dia']} {datos_obsidian['fecha']}**\n"]
            if pendientes:
                lineas.append("**📋 Tareas pendientes en Obsidian:**")
                for t in pendientes[:5]:
                    lineas.append(f"- {t}")
            else:
                lineas.append("No tienes tareas pendientes anotadas para hoy.")
            return "\n".join(lineas)
