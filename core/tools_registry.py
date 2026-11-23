"""
Bus Unificado de Herramientas (Tools Registry) para el Ecosistema Antigravity.

Expone funciones limpias, fuertemente tipadas y con docstrings descriptivos
compatibles con Function Calling nativo de `google-genai` (vía `types.GenerateContentConfig`).
Unifica:
1. Obsidian (notas diarias, tareas, capturas rápidas, bitácora).
2. Google Calendar (consulta de agenda, creación de eventos y Meet).
3. Finanzas Personales (consulta de presupuestos, métricas, registro de gastos).
4. Evaluador Docente (consulta de entregas, respuestas y estadísticas de exámenes).
5. Memoria Persistente y Perfil (hechos, historial de conversaciones).
6. Tareas Persistentes del Agente (creación, monitoreo, aplazamiento y cierre de tareas).
"""

import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from asistente.conector_calendar import ConectorCalendar
from asistente.conector_obsidian import ConectorObsidian
from asistente.memoria_persistente import MemoriaPersistente
from evaluador.almacenamiento import GestorAlmacenamiento
from finanzas.gestor_presupuesto import Gasto, GestorPresupuesto


class ToolsRegistry:
    """Registro y orquestador central de herramientas ejecutables por Gemini."""

    def __init__(
        self,
        obsidian: Optional[ConectorObsidian] = None,
        calendar: Optional[ConectorCalendar] = None,
        memoria: Optional[MemoriaPersistente] = None,
        gestor_presupuesto: Optional[GestorPresupuesto] = None,
        gestor_evaluador: Optional[GestorAlmacenamiento] = None,
    ):
        raiz_proyecto = Path(__file__).resolve().parent.parent
        dir_data = raiz_proyecto / "data"
        dir_data.mkdir(parents=True, exist_ok=True)

        self.obsidian = obsidian or ConectorObsidian()
        self.calendar = calendar or ConectorCalendar()
        self.memoria = memoria or MemoriaPersistente()
        self.presupuesto = gestor_presupuesto or GestorPresupuesto(
            ruta_gastos=dir_data / "gastos.json",
            ruta_config=dir_data / "presupuesto_config.json"
        )
        self.evaluador = gestor_evaluador or GestorAlmacenamiento(
            ruta_archivo=str(dir_data / "respuestas.json")
        )

    # =========================================================================
    # 1. HERRAMIENTAS DE OBSIDIAN
    # =========================================================================
    def consultar_tareas_obsidian(self, solo_hoy: bool = True) -> str:
        """
        Consulta las tareas pendientes en Obsidian.
        
        Args:
            solo_hoy: Si es True, revisa únicamente la nota diaria de hoy; si es False,
                      revisa todas las notas diarias recientes y la lista general.
        """
        try:
            if solo_hoy:
                datos = self.obsidian.leer_nota_diaria()
                pendientes = datos["tareas_pendientes"]
                completadas = datos["tareas_completadas"]
                return json.dumps({
                    "exito": True,
                    "fecha": datos["fecha"],
                    "dia": datos["dia"],
                    "pendientes": pendientes,
                    "completadas": completadas,
                    "total_pendientes": len(pendientes)
                }, ensure_ascii=False)
            else:
                todas = self.obsidian.listar_todas_las_tareas_pendientes()
                return json.dumps({
                    "exito": True,
                    "tareas": todas,
                    "total": len(todas)
                }, ensure_ascii=False)
        except Exception as exc:
            return json.dumps({"exito": False, "error": str(exc)}, ensure_ascii=False)

    def agregar_tarea_obsidian(self, tarea: str, fecha_iso: Optional[str] = None) -> str:
        """
        Agrega una nueva tarea a la nota diaria de Obsidian.
        
        Args:
            tarea: Texto descriptivo de la tarea pendiente.
            fecha_iso: Fecha opcional en formato YYYY-MM-DD (por defecto hoy).
        """
        try:
            exito = self.obsidian.agregar_tarea_nota_diaria(tarea, fecha=fecha_iso)
            return json.dumps({
                "exito": exito,
                "tarea_agregada": tarea,
                "fecha": fecha_iso or str(date.today())
            }, ensure_ascii=False)
        except Exception as exc:
            return json.dumps({"exito": False, "error": str(exc)}, ensure_ascii=False)

    def marcar_tarea_obsidian(self, texto_tarea: str, completada: bool = True) -> str:
        """
        Marca una tarea como completada [x] o como pendiente [ ] en la nota diaria de Obsidian.
        
        Args:
            texto_tarea: Frase o palabra clave que identifica la tarea.
            completada: True para marcarla como completada [x], False para desmarcarla [ ].
        """
        try:
            exito = self.obsidian.marcar_tarea(texto_tarea, completada=completada)
            return json.dumps({
                "exito": exito,
                "tarea": texto_tarea,
                "completada": completada
            }, ensure_ascii=False)
        except Exception as exc:
            return json.dumps({"exito": False, "error": str(exc)}, ensure_ascii=False)

    def guardar_apunte_obsidian(self, texto: str, titulo: Optional[str] = None) -> str:
        """
        Guarda una nota rápida, idea o pensamiento en la carpeta Capturas de Obsidian.
        
        Args:
            texto: Contenido detallado del apunte o pensamiento.
            titulo: Título opcional para el encabezado y nombre del archivo.
        """
        try:
            ruta = self.obsidian.agregar_captura_rapida(texto, titulo=titulo)
            return json.dumps({
                "exito": True,
                "archivo_creado": ruta.name,
                "ruta_completa": str(ruta)
            }, ensure_ascii=False)
        except Exception as exc:
            return json.dumps({"exito": False, "error": str(exc)}, ensure_ascii=False)

    def leer_nota_diaria_obsidian(self, fecha_iso: Optional[str] = None) -> str:
        """
        Lee el contenido estructurado completo de una nota diaria de Obsidian.
        
        Args:
            fecha_iso: Fecha opcional en formato YYYY-MM-DD (por defecto hoy).
        """
        try:
            datos = self.obsidian.leer_nota_diaria(fecha=fecha_iso)
            return json.dumps({
                "exito": True,
                "fecha": datos["fecha"],
                "dia": datos["dia"],
                "tareas_pendientes": datos["tareas_pendientes"],
                "tareas_completadas": datos["tareas_completadas"],
                "contenido": datos["contenido_completo"]
            }, ensure_ascii=False)
        except Exception as exc:
            return json.dumps({"exito": False, "error": str(exc)}, ensure_ascii=False)

    # =========================================================================
    # 2. HERRAMIENTAS DE GOOGLE CALENDAR
    # =========================================================================
    def consultar_eventos_calendario(
        self,
        fecha_inicio_iso: Optional[str] = None,
        dias: int = 1
    ) -> str:
        """
        Consulta los eventos programados en Google Calendar.
        
        Args:
            fecha_inicio_iso: Fecha y hora de inicio en formato ISO (ej. '2026-11-18T00:00:00').
            dias: Número de días hacia adelante a consultar (predeterminado: 1).
        """
        if not self.calendar.esta_autenticado():
            return json.dumps({
                "exito": False,
                "autenticado": False,
                "mensaje": "Google Calendar no está autenticado aún. Coloca credentials.json para habilitarlo."
            }, ensure_ascii=False)

        try:
            inicio = datetime.fromisoformat(fecha_inicio_iso) if fecha_inicio_iso else datetime.now()
            fin = inicio + timedelta(days=max(1, dias))
            eventos = self.calendar.listar_eventos(fecha_inicio=inicio, fecha_fin=fin)
            return json.dumps({
                "exito": True,
                "total": len(eventos),
                "eventos": eventos
            }, ensure_ascii=False)
        except Exception as exc:
            return json.dumps({"exito": False, "error": str(exc)}, ensure_ascii=False)

    def crear_evento_calendario(
        self,
        titulo: str,
        fecha_hora_iso: str,
        duracion_minutos: int = 60,
        descripcion: str = "",
        con_meet: bool = False
    ) -> str:
        """
        Crea y agenda un nuevo evento en Google Calendar.
        
        Args:
            titulo: Nombre o título de la reunión o compromiso.
            fecha_hora_iso: Fecha y hora de inicio en formato ISO (ej. '2026-11-18T15:30:00').
            duracion_minutos: Duración en minutos del evento (predeterminado: 60).
            descripcion: Detalles o notas adicionales sobre el evento.
            con_meet: Si es True, genera automáticamente enlace de videoconferencia Google Meet.
        """
        if not self.calendar.esta_autenticado():
            return json.dumps({
                "exito": False,
                "autenticado": False,
                "error": "Google Calendar no está autenticado aún."
            }, ensure_ascii=False)

        try:
            # Limpiar formatos comunes como '2026-11-19 06:00' -> '2026-11-19T06:00:00'
            limpio = fecha_hora_iso.strip().replace(" ", "T")
            if len(limpio) == 16:  # 'YYYY-MM-DDTHH:MM'
                limpio += ":00"
            inicio = datetime.fromisoformat(limpio)
            resultado = self.calendar.crear_evento(
                titulo=titulo,
                fecha_hora_inicio=inicio,
                duracion_minutos=duracion_minutos,
                descripcion=descripcion,
                con_meet=con_meet
            )
            return json.dumps(resultado, ensure_ascii=False)
        except Exception as exc:
            return json.dumps({"exito": False, "error": str(exc)}, ensure_ascii=False)

    # =========================================================================
    # 3. HERRAMIENTAS DE FINANZAS PERSONALES
    # =========================================================================
    def consultar_resumen_finanzas(
        self,
        mes: Optional[int] = None,
        anio: Optional[int] = None,
        categoria: Optional[str] = None
    ) -> str:
        """
        Consulta las métricas consolidadas del presupuesto personal y gastos acumulados.
        
        Args:
            mes: Número del mes a consultar (1 a 12). Si se omite, usa el mes actual.
            anio: Año a consultar (ej. 2026). Si se omite, usa el año actual.
            categoria: Filtrar por categoría específica (ej. 'Alimentación', 'Transporte').
        """
        try:
            metricas = self.presupuesto.calcular_metricas(
                mes=mes,
                anio=anio,
                categoria_filtro=categoria
            )
            # Simplificar para respuesta ligera en JSON
            resumen = {
                "exito": True,
                "mes": metricas["mes"],
                "anio": metricas["anio"],
                "total_gastos_registrados": metricas["total_gastos"],
                "total_gastado": metricas["total_gastado"],
                "presupuesto_total": metricas["presupuesto_total"],
                "presupuesto_restante": metricas["restante"],
                "porcentaje_consumido": metricas["porcentaje_consumido"],
                "estado_global": metricas["estado_global"],
                "desglose_por_categoria": metricas["por_categoria"],
                "alertas": [a["mensaje"] for a in metricas.get("alertas_categoria", [])],
                "top_comercios": metricas.get("top_comercios", [])
            }
            return json.dumps(resumen, ensure_ascii=False)
        except Exception as exc:
            return json.dumps({"exito": False, "error": str(exc)}, ensure_ascii=False)

    def registrar_nuevo_gasto(
        self,
        monto: float,
        categoria: str,
        comercio: str = "Comercio General",
        descripcion: str = "",
        metodo_pago: str = "Tarjeta de Crédito",
        fecha_iso: Optional[str] = None
    ) -> str:
        """
        Registra una nueva transacción o gasto en el sistema de finanzas personales.
        
        Args:
            monto: Valor numérico positivo del gasto (en COP u otra moneda configurada).
            categoria: Categoría del gasto (ej. 'Alimentación', 'Servicios Públicos', 'Transporte', 'Restaurantes & Ocio').
            comercio: Nombre del establecimiento, proveedor o tienda.
            descripcion: Detalle o motivo del gasto.
            metodo_pago: Medio de pago utilizado (ej. 'Efectivo', 'Tarjeta de Débito', 'Tarjeta de Crédito').
            fecha_iso: Fecha de la transacción en formato YYYY-MM-DD (por defecto hoy).
        """
        try:
            fecha_final = fecha_iso or datetime.now().strftime("%Y-%m-%d")
            nuevo_gasto = Gasto(
                fecha=fecha_final,
                comercio=comercio.strip(),
                categoria=categoria.strip(),
                monto=float(monto),
                descripcion=descripcion.strip(),
                metodo_pago=metodo_pago.strip()
            )
            gasto_guardado = self.presupuesto.agregar_gasto(nuevo_gasto)
            return json.dumps({
                "exito": True,
                "id_gasto": gasto_guardado.id,
                "monto": gasto_guardado.monto,
                "categoria": gasto_guardado.categoria,
                "comercio": gasto_guardado.comercio,
                "fecha": gasto_guardado.fecha
            }, ensure_ascii=False)
        except Exception as exc:
            return json.dumps({"exito": False, "error": str(exc)}, ensure_ascii=False)

    # =========================================================================
    # 4. HERRAMIENTAS DEL EVALUADOR DOCENTE
    # =========================================================================
    def consultar_estado_evaluaciones(self, id_examen: Optional[str] = None) -> str:
        """
        Consulta las entregas y respuestas registradas de exámenes de estudiantes.
        
        Args:
            id_examen: Identificador opcional del examen (ej. 'EXAM-PYTHON-2026'). Si se omite, lista todas.
        """
        try:
            if id_examen:
                respuestas = self.evaluador.obtener_respuestas_por_examen(id_examen)
            else:
                respuestas = self.evaluador.obtener_todas_las_respuestas()

            lista_resumen = []
            for r in respuestas:
                lista_resumen.append({
                    "estudiante_id": r.estudiante_id,
                    "nombre": r.nombre,
                    "correo": r.correo,
                    "id_examen": r.id_examen,
                    "total_respuestas": len(r.respuestas),
                    "fecha_registro": r.fecha_registro
                })

            return json.dumps({
                "exito": True,
                "id_examen_filtrado": id_examen,
                "total_entregas": len(lista_resumen),
                "entregas": lista_resumen
            }, ensure_ascii=False)
        except Exception as exc:
            return json.dumps({"exito": False, "error": str(exc)}, ensure_ascii=False)

    def consultar_ranking_examen(self, id_examen: str) -> str:
        """
        Genera un resumen analítico con las entregas de un examen específico.
        
        Args:
            id_examen: Identificador único del examen a consultar.
        """
        try:
            respuestas = self.evaluador.obtener_respuestas_por_examen(id_examen)
            if not respuestas:
                return json.dumps({
                    "exito": True,
                    "id_examen": id_examen,
                    "total_estudiantes": 0,
                    "mensaje": f"No se han registrado entregas para el examen '{id_examen}'."
                }, ensure_ascii=False)

            estudiantes = [
                {"nombre": r.nombre, "id": r.estudiante_id, "preguntas_respondidas": len(r.respuestas)}
                for r in respuestas
            ]
            return json.dumps({
                "exito": True,
                "id_examen": id_examen,
                "total_estudiantes": len(estudiantes),
                "estudiantes": estudiantes
            }, ensure_ascii=False)
        except Exception as exc:
            return json.dumps({"exito": False, "error": str(exc)}, ensure_ascii=False)

    # =========================================================================
    # 5. HERRAMIENTAS DE MEMORIA Y PERFIL
    # =========================================================================
    def guardar_hecho_usuario(self, clave: str, valor: str, categoria: str = "general") -> str:
        """
        Guarda o actualiza un hecho, preferencia personal o información relevante del usuario.
        
        Args:
            clave: Clave identificadora corta (ej. 'lenguaje_favorito', 'ciudad_residencia', 'meta_ahorro').
            valor: Descripción o valor del hecho.
            categoria: Categoría de clasificación (ej. 'personal', 'profesional', 'metas').
        """
        try:
            self.memoria.guardar_hecho(clave, valor, categoria=categoria)
            return json.dumps({
                "exito": True,
                "clave": clave,
                "valor": valor,
                "categoria": categoria
            }, ensure_ascii=False)
        except Exception as exc:
            return json.dumps({"exito": False, "error": str(exc)}, ensure_ascii=False)

    def buscar_memoria_pasada(self, termino: str) -> str:
        """
        Busca en el historial de conversaciones e interacciones pasadas del usuario.
        
        Args:
            termino: Palabra o concepto a buscar en la memoria.
        """
        try:
            resultados = self.memoria.buscar_en_historial(termino)
            return json.dumps({
                "exito": True,
                "termino": termino,
                "total_coincidencias": len(resultados),
                "resultados": resultados
            }, ensure_ascii=False)
        except Exception as exc:
            return json.dumps({"exito": False, "error": str(exc)}, ensure_ascii=False)

    # =========================================================================
    # 6. HERRAMIENTAS DE TAREAS PERSISTENTES DEL AGENTE (agent_tasks)
    # =========================================================================
    def crear_tarea_persistente(
        self,
        objetivo: str,
        minutos_espera: int = 0,
        contexto: Optional[str] = None
    ) -> str:
        """
        Crea una nueva tarea persistente en segundo plano para que el agente la revise o ejecute más adelante.
        
        Args:
            objetivo: Descripción clara de lo que se debe hacer o monitorear.
            minutos_espera: Minutos a esperar antes del primer chequeo (0 para chequeo inmediato).
            contexto: Información adicional o contexto serializado en texto o JSON.
        """
        try:
            ctx_dict = {}
            if contexto:
                try:
                    ctx_dict = json.loads(contexto)
                except Exception:
                    ctx_dict = {"detalle": contexto}

            tarea_id = self.memoria.crear_tarea(
                objetivo=objetivo,
                contexto=ctx_dict,
                minutos_espera=minutos_espera
            )
            return json.dumps({
                "exito": True,
                "id_tarea": tarea_id,
                "objetivo": objetivo,
                "minutos_espera": minutos_espera,
                "mensaje": f"Tarea #{tarea_id} creada exitosamente en la cola persistente."
            }, ensure_ascii=False)
        except Exception as exc:
            return json.dumps({"exito": False, "error": str(exc)}, ensure_ascii=False)

    def consultar_tareas_persistentes(self, estado: Optional[str] = None) -> str:
        """
        Consulta la cola de tareas persistentes del agente.
        
        Args:
            estado: Estado por el cual filtrar ('PENDIENTE', 'EN_PROGRESO', 'ESPERANDO_USUARIO', 'COMPLETADO', 'FALLIDO').
                    Si se omite, devuelve las más recientes.
        """
        try:
            tareas = self.memoria.obtener_tareas(estado=estado, limite=15)
            return json.dumps({
                "exito": True,
                "total": len(tareas),
                "estado_filtrado": estado,
                "tareas": tareas
            }, ensure_ascii=False)
        except Exception as exc:
            return json.dumps({"exito": False, "error": str(exc)}, ensure_ascii=False)

    def posponer_tarea_persistente(
        self,
        tarea_id: int,
        minutos_demora: int = 15,
        razon: str = ""
    ) -> str:
        """
        Pospone la ejecución de una tarea persistente por un tiempo determinado.
        
        Args:
            tarea_id: Identificador numérico de la tarea.
            minutos_demora: Cantidad de minutos a posponer (predeterminado: 15).
            razon: Motivo por el cual se pospone la tarea.
        """
        try:
            exito = self.memoria.posponer_tarea(tarea_id, minutos_demora=minutos_demora, razon=razon)
            return json.dumps({
                "exito": exito,
                "id_tarea": tarea_id,
                "minutos_pospuesto": minutos_demora,
                "razon": razon
            }, ensure_ascii=False)
        except Exception as exc:
            return json.dumps({"exito": False, "error": str(exc)}, ensure_ascii=False)

    def completar_tarea_persistente(
        self,
        tarea_id: int,
        resultado: str = "Completada con éxito"
    ) -> str:
        """
        Marca una tarea persistente como COMPLETADA registrando su resultado final.
        
        Args:
            tarea_id: Identificador numérico de la tarea.
            resultado: Resumen o descripción de cómo se completó la tarea.
        """
        try:
            exito = self.memoria.actualizar_estado_tarea(
                tarea_id=tarea_id,
                estado="COMPLETADO",
                resultado=resultado
            )
            return json.dumps({
                "exito": exito,
                "id_tarea": tarea_id,
                "estado": "COMPLETADO",
                "resultado": resultado
            }, ensure_ascii=False)
        except Exception as exc:
            return json.dumps({"exito": False, "error": str(exc)}, ensure_ascii=False)

    # =========================================================================
    # LISTA DE HERRAMIENTAS PARA GOOGLE GENAI
    # =========================================================================
    def obtener_herramientas(self) -> List[Callable]:
        """
        Devuelve la lista completa de funciones vinculadas (callables)
        para pasar directamente a `types.GenerateContentConfig(tools=[...])`.
        """
        return [
            # Obsidian
            self.consultar_tareas_obsidian,
            self.agregar_tarea_obsidian,
            self.marcar_tarea_obsidian,
            self.guardar_apunte_obsidian,
            self.leer_nota_diaria_obsidian,
            # Calendar
            self.consultar_eventos_calendario,
            self.crear_evento_calendario,
            # Finanzas
            self.consultar_resumen_finanzas,
            self.registrar_nuevo_gasto,
            # Evaluador
            self.consultar_estado_evaluaciones,
            self.consultar_ranking_examen,
            # Memoria
            self.guardar_hecho_usuario,
            self.buscar_memoria_pasada,
            # Tareas Persistentes
            self.crear_tarea_persistente,
            self.consultar_tareas_persistentes,
            self.posponer_tarea_persistente,
            self.completar_tarea_persistente,
        ]

    def obtener_mapa_herramientas(self) -> Dict[str, Callable]:
        """Devuelve un diccionario {nombre_herramienta: funcion} para invocación por nombre."""
        return {fn.__name__: fn for fn in self.obtener_herramientas()}
