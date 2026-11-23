"""
Módulo de calificación automática, desglose métrico y análisis estadístico comparativo de evaluaciones.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
from .almacenamiento import RespuestaEstudiante
from .generador_examen import Examen


@dataclass
class ResultadoEvaluacion:
    """Resultado individual de la evaluación de un estudiante.

    Attributes:
        estudiante_id: Identificador del alumno.
        nombre: Nombre completo.
        correo: Correo electrónico.
        correctas: Cantidad de preguntas respondidas correctamente (aciertos).
        incorrectas: Cantidad de preguntas respondidas incorrectamente (errores).
        sin_responder: Cantidad de preguntas sin responder o dejadas en blanco.
        total_preguntas: Total de preguntas del examen.
        nota: Calificación obtenida en la escala configurada (ej. 0.0 a 5.0 o 0 a 100).
        escala_maxima: Escala superior de calificación (predeterminado: 5.0).
        escala_minima: Escala inferior de calificación (predeterminado: 0.0).
        porcentaje_acierto: Porcentaje de respuestas correctas (0.0% a 100.0%).
        detalles_respuestas: Diccionario {id_pregunta: bool (True si acertó)}.
    """

    estudiante_id: str
    nombre: str
    correo: str
    correctas: int
    incorrectas: int
    sin_responder: int
    total_preguntas: int
    nota: float
    escala_maxima: float = 5.0
    escala_minima: float = 0.0
    porcentaje_acierto: float = 0.0
    detalles_respuestas: Dict[int, bool] = field(default_factory=dict)

    # Compatibilidad hacia atrás con atributo 'aciertos'
    @property
    def aciertos(self) -> int:
        return self.correctas

    @aciertos.setter
    def aciertos(self, valor: int) -> None:
        self.correctas = valor

    def __post_init__(self) -> None:
        if self.total_preguntas > 0:
            self.porcentaje_acierto = round((self.correctas / self.total_preguntas) * 100.0, 2)
        else:
            self.porcentaje_acierto = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Serializa el resultado individual a un diccionario con todas las métricas."""
        return {
            "estudiante_id": self.estudiante_id,
            "nombre": self.nombre,
            "correo": self.correo,
            "correctas": self.correctas,
            "incorrectas": self.incorrectas,
            "sin_responder": self.sin_responder,
            "total_preguntas": self.total_preguntas,
            "nota": self.nota,
            "escala_maxima": self.escala_maxima,
            "escala_minima": self.escala_minima,
            "porcentaje_acierto": self.porcentaje_acierto,
            "detalles_respuestas": self.detalles_respuestas,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ResultadoEvaluacion:
        """Crea una instancia de ResultadoEvaluacion a partir de un diccionario."""
        correctas = data.get("correctas", data.get("aciertos", 0))
        return cls(
            estudiante_id=data.get("estudiante_id", ""),
            nombre=data.get("nombre", ""),
            correo=data.get("correo", ""),
            correctas=correctas,
            incorrectas=data.get("incorrectas", 0),
            sin_responder=data.get("sin_responder", 0),
            total_preguntas=data.get("total_preguntas", 0),
            nota=float(data.get("nota", 0.0)),
            escala_maxima=float(data.get("escala_maxima", 5.0)),
            escala_minima=float(data.get("escala_minima", 0.0)),
            porcentaje_acierto=float(data.get("porcentaje_acierto", 0.0)),
            detalles_respuestas=data.get("detalles_respuestas", {}),
        )


def _normalizar_resultados(
    resultados: List[Union[ResultadoEvaluacion, Dict[str, Any]]]
) -> List[ResultadoEvaluacion]:
    """Convierte listas heterogéneas (ResultadoEvaluacion o dict) en objetos ResultadoEvaluacion."""
    normalizados: List[ResultadoEvaluacion] = []
    for r in resultados:
        if isinstance(r, ResultadoEvaluacion):
            normalizados.append(r)
        elif isinstance(r, dict):
            normalizados.append(ResultadoEvaluacion.from_dict(r))
    return normalizados


def generar_tabla_comparativa(
    resultados: List[Union[ResultadoEvaluacion, Dict[str, Any]]],
    formato: str = "consola",
    escala_maxima: Optional[float] = None,
) -> str:
    """Genera una tabla comparativa detallada y ordenada de mayor a menor calificación.

    Columnas obligatorias por estudiante:
    1. Nombre del Estudiante
    2. Número de Respuestas Correctas
    3. Número de Respuestas Incorrectas
    4. Resultado Final / Nota

    Args:
        resultados: Lista de objetos ResultadoEvaluacion o diccionarios con métricas.
        formato: 'consola' (ASCII limpio) o 'markdown' (formato tabla GitHub Markdown).
        escala_maxima: Escala superior para mostrar (ej. 5.0 o 100.0). Si es None,
                       se deduce del primer registro o se asume 5.0.

    Returns:
        Cadena con la tabla formateada y el resumen estadístico al pie.
    """
    lista = _normalizar_resultados(resultados)

    # Manejo de caso borde: lista vacía
    if not lista:
        if formato.lower() == "markdown":
            return (
                "| Puesto | Nombre del Estudiante | Respuestas Correctas | Respuestas Incorrectas | Resultado Final / Nota |\n"
                "| :---: | :--- | :---: | :---: | :---: |\n"
                "| - | *No hay estudiantes evaluados* | - | - | - |\n\n"
                "> **[INFO] Sin datos**: No se encontraron exámenes para procesar."
            )
        return (
            "+--------+------------------------------+-------------------+---------------------+----------------------+\n"
            "| Puesto | Nombre del Estudiante        | Resp. Correctas   | Resp. Incorrectas   | Resultado Final/Nota |\n"
            "+--------+------------------------------+-------------------+---------------------+----------------------+\n"
            "| -      | No hay estudiantes evaluados | -                 | -                   | -                    |\n"
            "+--------+------------------------------+-------------------+---------------------+----------------------+\n"
            "[INFO] No se registraron evaluaciones para generar la tabla comparativa."
        )

    # Determinar escala máxima
    if escala_maxima is None:
        escala_maxima = lista[0].escala_maxima if lista else 5.0

    # Ordenar ranking automáticamente de mayor a menor nota; desempatar por correctas y nombre
    ordenados = sorted(
        lista,
        key=lambda r: (r.nota, r.correctas, -r.incorrectas, r.nombre),
        reverse=True,
    )

    # Métricas estadísticas para el pie de la tabla
    notas = [r.nota for r in ordenados]
    promedio = sum(notas) / len(notas)
    nota_max = max(notas)
    nota_min = min(notas)

    maximos = [r for r in ordenados if r.nota == nota_max]
    minimos = [r for r in ordenados if r.nota == nota_min]

    # Formato Markdown
    if formato.lower() == "markdown":
        lineas_md = [
            "| Puesto | Nombre del Estudiante | Respuestas Correctas | Respuestas Incorrectas | Resultado Final / Nota |",
            "| :---: | :--- | :---: | :---: | :---: |",
        ]
        for puesto, r in enumerate(ordenados, start=1):
            lineas_md.append(
                f"| #{puesto} | {r.nombre} | {r.correctas}/{r.total_preguntas} | {r.incorrectas} | **{r.nota:.2f} / {escala_maxima:.1f}** |"
            )

        # Resumen al pie en Markdown
        max_str = ", ".join(f"**{m.nombre}** ({m.correctas}/{m.total_preguntas} aciertos, {m.nota:.2f})" for m in maximos)
        min_str = ", ".join(f"**{mi.nombre}** ({mi.correctas}/{mi.total_preguntas} aciertos, {mi.nota:.2f})" for mi in minimos)

        lineas_md.extend([
            "",
            "### Resumen Estadístico del Grupo",
            f"- **[+] Nota Máxima:** {max_str}",
            f"- **[-] Nota Mínima:** {min_str}",
            f"- **[*] Promedio General del Grupo:** **{promedio:.2f} / {escala_maxima:.1f}** (Total evaluados: {len(ordenados)})",
        ])
        return "\n".join(lineas_md)

    # Formato Consola (ASCII limpio con anchos alineados)
    ancho_puesto = 8
    ancho_nombre = 30
    ancho_corr = 18
    ancho_inc = 18
    ancho_nota = 20

    sep_borde = (
        f"+{'-' * ancho_puesto}+{'-' * ancho_nombre}+{'-' * ancho_corr}+{'-' * ancho_inc}+{'-' * ancho_nota}+"
    )

    lineas_consola = [
        sep_borde,
        (
            f"| {'PUESTO':<{ancho_puesto - 2}} "
            f"| {'NOMBRE DEL ESTUDIANTE':<{ancho_nombre - 2}} "
            f"| {'RESP. CORRECTAS':^{ancho_corr - 2}} "
            f"| {'RESP. INCORRECTAS':^{ancho_inc - 2}} "
            f"| {'RESULTADO FINAL':^{ancho_nota - 2}} |"
        ),
        sep_borde,
    ]

    for puesto, r in enumerate(ordenados, start=1):
        puesto_str = f"#{puesto}"
        nombre_str = r.nombre[: ancho_nombre - 4]
        corr_str = f"{r.correctas} ({r.porcentaje_acierto:.0f}%)"
        inc_str = f"{r.incorrectas}"
        if r.sin_responder > 0:
            inc_str += f" ({r.sin_responder} s/r)"
        nota_str = f"{r.nota:.2f} / {escala_maxima:.1f}"

        lineas_consola.append(
            f"| {puesto_str:<{ancho_puesto - 2}} "
            f"| {nombre_str:<{ancho_nombre - 2}} "
            f"| {corr_str:^{ancho_corr - 2}} "
            f"| {inc_str:^{ancho_inc - 2}} "
            f"| {nota_str:^{ancho_nota - 2}} |"
        )

    lineas_consola.append(sep_borde)

    # Resumen estadístico al pie
    lineas_consola.append("\n" + "=" * 80)
    lineas_consola.append("RESUMEN ESTADÍSTICO DEL GRUPO:")
    lineas_consola.append("-" * 80)

    # Nota Máxima
    if len(maximos) == 1:
        m = maximos[0]
        lineas_consola.append(
            f"  [+] NOTA MÁXIMA : {m.nombre} (Aciertos: {m.correctas}/{m.total_preguntas}) -> {m.nota:.2f} / {escala_maxima:.1f}"
        )
    else:
        lineas_consola.append(
            f"  [+] NOTA MÁXIMA : Empate ({nota_max:.2f} / {escala_maxima:.1f}) entre {len(maximos)} estudiantes:"
        )
        for m in maximos:
            lineas_consola.append(f"      * {m.nombre} ({m.correo}) - {m.correctas}/{m.total_preguntas} correctas")

    # Nota Mínima
    if len(minimos) == 1:
        mi = minimos[0]
        lineas_consola.append(
            f"  [-] NOTA MÍNIMA : {mi.nombre} (Aciertos: {mi.correctas}/{mi.total_preguntas}) -> {mi.nota:.2f} / {escala_maxima:.1f}"
        )
    else:
        lineas_consola.append(
            f"  [-] NOTA MÍNIMA : Empate ({nota_min:.2f} / {escala_maxima:.1f}) entre {len(minimos)} estudiantes:"
        )
        for mi in minimos:
            lineas_consola.append(f"      * {mi.nombre} ({mi.correo}) - {mi.correctas}/{mi.total_preguntas} correctas")

    # Promedio
    lineas_consola.append(f"  [*] PROMEDIO GRUPO : {promedio:.2f} / {escala_maxima:.1f} (Total evaluados: {len(ordenados)})")
    lineas_consola.append("=" * 80)

    return "\n".join(lineas_consola)


@dataclass
class InformeComparativo:
    """Informe estadístico consolidado del rendimiento de todo el grupo en un examen.

    Attributes:
        id_examen: Identificador de la evaluación calificada.
        titulo_examen: Título del examen.
        total_evaluados: Número de estudiantes evaluados.
        promedio_general: Promedio aritmético de las notas del grupo.
        nota_maxima: Estudiante o resultado con el puntaje más alto.
        nota_minima: Estudiante o resultado con el puntaje más bajo.
        ranking: Lista de resultados ordenada descendentemente por nota.
        estudiantes_maxima: Lista de todos los estudiantes que empataron con la nota máxima.
        estudiantes_minima: Lista de todos los estudiantes que empataron con la nota mínima.
    """

    id_examen: str
    titulo_examen: str
    total_evaluados: int
    promedio_general: float
    nota_maxima: Optional[ResultadoEvaluacion]
    nota_minima: Optional[ResultadoEvaluacion]
    ranking: List[ResultadoEvaluacion]
    estudiantes_maxima: List[ResultadoEvaluacion] = field(default_factory=list)
    estudiantes_minima: List[ResultadoEvaluacion] = field(default_factory=list)

    def generar_tabla_comparativa(self, formato: str = "consola") -> str:
        """Genera la tabla comparativa directamente desde el informe."""
        return generar_tabla_comparativa(self.ranking, formato=formato)

    def generar_reporte_texto(self) -> str:
        """Produce el reporte formal integrando el encabezado y la tabla comparativa."""
        ancho = 80
        encabezado = [
            "=" * ancho,
            f"INFORME COMPARATIVO DE EVALUACIÓN: {self.titulo_examen}".center(ancho),
            f"(ID Examen: {self.id_examen})".center(ancho),
            "=" * ancho,
            "",
            "TABLA COMPARATIVA DETALLADA DE RESULTADOS:",
            "-" * ancho,
        ]
        tabla = self.generar_tabla_comparativa(formato="consola")
        return "\n".join(encabezado) + "\n" + tabla


class EvaluadorNotas:
    """Motor de cálculo de notas, desglose de métricas y análisis estadístico."""

    def __init__(self, escala_maxima: float = 5.0, escala_minima: float = 0.0):
        """Inicializa el evaluador con el rango de escala deseado.

        Args:
            escala_maxima: Nota máxima posible (ej. 5.0 o 100.0).
            escala_minima: Nota mínima posible (ej. 0.0).
        """
        if escala_maxima <= escala_minima:
            raise ValueError("La escala máxima debe ser mayor que la escala mínima.")
        self.escala_maxima = escala_maxima
        self.escala_minima = escala_minima

    def calificar_respuesta(
        self,
        examen: Examen,
        respuesta_estudiante: RespuestaEstudiante,
    ) -> ResultadoEvaluacion:
        """Califica las respuestas computando aciertos, errores y preguntas sin responder.

        Args:
            examen: Instancia del Examen con sus preguntas y respuestas correctas.
            respuesta_estudiante: Respuestas enviadas por el alumno.

        Returns:
            Instancia de ResultadoEvaluacion con el desglose completo de métricas.
        """
        if not examen.preguntas:
            raise ValueError(f"El examen {examen.id_examen} no contiene preguntas para evaluar.")

        clave_oficial = examen.obtener_clave_respuestas()
        correctas = 0
        incorrectas = 0
        sin_responder = 0
        total_peso_acertado = 0.0
        total_peso_posible = 0.0
        detalles: Dict[int, bool] = {}

        for p in examen.preguntas:
            total_peso_posible += p.puntaje_peso
            respuesta_dada = respuesta_estudiante.respuestas.get(p.id, "")

            if respuesta_dada is None or str(respuesta_dada).strip() == "":
                sin_responder += 1
                detalles[p.id] = False
            else:
                respuesta_limpia = str(respuesta_dada).strip().upper()
                es_correcta = respuesta_limpia == p.respuesta_correcta
                detalles[p.id] = es_correcta

                if es_correcta:
                    correctas += 1
                    total_peso_acertado += p.puntaje_peso
                else:
                    incorrectas += 1

        # Cálculo de la nota sobre la escala configurada
        proporcion = (total_peso_acertado / total_peso_posible) if total_peso_posible > 0 else 0.0
        rango = self.escala_maxima - self.escala_minima
        nota_calculada = round(self.escala_minima + (proporcion * rango), 2)

        return ResultadoEvaluacion(
            estudiante_id=respuesta_estudiante.estudiante_id,
            nombre=respuesta_estudiante.nombre,
            correo=respuesta_estudiante.correo,
            correctas=correctas,
            incorrectas=incorrectas,
            sin_responder=sin_responder,
            total_preguntas=len(examen.preguntas),
            nota=nota_calculada,
            escala_maxima=self.escala_maxima,
            escala_minima=self.escala_minima,
            detalles_respuestas=detalles,
        )

    def calificar_grupo(
        self,
        examen: Examen,
        respuestas: List[RespuestaEstudiante],
    ) -> List[ResultadoEvaluacion]:
        """Califica a todos los estudiantes de una lista de respuestas."""
        return [self.calificar_respuesta(examen, r) for r in respuestas]

    def generar_informe_comparativo(
        self,
        examen: Examen,
        respuestas: List[RespuestaEstudiante],
    ) -> InformeComparativo:
        """Ejecuta el análisis estadístico completo sobre las respuestas del grupo."""
        if not respuestas:
            return InformeComparativo(
                id_examen=examen.id_examen,
                titulo_examen=examen.titulo,
                total_evaluados=0,
                promedio_general=0.0,
                nota_maxima=None,
                nota_minima=None,
                ranking=[],
                estudiantes_maxima=[],
                estudiantes_minima=[],
            )

        resultados = self.calificar_grupo(examen, respuestas)

        ranking = sorted(
            resultados,
            key=lambda r: (r.nota, r.correctas, -r.incorrectas, r.nombre),
            reverse=True,
        )

        suma_notas = sum(r.nota for r in resultados)
        promedio = round(suma_notas / len(resultados), 2)

        puntaje_max = max(r.nota for r in resultados)
        puntaje_min = min(r.nota for r in resultados)

        maximos = [r for r in resultados if r.nota == puntaje_max]
        minimos = [r for r in resultados if r.nota == puntaje_min]

        return InformeComparativo(
            id_examen=examen.id_examen,
            titulo_examen=examen.titulo,
            total_evaluados=len(resultados),
            promedio_general=promedio,
            nota_maxima=maximos[0] if maximos else None,
            nota_minima=minimos[0] if minimos else None,
            ranking=ranking,
            estudiantes_maxima=maximos,
            estudiantes_minima=minimos,
        )
