"""
Módulo de Finanzas: "Foto y Control" - Gestor Inteligente de Gastos y Facturas.

Componentes:
- gestor_presupuesto: Lógica de almacenamiento, KPIs, categorías y alertas.
- extractor_recibos: Extracción multimodal de datos desde fotos de recibos con Gemini.
- gestor_reporte_correo: Envío de balances financieros por correo vía SMTP.
- asistente_gemini: Chatbot financiero consultivo y coach de ahorro.
"""

from .gestor_presupuesto import GestorPresupuesto, Gasto, PresupuestoConfig
from .extractor_recibos import ExtractorRecibos, ReciboExtraido
from .gestor_reporte_correo import GestorReporteCorreo
from .asistente_gemini import AsistenteFinanciero

__all__ = [
    "GestorPresupuesto",
    "Gasto",
    "PresupuestoConfig",
    "ExtractorRecibos",
    "ReciboExtraido",
    "GestorReporteCorreo",
    "AsistenteFinanciero",
]

__version__ = "1.0.0"
