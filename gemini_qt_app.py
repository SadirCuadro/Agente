import os
import sys

from dotenv import load_dotenv
from google import genai
from PySide6.QtCore import Qt
from PySide6.QtGui import QPalette, QColor
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QTextEdit,
    QLineEdit,
    QPushButton,
    QMessageBox,
    QHBoxLayout,
    QLabel,
    QFileDialog,
)


def explain_gemini_error(exc, model_id=None):
    message = str(exc).lower()

    if "api key" in message or "authentication" in message or "forbidden" in message or "401" in message or "403" in message:
        return "La clave de Gemini es inválida o no tiene permisos. Revisa GOOGLE_API_KEY en .env."
    if "503" in message or "unavailable" in message or "high demand" in message or "overload" in message or "spikes in demand" in message:
        return "Gemini está experimentando alta demanda o sobrecarga temporal (error 503). Por favor, intenta de nuevo en unos momentos."
    if "quota" in message or "rate limit" in message or "429" in message or "resource_exhausted" in message:
        return "Gemini respondió que se agotó la cuota o hay demasiadas peticiones (429). Espera unos minutos e inténtalo de nuevo."
    if "network" in message or "connection" in message or "timed out" in message or "timeout" in message:
        return "No hubo conexión con Google o la petición tardó demasiado. Revisa tu internet y prueba otra vez."
    if "not found" in message or "not_found" in message or "404" in message or "no longer available" in message or "does not exist" in message:
        mod_str = f" '{model_id}'" if model_id else ""
        return f"El modelo{mod_str} no es válido o ya no está disponible en la API. Revisa GOOGLE_MODEL_ID en .env (recomendado: gemini-3.6-flash)."
    return f"Error con Gemini: {exc}"


def load_gemini_config():
    load_dotenv(override=True)
    api_key = os.getenv("GOOGLE_API_KEY")
    model_id = os.getenv("GOOGLE_MODEL_ID", "gemini-3.6-flash").strip()

    if not api_key:
        raise RuntimeError(
            "Falta GOOGLE_API_KEY en el archivo .env. Copia tu clave desde .env.example y vuelve a intentar."
        )

    return api_key, model_id


def create_chat_client(api_key, model_id):
    try:
        client = genai.Client(api_key=api_key)
        chat = client.chats.create(model=model_id)
        return client, chat
    except Exception as exc:
        raise RuntimeError(f"No se pudo inicializar el cliente de Gemini ({model_id}): {exc}") from exc


class GeminiChatWindow(QWidget):
    def __init__(self, client, chat, model_id=""):
        super().__init__()
        self.client = client
        self.chat = chat
        self.model_id = model_id
        self.setWindowTitle(f"Gemini Agent ({self.model_id})" if self.model_id else "Gemini Agent")
        self.resize(820, 620)
        self.setWindowFlags(Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.selected_file = None

        self._build_ui()
        self._apply_dark_theme()
        self.center_on_screen()

    def center_on_screen(self):
        screen = QApplication.primaryScreen().availableGeometry()
        size = self.geometry()
        self.move(
            (screen.width() - size.width()) // 2,
            (screen.height() - size.height()) // 2,
        )

    def _build_ui(self):
        self.frame = QWidget(self)
        self.frame.setObjectName("windowFrame")
        self.frame.setStyleSheet(
            "QWidget#windowFrame {"
            "background: #111827;"
            "border: 1px solid #2d3748;"
            "border-radius: 18px;"
            "}"
        )

        header = QWidget(self.frame)
        header.setFixedHeight(54)
        header.setStyleSheet("background: transparent;")

        self.title_label = QLabel(f"Gemini Agent  •  {self.model_id}" if self.model_id else "Gemini Agent", header)
        self.title_label.setStyleSheet(
            "color: #edf2ff; font-size: 16px; font-weight: 700; margin-left: 18px;"
        )

        self.min_button = QPushButton("_", header)
        self.min_button.setFixedSize(28, 28)
        self.min_button.setStyleSheet(
            "QPushButton { background: #1f2a3d; border: 1px solid #364765; border-radius: 8px; color: #e5eefc; font-weight: 700; }"
            "QPushButton:hover { background: #2b3a52; }"
        )

        self.close_button = QPushButton("✕", header)
        self.close_button.setFixedSize(28, 28)
        self.close_button.setStyleSheet(
            "QPushButton { background: #b7455c; border: 1px solid #d77784; border-radius: 8px; color: white; font-weight: 700; }"
            "QPushButton:hover { background: #d55c6d; }"
        )

        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 12, 0)
        header_layout.setSpacing(8)
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.min_button)
        header_layout.addWidget(self.close_button)

        self.output = QTextEdit(self.frame)
        self.output.setReadOnly(True)
        self.output.setPlaceholderText("Conversación con Gemini...")
        self.output.setStyleSheet(
            "background: #1b2233; color: #edf4ff; border: 1px solid #2d3b53; border-radius: 12px; padding: 12px;"
            "font-size: 14px;"
        )

        self.input = QLineEdit(self.frame)
        self.input.setPlaceholderText("Escribe aquí tu mensaje...")
        self.input.setStyleSheet(
            "background: #1b2233; color: #edf4ff; border: 1px solid #2d3b53; border-radius: 12px; padding: 12px;"
            "font-size: 14px;"
        )

        self.attach_button = QPushButton("Adjuntar")
        self.attach_button.setStyleSheet(
            "QPushButton { background: #24324a; border: 1px solid #3d5478; border-radius: 12px; color: #e5eefc; font-weight: 700; padding: 12px 16px; }"
            "QPushButton:hover { background: #304461; }"
        )

        self.test_button = QPushButton("Probar conexión")
        self.test_button.setStyleSheet(
            "QPushButton { background: #1f4d3f; border: 1px solid #3aa57f; border-radius: 12px; color: #e9fff6; font-weight: 700; padding: 12px 16px; }"
            "QPushButton:hover { background: #235f4a; }"
        )

        self.file_label = QLabel("Ningún archivo seleccionado")
        self.file_label.setStyleSheet("color: #91a4c2; padding-left: 4px;")

        self.send_button = QPushButton("Enviar")
        self.send_button.setStyleSheet(
            "QPushButton { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f8cff, stop:1 #7d5cff); border: none; border-radius: 12px; color: white; font-weight: 700; padding: 12px 18px; }"
            "QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #5d96ff, stop:1 #8a6cf8); }"
        )

        content = QVBoxLayout(self.frame)
        content.setContentsMargins(14, 8, 14, 14)
        content.setSpacing(12)
        content.addWidget(header)
        content.addWidget(self.output)

        file_row = QHBoxLayout()
        file_row.setSpacing(8)
        file_row.addWidget(self.attach_button)
        file_row.addWidget(self.test_button)
        file_row.addWidget(self.file_label, 1)
        content.addLayout(file_row)

        input_row = QHBoxLayout()
        input_row.setSpacing(8)
        input_row.addWidget(self.input, 1)
        input_row.addWidget(self.send_button)
        content.addLayout(input_row)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.addWidget(self.frame)

        self.min_button.clicked.connect(self.showMinimized)
        self.close_button.clicked.connect(self.close)
        self.attach_button.clicked.connect(self.select_file)
        self.test_button.clicked.connect(self.test_connection)
        self.input.returnPressed.connect(self.send_message)
        self.send_button.clicked.connect(self.send_message)

        self.output.append(f"Chat con Gemini listo (Modelo: {self.model_id}). Pulsa 'Probar conexión' para verificar la API.")

    def _apply_dark_theme(self):
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor("#111827"))
        palette.setColor(QPalette.WindowText, QColor("#edf2ff"))
        palette.setColor(QPalette.Base, QColor("#111827"))
        palette.setColor(QPalette.AlternateBase, QColor("#1b2233"))
        palette.setColor(QPalette.Text, QColor("#edf2ff"))
        palette.setColor(QPalette.Button, QColor("#1f2a3d"))
        palette.setColor(QPalette.ButtonText, QColor("#edf2ff"))
        QApplication.setPalette(palette)

    def send_message(self):
        text = self.input.text().strip()
        if not text and not self.selected_file:
            return

        if self.selected_file:
            self.output.append(f"Tú: [Archivo] {self.selected_file}")
        if text:
            self.output.append(f"Tú: {text}")
        self.input.clear()

        if text.lower() in {"salir", "exit", "quit"}:
            self.output.append("Gemini: Hasta luego.")
            self.close()
            return

        try:
            contents = []
            if self.selected_file:
                uploaded_file = self.client.files.upload(file=self.selected_file)
                contents.append(uploaded_file)
            if text:
                contents.append(text)

            response = self.chat.send_message(contents)
            self.output.append(f"Gemini: {response.text}")
            self.selected_file = None
            self.file_label.setText("Ningún archivo seleccionado")
        except Exception as exc:
            diagnosis = explain_gemini_error(exc, self.model_id)
            self.output.append(f"Error: {diagnosis}")
            QMessageBox.critical(self, "Error de conexión", f"{diagnosis}\n\nDetalle técnico:\n{exc}")

    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar archivo",
            "",
            "Todos los archivos (*);;Imágenes (*.png *.jpg *.jpeg *.webp);;PDF (*.pdf);;Texto (*.txt *.md *.csv)",
        )
        if file_path:
            self.selected_file = file_path
            self.file_label.setText(os.path.basename(file_path))

    def test_connection(self):
        self.output.append("Gemini: comprobando configuración y conexión...")
        try:
            api_key, model_id = load_gemini_config()
            self.model_id = model_id
            self.title_label.setText(f"Gemini Agent  •  {self.model_id}")
            self.setWindowTitle(f"Gemini Agent ({self.model_id})")
            self.client, self.chat = create_chat_client(api_key, model_id)
        except Exception as exc:
            diagnosis = explain_gemini_error(exc, getattr(self, "model_id", None))
            self.output.append(f"Error de configuración: {diagnosis}")
            QMessageBox.critical(self, "Prueba de conexión", f"{diagnosis}\n\nDetalle técnico:\n{exc}")
            return

        self.output.append(f"Gemini: enviando prueba con el modelo '{self.model_id}'...")
        try:
            response = self.chat.send_message("Responde solo con OK")
            message = getattr(response, "text", "").strip()
            self.output.append(f"Gemini: conexión correcta ({message or 'OK'}).")
            QMessageBox.information(
                self,
                "Prueba de conexión",
                f"¡Conexión exitosa con la API de Gemini!\n\nModelo activo: {self.model_id}\nRespuesta recibida: {message or 'OK'}"
            )
        except Exception as exc:
            diagnosis = explain_gemini_error(exc, self.model_id)
            self.output.append(f"Error: {diagnosis}")
            QMessageBox.critical(self, "Prueba de conexión", f"{diagnosis}\n\nDetalle técnico:\n{exc}")


if __name__ == "__main__":
    app = QApplication([])
    try:
        api_key, model_id = load_gemini_config()
        client, chat = create_chat_client(api_key, model_id)
    except Exception as exc:
        QMessageBox.critical(None, "Error de configuración", str(exc))
        sys.exit(1)

    app.setStyle("Fusion")
    window = GeminiChatWindow(client, chat, model_id)
    window.show()
    app.exec()
