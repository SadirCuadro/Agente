"""
Módulo para el envío de reportes y balances financieros consolidados vía SMTP.

Compatible con Gmail, Outlook y servidores corporativos mediante STARTTLS y SSL.
"""

from __future__ import annotations

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("GestorReporteCorreo")


class GestorReporteCorreo:
    """Administra la composición y envío de resúmenes ejecutivos de gastos."""

    def __init__(
        self,
        servidor: Optional[str] = None,
        puerto: Optional[int] = None,
        usuario: Optional[str] = None,
        password: Optional[str] = None,
        remitente: Optional[str] = None,
    ):
        self.servidor = servidor or os.getenv("SMTP_HOST") or os.getenv("SMTP_SERVER") or "smtp.gmail.com"
        self.puerto = puerto or int(os.getenv("SMTP_PORT") or "587")
        self.usuario = (usuario or os.getenv("SMTP_USER") or "").strip()
        pwd_raw = password or os.getenv("SMTP_PASSWORD") or os.getenv("SMTP_PASS") or ""
        self.password = pwd_raw.replace(" ", "").strip()
        self.remitente = remitente or os.getenv("EMAIL_FROM") or "Foto y Control - Finanzas Inteligentes"

    def generar_cuerpo_html(self, metricas: Dict[str, Any]) -> str:
        """Crea una plantilla HTML moderna y responsiva para el reporte financiero."""
        total_gastado = metricas.get("total_gastado", 0.0)
        presupuesto_total = metricas.get("presupuesto_total", 0.0)
        restante = metricas.get("restante", 0.0)
        pct = metricas.get("porcentaje_consumido", 0.0)
        estado = metricas.get("estado_global", "SALUDABLE")
        color_badge = "#10b981" if estado == "SALUDABLE" else ("#f59e0b" if "ADVERTENCIA" in estado else "#ef4444")

        # Filas por categoría
        filas_cat = ""
        for cat, monto in metricas.get("por_categoria", {}).items():
            filas_cat += f"""
            <tr>
                <td style="padding: 8px 12px; border-bottom: 1px solid #e5e7eb;">{cat}</td>
                <td style="padding: 8px 12px; border-bottom: 1px solid #e5e7eb; text-align: right; font-weight: bold;">${monto:,.0f} COP</td>
            </tr>
            """

        # Filas top comercios
        filas_comercios = ""
        for com, monto in metricas.get("top_comercios", []):
            filas_comercios += f"""
            <tr>
                <td style="padding: 8px 12px; border-bottom: 1px solid #e5e7eb;">{com}</td>
                <td style="padding: 8px 12px; border-bottom: 1px solid #e5e7eb; text-align: right; font-weight: bold;">${monto:,.0f} COP</td>
            </tr>
            """

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: 'Segoe UI', Arial, sans-serif; background-color: #f3f4f6; color: #1f2937; margin: 0; padding: 20px; }}
                .card {{ max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }}
                .header {{ background: linear-gradient(135deg, #1e3a8a, #3b82f6); color: #ffffff; padding: 24px; text-align: center; }}
                .content {{ padding: 24px; }}
                .kpi-grid {{ display: flex; justify-content: space-between; margin-bottom: 24px; }}
                .kpi-box {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; flex: 1; margin: 0 4px; text-align: center; }}
                .kpi-title {{ font-size: 11px; text-transform: uppercase; color: #64748b; margin-bottom: 4px; }}
                .kpi-val {{ font-size: 16px; font-weight: bold; color: #0f172a; }}
                .badge {{ display: inline-block; padding: 4px 12px; border-radius: 9999px; color: #ffffff; font-weight: bold; font-size: 12px; background: {color_badge}; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 13px; }}
                th {{ background: #f8fafc; padding: 10px 12px; text-align: left; font-size: 12px; color: #475569; border-bottom: 2px solid #e2e8f0; }}
                .footer {{ text-align: center; font-size: 11px; color: #94a3b8; padding: 16px; border-top: 1px solid #e5e7eb; }}
            </style>
        </head>
        <body>
            <div class="card">
                <div class="header">
                    <h2 style="margin: 0; font-size: 20px;">💳 Reporte Ejecutivo de Finanzas</h2>
                    <p style="margin: 6px 0 0 0; font-size: 13px; opacity: 0.9;">Plataforma "Foto y Control" - Balance Mensual</p>
                </div>
                <div class="content">
                    <div style="text-align: center; margin-bottom: 20px;">
                        <span class="badge">Estado de Presupuesto: {estado}</span>
                    </div>

                    <table style="margin-bottom: 24px;">
                        <tr>
                            <td style="padding: 10px; background: #eff6ff; border-radius: 8px; text-align: center;">
                                <div style="font-size: 11px; color: #3b82f6; font-weight: bold;">TOTAL GASTADO</div>
                                <div style="font-size: 20px; font-weight: bold; color: #1e3a8a;">${total_gastado:,.0f} COP</div>
                            </td>
                            <td style="width: 10px;"></td>
                            <td style="padding: 10px; background: #f0fdf4; border-radius: 8px; text-align: center;">
                                <div style="font-size: 11px; color: #16a34a; font-weight: bold;">PRESUPUESTO DISPONIBLE</div>
                                <div style="font-size: 20px; font-weight: bold; color: #15803d;">${restante:,.0f} COP</div>
                            </td>
                            <td style="width: 10px;"></td>
                            <td style="padding: 10px; background: #fefce8; border-radius: 8px; text-align: center;">
                                <div style="font-size: 11px; color: #ca8a04; font-weight: bold;">% CONSUMIDO</div>
                                <div style="font-size: 20px; font-weight: bold; color: #a16207;">{pct:.1f}%</div>
                            </td>
                        </tr>
                    </table>

                    <h4 style="margin: 20px 0 8px 0; color: #1e3a8a;">📊 Gastos por Categoría</h4>
                    <table>
                        <thead>
                            <tr>
                                <th>Categoría</th>
                                <th style="text-align: right;">Total Gastado</th>
                            </tr>
                        </thead>
                        <tbody>
                            {filas_cat}
                        </tbody>
                    </table>

                    <h4 style="margin: 20px 0 8px 0; color: #1e3a8a;">🏪 Principales Comercios</h4>
                    <table>
                        <thead>
                            <tr>
                                <th>Establecimiento</th>
                                <th style="text-align: right;">Monto Total</th>
                            </tr>
                        </thead>
                        <tbody>
                            {filas_comercios}
                        </tbody>
                    </table>

                    <div style="background: #eff6ff; border-left: 4px solid #2563eb; padding: 12px 16px; border-radius: 6px; margin-top: 24px; font-size: 13px;">
                        <b>💡 Consejo de Ahorro del Asistente Gemini:</b><br>
                        "Mantén monitoreados los gastos hormiga en salidas y restaurantes para no comprometer tu fondo de emergencia este mes."
                    </div>
                </div>
                <div class="footer">
                    Generado automáticamente por Foto y Control &copy; 2026.
                </div>
            </div>
        </body>
        </html>
        """
        return html

    def generar_cuerpo_texto(self, metricas: Dict[str, Any]) -> str:
        """Versión en texto plano para clientes de correo sin soporte HTML."""
        total = metricas.get("total_gastado", 0.0)
        restante = metricas.get("restante", 0.0)
        pct = metricas.get("porcentaje_consumido", 0.0)
        estado = metricas.get("estado_global", "NORMAL")

        lineas = [
            "=" * 60,
            "REPORTE EJECUTIVO DE FINANZAS - FOTO Y CONTROL",
            "=" * 60,
            f"Estado General       : {estado}",
            f"Total Gastado        : ${total:,.0f} COP",
            f"Presupuesto Restante : ${restante:,.0f} COP",
            f"Porcentaje Consumido : {pct:.1f}%",
            "-" * 60,
            "GASTOS POR CATEGORÍA:",
        ]
        for cat, monto in metricas.get("por_categoria", {}).items():
            lineas.append(f"  * {cat:<25}: ${monto:,.0f} COP")

        lineas.extend([
            "-" * 60,
            "TOP COMERCIOS:",
        ])
        for com, monto in metricas.get("top_comercios", []):
            lineas.append(f"  * {com:<25}: ${monto:,.0f} COP")

        lineas.extend([
            "=" * 60,
            "Generado por Foto y Control.",
        ])
        return "\n".join(lineas)

    def enviar_reporte(
        self,
        destinatario: str,
        metricas: Dict[str, Any],
        asunto: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """Envía el balance financiero vía SMTP con alternativas multipart HTML/texto."""
        if not self.usuario or not self.password:
            return False, "Faltan credenciales SMTP (SMTP_USER o SMTP_PASSWORD en .env)."

        asunto_correo = asunto or "📊 Balance Financiero Mensual - Foto y Control"
        cuerpo_html = self.generar_cuerpo_html(metricas)
        cuerpo_texto = self.generar_cuerpo_texto(metricas)

        mensaje = MIMEMultipart("alternative")
        mensaje["Subject"] = asunto_correo
        mensaje["From"] = f"{self.remitente} <{self.usuario}>"
        mensaje["To"] = destinatario

        mensaje.attach(MIMEText(cuerpo_texto, "plain", "utf-8"))
        mensaje.attach(MIMEText(cuerpo_html, "html", "utf-8"))

        try:
            with smtplib.SMTP(self.servidor, self.puerto, timeout=15) as servidor:
                servidor.ehlo()
                servidor.starttls()
                servidor.ehlo()
                servidor.login(self.usuario, self.password)
                servidor.sendmail(self.usuario, [destinatario], mensaje.as_string())

            logger.info(f"Reporte de gastos enviado exitosamente a {destinatario}")
            return True, f"Reporte enviado exitosamente a {destinatario}."
        except Exception as err:
            logger.error(f"Error enviando correo a {destinatario}: {err}")
            return False, f"Fallo al enviar correo: {err}"
