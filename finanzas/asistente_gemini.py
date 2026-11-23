"""
Módulo del Asistente Financiero y Coach de Ahorro impulsado por Gemini.

Proporciona asesoramiento consultivo sobre finanzas personales, análisis de fugas
de dinero ("gastos hormiga") y recomendaciones estratégicas contextualizadas.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Generator, List, Optional

from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("AsistenteFinanciero")


class AsistenteFinanciero:
    """Coach financiero conversacional que razona con el contexto de gastos del usuario."""

    def __init__(self, api_key: Optional[str] = None, model_id: Optional[str] = None):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY", "")
        self.model_id = model_id or os.getenv("GOOGLE_MODEL_ID", "gemini-2.5-flash")
        self._cliente = None

    def _obtener_cliente(self):
        if self._cliente is None and self.api_key:
            try:
                from google import genai
                self._cliente = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.error(f"Error al inicializar cliente genai: {e}")
        return self._cliente

    def construir_contexto_financiero(self, metricas: Dict[str, Any]) -> str:
        """Sintetiza las métricas actuales del usuario en un prompt de contexto."""
        total = metricas.get("total_gastado", 0.0)
        presupuesto = metricas.get("presupuesto_total", 0.0)
        restante = metricas.get("restante", 0.0)
        pct = metricas.get("porcentaje_consumido", 0.0)
        estado = metricas.get("estado_global", "NORMAL")

        lineas = [
            f"- Presupuesto Total Mensual: ${presupuesto:,.0f} COP",
            f"- Total Gastado hasta la fecha: ${total:,.0f} COP ({pct:.1f}% del límite)",
            f"- Presupuesto Disponible: ${restante:,.0f} COP",
            f"- Estado de Alerta General: {estado}",
            "- Desglose de Gastos por Categoría:",
        ]

        for cat, monto in metricas.get("por_categoria", {}).items():
            lineas.append(f"  * {cat}: ${monto:,.0f} COP")

        alertas = metricas.get("alertas_categoria", [])
        if alertas:
            lineas.append("- Alertas de Categorías Críticas o en Riesgo:")
            for a in alertas:
                lineas.append(f"  ! {a.get('mensaje')}")

        comercios = metricas.get("top_comercios", [])
        if comercios:
            lineas.append("- Principales Establecimientos donde más se ha gastado:")
            for com, monto in comercios:
                lineas.append(f"  * {com}: ${monto:,.0f} COP")

        return "\n".join(lineas)

    def responder_consulta(
        self,
        mensaje_usuario: str,
        metricas: Dict[str, Any],
        historial_mensajes: Optional[List[Dict[str, str]]] = None,
    ) -> Generator[str, None, None]:
        """Genera una respuesta en streaming contextualizada con las finanzas del usuario."""
        contexto_datos = self.construir_contexto_financiero(metricas)

        prompt_sistema = f"""
Eres "Coach Financiero", el asesor financiero personal y consultor de ahorro de la plataforma "Foto y Control".
Tu objetivo es ayudar al usuario a tomar decisiones inteligentes con su dinero, reducir gastos superfluos ("gastos hormiga") y optimizar su presupuesto.

ESTADO FINANCIERO REAL DEL USUARIO ESTE MES:
{contexto_datos}

INSTRUCCIONES DE RESPUESTA:
- Sé empático, práctico, directo y analítico.
- Si te piden consejos de ahorro, básate en los datos reales que ves arriba (categorías con mayor gasto o alertas).
- Si el presupuesto está en "PELIGRO" o "ADVERTENCIA", sugiere acciones de contención inmediatas.
- Usa formato Markdown con viñetas claras y negritas.
- Habla en español cordial y profesional.
"""

        cliente = self._obtener_cliente()
        if cliente is not None:
            try:
                # Construir contenido para Gemini
                prompt_completo = f"{prompt_sistema}\n\nPregunta del usuario: {mensaje_usuario}"

                # Llamada con streaming nativo de google-genai
                response_stream = cliente.models.generate_content_stream(
                    model=self.model_id,
                    contents=prompt_completo,
                )
                for chunk in response_stream:
                    if chunk.text:
                        yield chunk.text
                return
            except Exception as e:
                logger.warning(f"Error en streaming de Gemini ({e}). Usando generador local.")

        # Fallback analítico local si no hay conexión externa
        yield from self._respuesta_analitica_local(mensaje_usuario, metricas)

    def _respuesta_analitica_local(
        self,
        mensaje: str,
        metricas: Dict[str, Any],
    ) -> Generator[str, None, None]:
        """Motor de consejos heurísticos locales cuando el modelo remoto no está disponible."""
        total = metricas.get("total_gastado", 0.0)
        pct = metricas.get("porcentaje_consumido", 0.0)
        restante = metricas.get("restante", 0.0)
        por_cat = metricas.get("por_categoria", {})
        top_cat = max(por_cat.items(), key=lambda x: x[1]) if por_cat else ("Sin gastos", 0.0)

        mensaje_lower = mensaje.lower()
        if "resumen" in mensaje_lower or "balance" in mensaje_lower or "cómo voy" in mensaje_lower:
            texto = (
                f"### 📊 Resumen Ejecutivo de tu Mes\n\n"
                f"Hasta el momento has gastado **${total:,.0f} COP**, lo que representa el **{pct:.1f}%** de tu presupuesto mensual.\n\n"
                f"- **Presupuesto Disponible:** ${restante:,.0f} COP.\n"
                f"- **Categoría con mayor consumo:** **{top_cat[0]}** con ${top_cat[1]:,.0f} COP.\n\n"
                f"💡 **Recomendación:** Mantén el ritmo en las categorías básicas y restringe consumos no esenciales para cerrar el mes con balance positivo."
            )
        elif "ahorro" in mensaje_lower or "reducir" in mensaje_lower or "consejo" in mensaje_lower:
            texto = (
                f"### 💡 Estrategia Personalizada de Ahorro\n\n"
                f"Revisando tus números, tu mayor volumen de gasto está en **{top_cat[0]}** (${top_cat[1]:,.0f} COP).\n\n"
                f"1. **Regla del 50/30/20:** Destina el 50% a necesidades básicas, 30% a estilo de vida y 20% directamente a tu fondo de ahorro o inversión.\n"
                f"2. **Caza los 'gastos hormiga':** Pequeños consumos diarios en café o snacks pueden sumar más del 15% de tu disponible mensual.\n"
                f"3. **Planifica compras:** Haz listas de compras semanales para evitar compras impulsivas en supermercados."
            )
        else:
            texto = (
                f"### 🤝 Análisis Financiero\n\n"
                f"Tu saldo disponible para lo que queda del mes es de **${restante:,.0f} COP** ({100 - pct:.1f}% del total).\n\n"
                f"Cuentas con un estado financiero clasificado como **{metricas.get('estado_global', 'NORMAL')}**.\n"
                f"¿En qué categoría específica o hábito de compra te gustaría que profundicemos?"
            )

        # Simular streaming por palabras
        for palabra in texto.split(" "):
            yield palabra + " "
