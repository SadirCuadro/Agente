"""
Módulo para el envío de exámenes mediante SMTP.

Compatible con proveedores como Gmail, Outlook/Office365 y servidores SMTP corporativos,
utilizando contraseñas de aplicación (App Passwords) y cifrado seguro STARTTLS / SSL.
"""

from __future__ import annotations

import logging
import smtplib
from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Optional, Tuple

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("EvaluadorCorreo")


@dataclass
class ConfiguracionSMTP:
    """Parámetros de conexión con el servidor SMTP.

    Attributes:
        servidor: Dirección del host SMTP (ej. 'smtp.gmail.com', 'smtp.office365.com').
        puerto: Puerto del servicio (587 para STARTTLS, 465 para SSL directo).
        usuario: Dirección de correo del remitente o usuario de autenticación.
        password: Clave de autenticación o contraseña de aplicación (App Password).
        usar_tls: Booleano que indica si se inicia conexión TLS explícita (STARTTLS).
        usar_ssl: Booleano que indica si la conexión es SSL directa (puerto 465).
        remitente_nombre: Nombre visible para la cabecera 'From' (ej. 'Profesor / Academia').
        tiempo_espera_segundos: Timeout para la conexión con el servidor SMTP.
    """

    servidor: str = "smtp.gmail.com"
    puerto: int = 587
    usuario: str = ""
    password: str = ""
    usar_tls: bool = True
    usar_ssl: bool = False
    remitente_nombre: str = "Sistema de Evaluación"
    tiempo_espera_segundos: int = 15

    def __post_init__(self) -> None:
        self.usuario = self.usuario.strip()
        if "gmail" in self.servidor.lower():
            self.password = self.password.replace(" ", "").strip()
        else:
            self.password = self.password.strip()


class GestorCorreo:
    """Administrador para la composición y envío de correos electrónicos vía SMTP."""

    def __init__(self, config: Optional[ConfiguracionSMTP] = None, modo_simulacion: bool = False):
        """Inicializa el gestor de correo.

        Args:
            config: Configuración de servidor SMTP y credenciales.
            modo_simulacion: Si es True, no abre sockets SMTP reales; simula el
              proceso e imprime en registro. Muy útil para entornos de prueba o
              desarrollo.
        """
        self.config = config or ConfiguracionSMTP()
        self.modo_simulacion = modo_simulacion

    def verificar_credenciales(self) -> Tuple[bool, str]:
        """Comprueba la conectividad y validez de las credenciales con el servidor SMTP.

        Returns:
            Una tupla (éxito: bool, mensaje: str).
        """
        if self.modo_simulacion:
            return True, "Modo simulación activo: no se validan credenciales reales en red."

        if not self.config.usuario or not self.config.password:
            return False, "Faltan credenciales: 'usuario' y/o 'password' no configurados."

        try:
            if self.config.usar_ssl:
                with smtplib.SMTP_SSL(
                    self.config.servidor,
                    self.config.puerto,
                    timeout=self.config.tiempo_espera_segundos,
                ) as servidor:
                    servidor.login(self.config.usuario, self.config.password)
            else:
                with smtplib.SMTP(
                    self.config.servidor,
                    self.config.puerto,
                    timeout=self.config.tiempo_espera_segundos,
                ) as servidor:
                    servidor.ehlo()
                    if self.config.usar_tls:
                        servidor.starttls()
                        servidor.ehlo()
                    servidor.login(self.config.usuario, self.config.password)

            return True, "Conexión y autenticación SMTP exitosa."

        except smtplib.SMTPAuthenticationError as err:
            msg = (
                f"Error de autenticación SMTP: Las credenciales son incorrectas. "
                f"Para Gmail o Outlook, asegúrate de usar una 'Contraseña de Aplicación'. Detalle: {err}"
            )
            logger.error(msg)
            return False, msg
        except (smtplib.SMTPConnectError, smtplib.SMTPServerDisconnected, TimeoutError) as err:
            msg = f"Error de conexión con el servidor SMTP ({self.config.servidor}:{self.config.puerto}): {err}"
            logger.error(msg)
            return False, msg
        except smtplib.SMTPException as err:
            msg = f"Excepción general SMTP: {err}"
            logger.error(msg)
            return False, msg
        except Exception as err:
            msg = f"Error inesperado al conectar con el servidor de correo: {err}"
            logger.error(msg)
            return False, msg

    def enviar_examen(
        self,
        destinatario: str,
        asunto: str,
        cuerpo_texto: str,
        cuerpo_html: Optional[str] = None,
    ) -> bool:
        """Envía un correo con el examen a un destinatario específico.

        Args:
            destinatario: Dirección de correo del estudiante.
            asunto: Asunto del mensaje.
            cuerpo_texto: Contenido del examen en texto plano.
            cuerpo_html: Opcional, contenido formateado en HTML.

        Returns:
            True si se envió (o simuló) satisfactoriamente, False en caso de
            error.
        """
        if self.modo_simulacion:
            logger.info(
                f"[SIMULACIÓN DE ENVÍO] -> Para: {destinatario} | Asunto: {asunto} | "
                f"Tamaño contenido: {len(cuerpo_texto)} caracteres."
            )
            return True

        if not self.config.usuario or not self.config.password:
            logger.error(
                f"No es posible enviar correo a {destinatario}: faltan credenciales SMTP. "
                "Active el modo simulación o proporcione credenciales válidas."
            )
            return False

        # Construir mensaje MIME
        mensaje = MIMEMultipart("alternative")
        mensaje["Subject"] = asunto
        mensaje["From"] = f"{self.config.remitente_nombre} <{self.config.usuario}>"
        mensaje["To"] = destinatario

        # Parte texto plano (obligatoria)
        parte_texto = MIMEText(cuerpo_texto, "plain", "utf-8")
        mensaje.attach(parte_texto)

        # Parte HTML (si está disponible)
        if cuerpo_html:
            parte_html = MIMEText(cuerpo_html, "html", "utf-8")
            mensaje.attach(parte_html)

        try:
            if self.config.usar_ssl:
                with smtplib.SMTP_SSL(
                    self.config.servidor,
                    self.config.puerto,
                    timeout=self.config.tiempo_espera_segundos,
                ) as servidor:
                    servidor.login(self.config.usuario, self.config.password)
                    servidor.sendmail(self.config.usuario, [destinatario], mensaje.as_string())
            else:
                with smtplib.SMTP(
                    self.config.servidor,
                    self.config.puerto,
                    timeout=self.config.tiempo_espera_segundos,
                ) as servidor:
                    servidor.ehlo()
                    if self.config.usar_tls:
                        servidor.starttls()
                        servidor.ehlo()
                    servidor.login(self.config.usuario, self.config.password)
                    servidor.sendmail(self.config.usuario, [destinatario], mensaje.as_string())

            logger.info(f"Correo de examen enviado con éxito a {destinatario}.")
            return True

        except smtplib.SMTPAuthenticationError as err:
            logger.error(f"Fallo de autenticación al enviar a {destinatario}: {err}")
            return False
        except smtplib.SMTPRecipientsRefused as err:
            logger.error(f"El destinatario {destinatario} fue rechazado por el servidor: {err}")
            return False
        except (smtplib.SMTPException, TimeoutError) as err:
            logger.error(f"Fallo de envío SMTP hacia {destinatario}: {err}")
            return False
        except Exception as err:
            logger.error(f"Fallo no previsto al enviar correo a {destinatario}: {err}")
            return False

    def enviar_examen_masivo(
        self,
        estudiantes: List[Tuple[str, str]],
        asunto: str,
        generador_cuerpo_callback,
    ) -> Dict[str, bool]:
        """Envía el examen a una lista de estudiantes.

        Args:
            estudiantes: Lista de tuplas (nombre, correo).
            asunto: Asunto del correo.
            generador_cuerpo_callback: Función callable(nombre) -> str que
              genera el cuerpo personalizado.

        Returns:
            Diccionario {correo: exito_booleano}.
        """
        resultados = {}
        for nombre, correo in estudiantes:
            cuerpo = generador_cuerpo_callback(nombre)
            exito = self.enviar_examen(destinatario=correo, asunto=asunto, cuerpo_texto=cuerpo)
            resultados[correo] = exito
        return resultados
