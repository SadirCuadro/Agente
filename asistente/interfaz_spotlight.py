"""
Interfaz de Usuario Spotlight / Raycast para el Asistente Persistente.

Características:
- Ventana flotante sin marco (frameless) con estilo oscuro moderno y bordes redondeados.
- Atajo global en Windows (Ctrl + Espacio) para invocar o esconder la ventana instantáneamente.
- Icono residente en la bandeja del sistema (System Tray) con menú y notificaciones nativas.
- Botones de acción rápida: Briefing Matutino, Mi Agenda de Hoy, Tareas de Obsidian y Captura Rápida.
- Renderizado de respuestas con soporte Markdown.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import sys
from pathlib import Path
from typing import Optional

from PySide6.QtCore import (
    QAbstractNativeEventFilter,
    QEvent,
    QObject,
    QPoint,
    QRectF,
    QSize,
    Qt,
    QThread,
    QTimer,
    Signal,
)
from PySide6.QtGui import (
    QColor,
    QCursor,
    QFont,
    QIcon,
    QKeySequence,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QShortcut,
)
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStyle,
    QSystemTrayIcon,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from asistente.cerebro_gemini import CerebroGemini
from asistente.motor_proactivo import MotorProactivo

# Constantes de Windows API para Hotkey global
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
VK_SPACE = 0x20
WM_HOTKEY = 0x0312
HOTKEY_ID_GLOBAL = 9001


class BridgeHotkey(QObject):
    """Puente seguro con señal de Qt para invocar la ventana desde el hook de teclado."""
    toggle_solicitado = Signal()


class MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("message", wintypes.UINT),
        ("wParam", wintypes.WPARAM),
        ("lParam", wintypes.LPARAM),
        ("time", wintypes.DWORD),
        ("pt", wintypes.POINT),
    ]


class FiltroHotkeyWindows(QAbstractNativeEventFilter):
    """Filtro de eventos nativos de Windows para interceptar el atajo Ctrl + Espacio."""

    def __init__(self, callback_toggle):
        super().__init__()
        self.callback_toggle = callback_toggle

    def nativeEventFilter(self, event_type, message):
        if event_type == b"windows_generic_MSG":
            msg = MSG.from_address(int(message))
            if msg.message == WM_HOTKEY and msg.wParam == HOTKEY_ID_GLOBAL:
                self.callback_toggle()
                return True, 0
        return False, 0


def crear_icono_asistente() -> QIcon:
    """Genera dinámicamente un icono nítido y moderno para la bandeja del sistema."""
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Fondo circular degradado
    path = QPainterPath()
    path.addRoundedRect(QRectF(4, 4, 56, 56), 16, 16)
    painter.fillPath(path, QColor(124, 77, 255))  # Púrpura eléctrico

    # Símbolo central de brillo / cerebro
    painter.setPen(QPen(QColor(255, 255, 255), 4))
    painter.drawLine(32, 16, 32, 48)
    painter.drawLine(16, 32, 48, 32)
    painter.drawEllipse(QPoint(32, 32), 6, 6)
    painter.end()

    return QIcon(pixmap)


class WorkerConsulta(QThread):
    """
    Trabajador en segundo plano para procesar consultas a Gemini o generar briefings
    sin bloquear el hilo principal de la interfaz Qt ni hacer que Windows la marque como 'No responde'.
    """
    resultado_listo = Signal(dict)
    error_ocurrido = Signal(str)

    def __init__(self, cerebro: CerebroGemini, texto: str = "", es_briefing: bool = False):
        super().__init__()
        self.cerebro = cerebro
        self.texto = texto
        self.es_briefing = es_briefing

    def run(self):
        try:
            if self.es_briefing:
                texto_briefing = self.cerebro.generar_briefing_matutino()
                self.resultado_listo.emit({
                    "exito": True,
                    "respuesta": texto_briefing,
                    "es_briefing": True
                })
            else:
                resultado = self.cerebro.procesar_mensaje(self.texto)
                self.resultado_listo.emit(resultado)
        except Exception as exc:
            self.error_ocurrido.emit(str(exc))


class VentanaSpotlight(QWidget):
    """Ventana emergente minimalista estilo Raycast/Spotlight."""

    def __init__(self, cerebro: CerebroGemini):
        super().__init__()
        self.cerebro = cerebro
        self._worker: Optional[WorkerConsulta] = None
        self._arrastrando = False
        self._pos_arrastre = QPoint()

        self._configurar_ventana()
        self._construir_ui()
        self._centrar_en_pantalla()

    def _configurar_ventana(self) -> None:
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.resize(720, 520)

        # Atajo Esc para cerrar / ocultar
        shortcut_esc = QShortcut(QKeySequence("Esc"), self)
        shortcut_esc.activated.connect(self.hide)

        # Atajo Ctrl+L para limpiar
        shortcut_clear = QShortcut(QKeySequence("Ctrl+L"), self)
        shortcut_clear.activated.connect(self._limpiar_pantalla)

        # Control de debounce para evitar que un único pulso abra y cierre de inmediato
        self._ultimo_toggle_ms = 0

    def _construir_ui(self) -> None:
        layout_principal = QVBoxLayout(self)
        layout_principal.setContentsMargins(12, 12, 12, 12)

        # Contenedor central con estilo oscuro elegante
        self.tarjeta_fondo = QFrame(self)
        self.tarjeta_fondo.setObjectName("TarjetaFondo")
        self.tarjeta_fondo.setStyleSheet("""
            QFrame#TarjetaFondo {
                background-color: rgba(22, 22, 30, 0.96);
                border: 1px solid rgba(124, 77, 255, 0.35);
                border-radius: 18px;
            }
        """)

        layout_tarjeta = QVBoxLayout(self.tarjeta_fondo)
        layout_tarjeta.setContentsMargins(20, 18, 20, 16)
        layout_tarjeta.setSpacing(14)

        # ---------------------------------------------------------------------
        # 1. Barra de Búsqueda y Entrada Superior
        # ---------------------------------------------------------------------
        layout_entrada = QHBoxLayout()
        layout_entrada.setSpacing(10)

        self.icono_gemini = QLabel("✦")
        self.icono_gemini.setStyleSheet("color: #7c4dff; font-size: 22px; font-weight: bold;")
        layout_entrada.addWidget(self.icono_gemini)

        self.input_consulta = QLineEdit()
        self.input_consulta.setPlaceholderText("Pregúntame algo, agenda una cita o anota una tarea...")
        self.input_consulta.setStyleSheet("""
            QLineEdit {
                background-color: transparent;
                border: none;
                color: #ffffff;
                font-size: 16px;
                padding: 6px 0px;
                selection-background-color: #7c4dff;
            }
        """)
        self.input_consulta.returnPressed.connect(self._enviar_consulta)
        layout_entrada.addWidget(self.input_consulta)

        self.btn_enviar = QPushButton("↵")
        self.btn_enviar.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_enviar.setToolTip("Enviar mensaje (Enter)")
        self.btn_enviar.setStyleSheet("""
            QPushButton {
                background-color: #7c4dff;
                color: #ffffff;
                border-radius: 10px;
                padding: 4px 12px;
                font-weight: bold;
                font-size: 15px;
                border: none;
            }
            QPushButton:hover {
                background-color: #956aff;
            }
        """)
        self.btn_enviar.clicked.connect(self._enviar_consulta)
        layout_entrada.addWidget(self.btn_enviar)

        self.btn_cerrar = QPushButton("✕")
        self.btn_cerrar.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_cerrar.setToolTip("Ocultar ventana (Esc)")
        self.btn_cerrar.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #94a3b8;
                border-radius: 8px;
                padding: 4px 8px;
                font-size: 13px;
                border: none;
            }
            QPushButton:hover {
                background-color: rgba(239, 68, 68, 0.2);
                color: #ef4444;
            }
        """)
        self.btn_cerrar.clicked.connect(self.hide)
        layout_entrada.addWidget(self.btn_cerrar)

        layout_tarjeta.addLayout(layout_entrada)

        # Línea separadora sutil
        linea = QFrame()
        linea.setFrameShape(QFrame.Shape.HLine)
        linea.setStyleSheet("color: rgba(255, 255, 255, 0.08);")
        layout_tarjeta.addWidget(linea)

        # ---------------------------------------------------------------------
        # 2. Píldoras de Acciones Rápidas (Quick Actions)
        # ---------------------------------------------------------------------
        layout_pildoras = QHBoxLayout()
        layout_pildoras.setSpacing(8)

        self.btn_pildora_briefing = self._crear_boton_pildora("☀️ Briefing Hoy", self._accion_briefing)
        self.btn_pildora_agenda = self._crear_boton_pildora("📅 Mi Agenda", self._accion_agenda)
        self.btn_pildora_tareas = self._crear_boton_pildora("✅ Tareas Obsidian", self._accion_tareas)
        self.btn_pildora_captura = self._crear_boton_pildora("📥 Captura Rápida", self._accion_captura)

        layout_pildoras.addWidget(self.btn_pildora_briefing)
        layout_pildoras.addWidget(self.btn_pildora_agenda)
        layout_pildoras.addWidget(self.btn_pildora_tareas)
        layout_pildoras.addWidget(self.btn_pildora_captura)
        layout_pildoras.addStretch()

        layout_tarjeta.addLayout(layout_pildoras)

        # ---------------------------------------------------------------------
        # 3. Área de Respuesta y Contenido
        # ---------------------------------------------------------------------
        self.visor_respuesta = QTextBrowser()
        self.visor_respuesta.setOpenExternalLinks(True)
        self.visor_respuesta.setStyleSheet("""
            QTextBrowser {
                background-color: rgba(14, 14, 20, 0.75);
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 12px;
                color: #e2e8f0;
                font-family: 'Segoe UI', system-ui, sans-serif;
                font-size: 14px;
                padding: 14px;
                line-height: 1.5;
            }
            QScrollBar:vertical {
                border: none;
                background: transparent;
                width: 6px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.2);
                min-height: 20px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(124, 77, 255, 0.6);
            }
        """)
        self.visor_respuesta.setHtml(
            "<div style='color: #94a3b8; font-size: 13.5px;'>"
            "👋 <b>¡Hola! Soy tu Asistente Persistente.</b><br><br>"
            "Estoy conectado a tu <b>Obsidian Vault</b> y <b>Google Calendar</b>.<br>"
            "Pídeme cosas como:<br>"
            "• <i>'¿Qué tareas tengo pendientes hoy en Obsidian?'</i><br>"
            "• <i>'Añade a mi lista de hoy: preparar informe para las 4pm'</i><br>"
            "• <i>'¿Qué tengo agendado para esta semana en Calendar?'</i><br>"
            "• <i>'Dame mi briefing del día'</i>"
            "</div>"
        )
        layout_tarjeta.addWidget(self.visor_respuesta, stretch=1)

        # ---------------------------------------------------------------------
        # 4. Pie de Ventana (Barra de Estado y Atajos)
        # ---------------------------------------------------------------------
        layout_pie = QHBoxLayout()
        self.lbl_estado = QLabel("Listo")
        self.lbl_estado.setStyleSheet("color: #64748b; font-size: 12px;")
        layout_pie.addWidget(self.lbl_estado)

        layout_pie.addStretch()

        lbl_atajos = QLabel("[Enter] Enviar  •  [Esc] Ocultar  •  [Ctrl+L] Limpiar  •  Atajo Global: Ctrl+Espacio")
        lbl_atajos.setStyleSheet("color: #64748b; font-size: 11px;")
        layout_pie.addWidget(lbl_atajos)

        layout_tarjeta.addLayout(layout_pie)

        layout_principal.addWidget(self.tarjeta_fondo)

    def _crear_boton_pildora(self, texto: str, accion) -> QPushButton:
        btn = QPushButton(texto)
        btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.05);
                color: #cbd5e1;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 12px;
                padding: 5px 12px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: rgba(124, 77, 255, 0.25);
                border-color: rgba(124, 77, 255, 0.5);
                color: #ffffff;
            }
        """)
        btn.clicked.connect(accion)
        return btn

    def _centrar_en_pantalla(self) -> None:
        """Ubica la ventana centrada horizontalmente y en el tercio superior."""
        pantalla = QApplication.primaryScreen().geometry()
        x = (pantalla.width() - self.width()) // 2
        y = int(pantalla.height() * 0.16)
        self.move(x, y)

    def alternar_visibilidad(self) -> None:
        """
        Muestra u oculta la ventana según su estado actual.
        Incluye protección de 'debounce' (350 ms) para evitar pestañeo por disparo doble.
        """
        import time
        ahora_ms = int(time.time() * 1000)
        if ahora_ms - getattr(self, "_ultimo_toggle_ms", 0) < 350:
            return
        self._ultimo_toggle_ms = ahora_ms

        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.setWindowState(self.windowState() & ~Qt.WindowState.WindowMinimized | Qt.WindowState.WindowActive)
            self.raise_()
            self.activateWindow()
            self.input_consulta.setFocus()
            self.input_consulta.selectAll()

    # -------------------------------------------------------------------------
    # Soporte para arrastrar la ventana sin marco
    # -------------------------------------------------------------------------
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._arrastrando = True
            self._pos_arrastre = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if getattr(self, "_arrastrando", False) and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._pos_arrastre)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._arrastrando = False
        event.accept()

    # -------------------------------------------------------------------------
    # Gestión Asíncrona y Animación de Estado
    # -------------------------------------------------------------------------
    def _iniciar_pensamiento(self, prefijo: str = "Pensando con Gemini") -> None:
        self._texto_pensando_base = prefijo
        self._conteo_puntos = 0
        self.lbl_estado.setText(f"{prefijo}...")
        self.btn_enviar.setEnabled(False)
        self.input_consulta.setEnabled(False)
        self.btn_pildora_briefing.setEnabled(False)
        self.btn_pildora_agenda.setEnabled(False)
        self.btn_pildora_tareas.setEnabled(False)
        self.btn_pildora_captura.setEnabled(False)

        if not hasattr(self, "_timer_animacion"):
            self._timer_animacion = QTimer(self)
            self._timer_animacion.setInterval(350)
            self._timer_animacion.timeout.connect(self._actualizar_animacion_pensando)
        self._timer_animacion.start()

    def _actualizar_animacion_pensando(self) -> None:
        self._conteo_puntos = (self._conteo_puntos + 1) % 4
        puntos = "." * self._conteo_puntos
        self.lbl_estado.setText(f"{self._texto_pensando_base}{puntos}")

    def _detener_pensamiento(self, estado_final: str = "Listo") -> None:
        if hasattr(self, "_timer_animacion") and self._timer_animacion.isActive():
            self._timer_animacion.stop()
        self.lbl_estado.setText(estado_final)
        self.btn_enviar.setEnabled(True)
        self.input_consulta.setEnabled(True)
        self.btn_pildora_briefing.setEnabled(True)
        self.btn_pildora_agenda.setEnabled(True)
        self.btn_pildora_tareas.setEnabled(True)
        self.btn_pildora_captura.setEnabled(True)
        self.input_consulta.setFocus()

    def _al_recibir_resultado(self, resultado: dict) -> None:
        self._detener_pensamiento("Listo")
        respuesta = resultado.get("respuesta", "")
        html_respuesta = self._convertir_markdown_a_html(respuesta)
        if resultado.get("es_briefing"):
            self.visor_respuesta.append(f"<div style='color: #e2e8f0; margin-top: 6px;'>{html_respuesta}</div>")
        else:
            self.visor_respuesta.append(f"<div style='color: #e2e8f0; margin-top: 6px;'><b>✦ Asistente:</b><br>{html_respuesta}</div>")

        barra = self.visor_respuesta.verticalScrollBar()
        barra.setValue(barra.maximum())

    def _al_recibir_error(self, error_str: str) -> None:
        self._detener_pensamiento("Error en la consulta")
        self.visor_respuesta.append(
            f"<div style='color: #ef4444; margin-top: 6px;'><b>❌ Error:</b> No se pudo completar la consulta ({error_str})</div>"
        )
        barra = self.visor_respuesta.verticalScrollBar()
        barra.setValue(barra.maximum())

    # -------------------------------------------------------------------------
    # Acciones y Procesamiento
    # -------------------------------------------------------------------------
    def _enviar_consulta(self) -> None:
        if self._worker is not None and self._worker.isRunning():
            return

        texto = self.input_consulta.text().strip()
        if not texto:
            return

        self.input_consulta.clear()
        self.visor_respuesta.append(f"<div style='color: #7c4dff; margin-top: 10px;'><b>Tú:</b> {texto}</div>")

        self._iniciar_pensamiento("Pensando con Gemini")

        self._worker = WorkerConsulta(self.cerebro, texto=texto, es_briefing=False)
        self._worker.resultado_listo.connect(self._al_recibir_resultado)
        self._worker.error_ocurrido.connect(self._al_recibir_error)
        self._worker.start()

    def _convertir_markdown_a_html(self, texto: str) -> str:
        """Conversión simple y elegante de Markdown básico a HTML."""
        lineas = texto.splitlines()
        html_lineas = []
        for linea in lineas:
            linea_str = linea.strip()
            if linea_str.startswith("# "):
                html_lineas.append(f"<h3 style='color: #a78bfa; margin: 4px 0;'>{linea_str[2:]}</h3>")
            elif linea_str.startswith("## "):
                html_lineas.append(f"<h4 style='color: #c4b5fd; margin: 4px 0;'>{linea_str[3:]}</h4>")
            elif linea_str.startswith("- [ ] "):
                html_lineas.append(f"<div style='margin-left: 10px;'>⬜ {linea_str[6:]}</div>")
            elif linea_str.startswith("- [x] ") or linea_str.startswith("- [X] "):
                html_lineas.append(f"<div style='margin-left: 10px; color: #10b981;'>✅ <strike>{linea_str[6:]}</strike></div>")
            elif linea_str.startswith("- ") or linea_str.startswith("* "):
                html_lineas.append(f"<div style='margin-left: 10px;'>• {linea_str[2:]}</div>")
            else:
                html_lineas.append(f"<p style='margin: 4px 0;'>{linea}</p>")
        return "".join(html_lineas)

    def _limpiar_pantalla(self) -> None:
        self.visor_respuesta.clear()
        self.lbl_estado.setText("Historial limpiado")

    def _accion_briefing(self) -> None:
        if self._worker is not None and self._worker.isRunning():
            return

        self.visor_respuesta.append("<div style='color: #38bdf8; margin-top: 10px;'><b>☀️ Generando tu Briefing de Hoy...</b></div>")
        self._iniciar_pensamiento("Generando Briefing")

        self._worker = WorkerConsulta(self.cerebro, texto="", es_briefing=True)
        self._worker.resultado_listo.connect(self._al_recibir_resultado)
        self._worker.error_ocurrido.connect(self._al_recibir_error)
        self._worker.start()

    def _accion_agenda(self) -> None:
        self.input_consulta.setText("¿Qué tengo en mi agenda de Google Calendar para hoy y los próximos días?")
        self._enviar_consulta()

    def _accion_tareas(self) -> None:
        self.input_consulta.setText("¿Cuáles son mis tareas pendientes en Obsidian para hoy?")
        self._enviar_consulta()

    def _accion_captura(self) -> None:
        self.input_consulta.setText("Guarda este apunte rápido en Obsidian: ")
        self.input_consulta.setFocus()


class AplicacionAsistente:
    """Orquesta la aplicación PySide6, la ventana Spotlight, el System Tray y el Hotkey."""

    def __init__(self):
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        # 1. Componentes del sistema
        self.cerebro = CerebroGemini()
        self.ventana = VentanaSpotlight(self.cerebro)
        self.motor_proactivo = MotorProactivo(self.cerebro, intervalo_chequeo_segundos=60)

        # 2. Configurar System Tray
        self._configurar_system_tray()

        # 3. Registrar Hotkey global (Ctrl + Espacio) en Windows
        self._registrar_hotkey_windows()

        # 4. Conectar señales del motor proactivo asíncrono
        self.motor_proactivo.notificacion_solicitada.connect(self._mostrar_notificacion_tray)
        self.motor_proactivo.briefing_listo.connect(self._al_recibir_briefing)
        self.motor_proactivo.consolidacion_listo.connect(self._al_recibir_consolidacion)
        self.motor_proactivo.tarea_actualizada.connect(self._al_actualizar_tarea)

        # Iniciar motor proactivo en su propio hilo QThread (sin congelar Qt)
        self.motor_proactivo.iniciar()

    def _configurar_system_tray(self) -> None:
        icono = crear_icono_asistente()
        self.tray = QSystemTrayIcon(icono, self.app)
        self.tray.setToolTip("Antigravity Assistant - Segundo Cerebro (Ctrl + Espacio)")

        # Menú contextual
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu {
                background-color: #1a1a24;
                color: #ffffff;
                border: 1px solid #33334d;
                border-radius: 8px;
                padding: 6px;
            }
            QMenu::item {
                padding: 6px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #7c4dff;
            }
        """)

        accion_toggle = menu.addAction("Mostrar / Ocultar (Ctrl + Espacio)")
        accion_toggle.triggered.connect(self.ventana.alternar_visibilidad)

        accion_briefing = menu.addAction("☀️ Briefing Matutino")
        accion_briefing.triggered.connect(self._disparar_briefing_desde_menu)

        accion_tareas = menu.addAction("✅ Tareas de Obsidian")
        accion_tareas.triggered.connect(self._disparar_tareas_desde_menu)

        accion_consolidacion = menu.addAction("🌙 Consolidación Nocturna")
        accion_consolidacion.triggered.connect(self._disparar_consolidacion_desde_menu)

        menu.addSeparator()

        accion_salir = menu.addAction("Salir")
        accion_salir.triggered.connect(self.salir)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._al_activar_tray)
        self.tray.show()

    def _al_activar_tray(self, motivo) -> None:
        if motivo in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self.ventana.alternar_visibilidad()

    def _mostrar_notificacion_tray(self, titulo: str, mensaje: str) -> None:
        self.tray.showMessage(titulo, mensaje, QSystemTrayIcon.MessageIcon.Information, 7000)

    def _al_recibir_briefing(self, texto_briefing: str) -> None:
        # Pre-cargar el briefing en la ventana si el usuario la abre
        html = self.ventana._convertir_markdown_a_html(texto_briefing)
        self.ventana.visor_respuesta.setHtml(
            f"<div style='color: #a78bfa; font-size: 15px;'><b>☀️ Briefing Matutino</b></div><br>{html}"
        )

    def _al_recibir_consolidacion(self, texto_consolidacion: str) -> None:
        html = self.ventana._convertir_markdown_a_html(texto_consolidacion)
        self.ventana.visor_respuesta.append(
            f"<div style='color: #38bdf8; font-size: 14px;'><b>🌙 Consolidación de Jornada Guardada</b></div><br>{html}"
        )

    def _al_actualizar_tarea(self, tarea_id: int, estado: str, detalle: str) -> None:
        self.ventana.lbl_estado.setText(f"Tarea #{tarea_id}: {estado}")

    def _disparar_briefing_desde_menu(self) -> None:
        self.ventana.show()
        self.ventana.raise_()
        self.ventana.activateWindow()
        self.ventana._accion_briefing()

    def _disparar_tareas_desde_menu(self) -> None:
        self.ventana.show()
        self.ventana.raise_()
        self.ventana.activateWindow()
        self.ventana._accion_tareas()

    def _disparar_consolidacion_desde_menu(self) -> None:
        self.ventana.lbl_estado.setText("Consolidando jornada...")
        self.motor_proactivo.solicitar_consolidacion_inmediata()

    def _registrar_hotkey_windows(self) -> None:
        """
        Registra el atajo Ctrl + Espacio con estrategia dual resistente:
        1. Hook global de bajo nivel con 'keyboard' (no se pierde al cambiar de ventana o foco).
        2. Fallback / redundancia con RegisterHotKey de Windows API.
        """
        # Canal 1: Hook global persistente mediante el paquete 'keyboard'
        try:
            import keyboard
            self.bridge_hotkey = BridgeHotkey()
            self.bridge_hotkey.toggle_solicitado.connect(self.ventana.alternar_visibilidad)
            keyboard.add_hotkey("ctrl+space", self.bridge_hotkey.toggle_solicitado.emit)
            self._keyboard_registrado = True
            print("Atajo global 'Ctrl + Espacio' registrado con gancho persistente (keyboard).")
        except Exception as e_kb:
            self._keyboard_registrado = False
            print(f"Nota: Gancho de teclado primario no disponible ({e_kb}). Usando API nativa.")

        # Canal 2: RegisterHotKey nativo de Windows (como capa complementaria)
        try:
            user32 = ctypes.windll.user32
            exito = user32.RegisterHotKey(None, HOTKEY_ID_GLOBAL, MOD_CONTROL, VK_SPACE)
            if exito:
                self.filtro_hotkey = FiltroHotkeyWindows(self.ventana.alternar_visibilidad)
                self.app.installNativeEventFilter(self.filtro_hotkey)
                self._win_hotkey_registrado = True
                print("Atajo global 'Ctrl + Espacio' registrado con éxito en Windows API.")
            else:
                self._win_hotkey_registrado = False
        except Exception as exc:
            self._win_hotkey_registrado = False
            print(f"Error registrando hotkey nativo: {exc}")

    def salir(self) -> None:
        """Desregistra los hotkeys y cierra la aplicación limpiamente."""
        if getattr(self, "_keyboard_registrado", False):
            try:
                import keyboard
                keyboard.remove_hotkey("ctrl+space")
            except Exception:
                pass
        if getattr(self, "_win_hotkey_registrado", False):
            try:
                ctypes.windll.user32.UnregisterHotKey(None, HOTKEY_ID_GLOBAL)
            except Exception:
                pass
        self.motor_proactivo.detener()
        self.app.quit()

    def ejecutar(self) -> int:
        """Inicia el bucle de la aplicación mostrando la ventana inicialmente."""
        self.ventana.show()
        return self.app.exec()
