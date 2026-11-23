"""
Conector con Google Calendar para el Asistente Persistente.

Permite:
- Autenticación OAuth 2.0 con persistencia de token (token.json).
- Listar eventos del día, semana o rango de fechas.
- Crear nuevos eventos con fecha, hora, duración y enlace opcional de Google Meet.
- Buscar espacios libres en la agenda para planificar tareas.
- Manejo elegante en caso de que credentials.json aún no esté configurado.
"""

from __future__ import annotations

import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Scopes para lectura y modificación de eventos del calendario
SCOPES = [
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/calendar.readonly"
]


class ConectorCalendar:
    """Gestiona la conexión y operaciones con la API de Google Calendar."""

    def __init__(self, ruta_credenciales: Optional[str | Path] = None, ruta_token: Optional[str | Path] = None):
        self.raiz_proyecto = Path(__file__).resolve().parent.parent

        # Ruta de credentials.json
        if ruta_credenciales:
            self.ruta_credenciales = Path(ruta_credenciales).resolve()
        else:
            env_cred = os.getenv("GOOGLE_CALENDAR_CREDENTIALS")
            if env_cred:
                self.ruta_credenciales = Path(env_cred).resolve()
            else:
                self.ruta_credenciales = self.raiz_proyecto / "credentials.json"

        # Ruta de token.json (almacenamiento del token persistente)
        if ruta_token:
            self.ruta_token = Path(ruta_token).resolve()
        else:
            self.ruta_token = self.raiz_proyecto / "token.json"

        self._servicio = None

    def tiene_credenciales(self) -> bool:
        """Verifica si el archivo credentials.json o token.json existe."""
        return self.ruta_token.exists() or self.ruta_credenciales.exists()

    def esta_autenticado(self) -> bool:
        """Verifica si ya existe un token válido y autenticado sin bloquear el hilo."""
        if self._servicio is not None:
            return True
        try:
            return self._obtener_servicio(interactivo=False) is not None
        except Exception:
            return False

    def _obtener_servicio(self, interactivo: bool = False):
        """Inicializa o recarga el cliente de servicio de Google Calendar."""
        if self._servicio is not None:
            return self._servicio

        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build
        except ImportError:
            return None

        creds = None
        # Si ya existe un token guardado previamente
        if self.ruta_token.exists():
            try:
                creds = Credentials.from_authorized_user_file(str(self.ruta_token), SCOPES)
            except Exception:
                creds = None

        # Si no hay credenciales válidas o expiraron
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    self.ruta_token.write_text(creds.to_json(), encoding="utf-8")
                except Exception:
                    creds = None

            if not creds:
                if not interactivo or not self.ruta_credenciales.exists():
                    return None
                flow = InstalledAppFlow.from_client_secrets_file(str(self.ruta_credenciales), SCOPES)
                creds = flow.run_local_server(port=0)
                self.ruta_token.write_text(creds.to_json(), encoding="utf-8")

        if creds and creds.valid:
            self._servicio = build("calendar", "v3", credentials=creds)
            return self._servicio
        return None

    def listar_eventos(
        self,
        fecha_inicio: Optional[datetime | date] = None,
        fecha_fin: Optional[datetime | date] = None,
        max_resultados: int = 15
    ) -> List[Dict[str, Any]]:
        """
        Lista los eventos dentro del rango indicado.
        Si no se indica rango, lista los eventos de hoy y los próximos 7 días.
        """
        servicio = self._obtener_servicio()
        if not servicio:
            return []

        ahora_utc = datetime.now(timezone.utc)
        if fecha_inicio is None:
            time_min = ahora_utc.isoformat()
        elif isinstance(fecha_inicio, date) and not isinstance(fecha_inicio, datetime):
            time_min = datetime.combine(fecha_inicio, datetime.min.time(), tzinfo=timezone.utc).isoformat()
        else:
            time_min = fecha_inicio.astimezone(timezone.utc).isoformat()

        if fecha_fin is None:
            # Por defecto 7 días adelante
            time_max = (ahora_utc + timedelta(days=7)).isoformat()
        elif isinstance(fecha_fin, date) and not isinstance(fecha_fin, datetime):
            time_max = datetime.combine(fecha_fin, datetime.max.time(), tzinfo=timezone.utc).isoformat()
        else:
            time_max = fecha_fin.astimezone(timezone.utc).isoformat()

        try:
            eventos_result = (
                servicio.events()
                .list(
                    calendarId="primary",
                    timeMin=time_min,
                    timeMax=time_max,
                    maxResults=max_resultados,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
            items = eventos_result.get("items", [])
            formateados = []

            for ev in items:
                inicio = ev.get("start", {}).get("dateTime", ev.get("start", {}).get("date"))
                fin = ev.get("end", {}).get("dateTime", ev.get("end", {}).get("date"))
                meet_link = ev.get("hangoutLink") or ev.get("conferenceData", {}).get("entryPoints", [{}])[0].get("uri")

                formateados.append({
                    "id": ev.get("id"),
                    "titulo": ev.get("summary", "Sin título"),
                    "inicio": inicio,
                    "fin": fin,
                    "descripcion": ev.get("description", ""),
                    "ubicacion": ev.get("location", ""),
                    "link_meet": meet_link or "",
                    "html_link": ev.get("htmlLink", "")
                })

            return formateados
        except Exception as exc:
            print(f"Error consultando Google Calendar: {exc}")
            return []

    def crear_evento(
        self,
        titulo: str,
        fecha_hora_inicio: datetime,
        duracion_minutos: int = 60,
        descripcion: str = "",
        ubicacion: str = "",
        con_meet: bool = False
    ) -> Dict[str, Any]:
        """Crea un nuevo evento en Google Calendar."""
        servicio = self._obtener_servicio()
        if not servicio:
            return {"error": "Google Calendar no está autenticado o falta credentials.json."}

        local_tz = datetime.now().astimezone().tzinfo
        if fecha_hora_inicio.tzinfo is None:
            fecha_hora_inicio = fecha_hora_inicio.replace(tzinfo=local_tz)

        fecha_hora_fin = fecha_hora_inicio + timedelta(minutes=duracion_minutos)

        cuerpo_evento: Dict[str, Any] = {
            "summary": titulo,
            "description": descripcion,
            "location": ubicacion,
            "start": {
                "dateTime": fecha_hora_inicio.isoformat(),
            },
            "end": {
                "dateTime": fecha_hora_fin.isoformat(),
            },
        }

        if con_meet:
            cuerpo_evento["conferenceData"] = {
                "createRequest": {
                    "requestId": f"meet_{int(datetime.now().timestamp())}",
                    "conferenceSolutionKey": {"type": "hangoutsMeet"}
                }
            }

        try:
            creado = (
                servicio.events()
                .insert(
                    calendarId="primary",
                    body=cuerpo_evento,
                    conferenceDataVersion=1 if con_meet else 0
                )
                .execute()
            )
            return {
                "exito": True,
                "id": creado.get("id"),
                "titulo": creado.get("summary"),
                "inicio": creado.get("start", {}).get("dateTime"),
                "fin": creado.get("end", {}).get("dateTime"),
                "link_meet": creado.get("hangoutLink", ""),
                "html_link": creado.get("htmlLink", "")
            }
        except Exception as exc:
            return {"exito": False, "error": str(exc)}

    def obtener_resumen_hoy(self) -> List[Dict[str, Any]]:
        """Obtiene todos los eventos correspondientes al día de hoy."""
        hoy = date.today()
        inicio_hoy = datetime.combine(hoy, datetime.min.time(), tzinfo=timezone.utc)
        fin_hoy = datetime.combine(hoy, datetime.max.time(), tzinfo=timezone.utc)
        return self.listar_eventos(fecha_inicio=inicio_hoy, fecha_fin=fin_hoy, max_resultados=20)
