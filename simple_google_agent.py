import os
import smtplib
import tempfile
import uuid
from email.message import EmailMessage

import streamlit as st
from dotenv import load_dotenv
from google import genai


def explain_gemini_error(exc):
    message = str(exc).lower()

    if "api key" in message or "authentication" in message or "forbidden" in message:
        return "La clave de Gemini es inválida o no tiene permisos. Revisa GOOGLE_API_KEY en .env."
    if "quota" in message or "rate limit" in message or "429" in message:
        return "Gemini respondió que se agotó la cuota o hay demasiadas peticiones. Espera unos minutos e inténtalo de nuevo."
    if "network" in message or "connection" in message or "timed out" in message:
        return "No hubo conexión con Google o la petición tardó demasiado. Revisa tu internet y prueba otra vez."
    if "model" in message:
        return "El modelo configurado no es válido o no está disponible. Revisa GOOGLE_MODEL_ID en .env."
    return f"Ocurrió un error con Gemini: {exc}"


def get_gemini_config():
    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")
    model_id = os.getenv("GOOGLE_MODEL_ID", "gemini-3.6-flash").strip()

    if not api_key:
        raise ValueError("Falta la GOOGLE_API_KEY en el archivo .env. Copia la clave desde .env.example.")

    return api_key, model_id


def create_chat_session(api_key, model_id):
    try:
        client = genai.Client(api_key=api_key)
        chat = client.chats.create(model=model_id)
        return client, chat
    except Exception as exc:  # pragma: no cover - depende de la API externa
        raise RuntimeError(f"No se pudo inicializar Gemini: {exc}") from exc


def send_email(recipient, subject, body, smtp_host, smtp_port, smtp_user, smtp_password, sender):
    smtp_host = smtp_host or os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(smtp_port or os.getenv("SMTP_PORT", "587"))
    smtp_user = smtp_user or os.getenv("SMTP_USER")
    smtp_password = smtp_password or os.getenv("SMTP_PASSWORD")
    sender = sender or os.getenv("EMAIL_FROM") or smtp_user

    if not smtp_user or not smtp_password:
        raise ValueError(
            "Configura el correo remitente y su contraseña de aplicación."
        )

    message = EmailMessage()
    message["From"] = sender
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)

    with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(message)


# Configuración de la página del navegador
st.set_page_config(page_title="AvisoIA", page_icon="🤖", layout="centered")
st.title("AvisoIA")

try:
    api_key, model_id = get_gemini_config()

    if (
        "client" not in st.session_state
        or "chat" not in st.session_state
        or st.session_state.get("model_id") != model_id
    ):
        st.session_state.client, st.session_state.chat = create_chat_session(api_key, model_id)
        st.session_state.model_id = model_id

    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "search_history" not in st.session_state:
        st.session_state.search_history = []
    if "comparison_result" not in st.session_state:
        st.session_state.comparison_result = ""
except Exception as exc:
    st.error(str(exc))
    st.stop()

# Subida de archivos PDF en la barra lateral
with st.sidebar:
    st.header("Documentos")
    uploaded_file = st.file_uploader("Sube un archivo PDF", type=["pdf"])

chat_tab, comparison_tab = st.tabs(["Chat", "Comparar exámenes"])

with chat_tab:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Escribe tu mensaje..."):
        if prompt not in st.session_state.search_history:
            st.session_state.search_history.insert(0, prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Pensando..."):
                try:
                    if uploaded_file is not None:
                        temp_dir = os.path.join(os.getcwd(), "tmp_uploads")
                        os.makedirs(temp_dir, exist_ok=True)
                        temp_path = os.path.join(temp_dir, f"{uuid.uuid4().hex}_{uploaded_file.name}")

                        with open(temp_path, "wb") as file_handle:
                            file_handle.write(uploaded_file.getbuffer())

                        try:
                            pdf_file = st.session_state.client.files.upload(file=temp_path)
                            response = st.session_state.chat.send_message([pdf_file, prompt])
                        finally:
                            try:
                                os.remove(temp_path)
                            except FileNotFoundError:
                                pass
                    else:
                        response = st.session_state.chat.send_message(prompt)

                    st.markdown(response.text)
                    st.session_state.messages.append({"role": "assistant", "content": response.text})
                except Exception as exc:
                    st.error(explain_gemini_error(exc))

with comparison_tab:
    st.subheader("Revisión de respuestas")
    st.caption("Los PDF se enviarán al modelo Gemini configurado. Evita incluir datos personales innecesarios.")
    with st.form("exam_comparison_form"):
        exam_files = st.file_uploader(
            "Exámenes de estudiantes (PDF)",
            type=["pdf"],
            accept_multiple_files=True,
        )
        answer_key = st.text_area(
            "Clave oficial de respuestas (opcional)",
            placeholder="Ejemplo: 1) B, 2) 14, 3) La fotosíntesis...",
        )
        compare_button = st.form_submit_button("Comparar exámenes", icon=":material/compare_arrows:")

    if compare_button:
        if len(exam_files) < 2:
            st.warning("Sube al menos dos exámenes PDF para compararlos.")
        else:
            uploaded_files = []
            result = ""
            try:
                with st.spinner("Leyendo y comparando los exámenes..."):
                    with tempfile.TemporaryDirectory() as temp_dir:
                        contents = []
                        for index, exam_file in enumerate(exam_files, start=1):
                            temp_path = os.path.join(temp_dir, f"exam_{index}.pdf")
                            with open(temp_path, "wb") as file_handle:
                                file_handle.write(exam_file.getbuffer())
                            remote_file = st.session_state.client.files.upload(file=temp_path)
                            uploaded_files.append(remote_file)
                            contents.extend([f"Documento {index}: {exam_file.name}", remote_file])

                        key_instructions = (
                            f"Clave oficial de respuestas:\n{answer_key.strip()}\n"
                            "Evalúa cada respuesta contra esta clave. Señala acierto, error o no evaluable; "
                            "no inventes respuestas ilegibles."
                            if answer_key.strip()
                            else "No se proporcionó clave oficial. Compara las respuestas por pregunta y "
                            "señala coincidencias y diferencias, pero no clasifiques a nadie como correcto "
                            "o equivocado ni infieras la respuesta correcta."
                        )
                        contents.append(
                            "Compara los exámenes PDF adjuntos; cada documento corresponde a un estudiante. "
                            "Identifica al estudiante por el nombre escrito en el examen; si no aparece, "
                            "usa el nombre del archivo y aclara que es una referencia. Para cada estudiante, "
                            "resume las respuestas por pregunta y los puntos que requieren revisión. "
                            "Después incluye un resumen comparativo por pregunta y un balance por estudiante. "
                            "No supongas que preguntas o respuestas ilegibles están en blanco. "
                            f"{key_instructions}"
                        )
                        response = st.session_state.client.models.generate_content(
                            model=model_id,
                            contents=contents,
                        )
                        result = response.text or "Gemini no devolvió un resultado legible."
            except Exception as exc:
                st.error(explain_gemini_error(exc))
            finally:
                for remote_file in uploaded_files:
                    try:
                        st.session_state.client.files.delete(name=remote_file.name)
                    except Exception:
                        pass

            if result:
                st.session_state.comparison_result = result

    if st.session_state.comparison_result:
        st.markdown(st.session_state.comparison_result)

with st.sidebar:
    st.header("Historial de búsqueda")
    if st.session_state.search_history:
        if st.button("Borrar historial", icon=":material/delete:"):
            st.session_state.search_history = []
            st.rerun()
        for index, query in enumerate(st.session_state.search_history):
            st.caption(f"{index + 1}. {query}")
    else:
        st.caption("Todavía no hay búsquedas.")

    st.header("Enviar correo")
    with st.expander("Configuración del correo"):
        smtp_user = st.text_input(
            "Correo remitente",
            value=os.getenv("SMTP_USER", ""),
            placeholder="tu_correo@gmail.com",
        )
        smtp_password = st.text_input(
            "Contraseña de aplicación",
            value=os.getenv("SMTP_PASSWORD", ""),
            type="password",
        )
        smtp_host = st.text_input(
            "Servidor SMTP",
            value=os.getenv("SMTP_HOST", "smtp.gmail.com"),
        )
        smtp_port = st.number_input(
            "Puerto SMTP",
            min_value=1,
            max_value=65535,
            value=int(os.getenv("SMTP_PORT", "587")),
        )
        sender = st.text_input(
            "Dirección que aparecerá como remitente",
            value=os.getenv("EMAIL_FROM", ""),
            placeholder="Opcional: usa el correo remitente si queda vacío",
        )

    with st.form("email_form", clear_on_submit=True):
        recipient = st.text_input("Correo destinatario", placeholder="persona@ejemplo.com")
        subject = st.text_input("Asunto", value="Mensaje desde AvisoIA")
        body = st.text_area("Mensaje", placeholder="Escribe el contenido del correo...")
        send_button = st.form_submit_button("Enviar correo", icon=":material/send:")

    if send_button:
        if not recipient.strip() or not subject.strip() or not body.strip():
            st.warning("Completa destinatario, asunto y mensaje.")
        else:
            try:
                send_email(
                    recipient.strip(),
                    subject.strip(),
                    body.strip(),
                    smtp_host,
                    smtp_port,
                    smtp_user.strip(),
                    smtp_password,
                    sender.strip(),
                )
                st.success("Correo enviado correctamente.")
            except Exception as exc:
                st.error(f"No se pudo enviar el correo: {exc}")