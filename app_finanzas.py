"""
💳 "Foto y Control": Gestor Inteligente de Gastos y Facturas.

Plataforma Web SaaS con Streamlit:
- Dashboard de métricas financieras (KPIs, progreso presupuestario y gráficos).
- Escáner multimodal de recibos y facturas (Foto a JSON con Gemini).
- Registro tabular con filtros, edición y exportación de transacciones.
- Coach Financiero y Asistente Consultivo con IA.
- Módulo de envío de reportes ejecutivos por correo vía SMTP.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
from PIL import Image

from finanzas.asistente_gemini import AsistenteFinanciero
from finanzas.extractor_recibos import ExtractorRecibos
from finanzas.gestor_presupuesto import (
    CATEGORIAS_PREDETERMINADAS,
    Gasto,
    GestorPresupuesto,
    PresupuestoConfig,
)
from finanzas.gestor_reporte_correo import GestorReporteCorreo

# -----------------------------------------------------------------------------
# CONFIGURACIÓN DE PÁGINA
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Foto y Control | Finanzas Inteligentes",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------------------------------------------------------
# INICIALIZACIÓN DE SERVICIOS Y ESTADO
# -----------------------------------------------------------------------------
@st.cache_resource
def obtener_gestor_presupuesto() -> GestorPresupuesto:
    return GestorPresupuesto()

@st.cache_resource
def obtener_extractor() -> ExtractorRecibos:
    return ExtractorRecibos()

@st.cache_resource
def obtener_asistente() -> AsistenteFinanciero:
    return AsistenteFinanciero()

@st.cache_resource
def obtener_gestor_correo() -> GestorReporteCorreo:
    return GestorReporteCorreo()

gestor = obtener_gestor_presupuesto()
extractor = obtener_extractor()
asistente = obtener_asistente()
gestor_correo = obtener_gestor_correo()

# Inicializar historial de chat si no existe
if "mensajes_coach" not in st.session_state:
    st.session_state.mensajes_coach = [
        {
            "role": "assistant",
            "content": (
                "¡Hola! 👋 Soy tu **Coach Financiero** en *Foto y Control*. "
                "Tengo acceso en tiempo real al balance de tus gastos y presupuesto. "
                "Pregúntame sobre cómo optimizar tus finanzas, identificar gastos hormiga "
                "o consejos prácticos para alcanzar tu meta de ahorro."
            ),
        }
    ]

# -----------------------------------------------------------------------------
# BARRA LATERAL (SIDEBAR) - RESUMEN RÁPIDO & CONFIGURACIÓN
# -----------------------------------------------------------------------------
with st.sidebar:
    st.title("💳 Foto y Control")
    st.caption("Gestor Inteligente de Gastos y Facturas")
    st.divider()

    config_actual = gestor.cargar_config()

    with st.expander("⚙️ Configuración de Presupuesto", expanded=False):
        nuevo_presupuesto = st.number_input(
            "Presupuesto Mensual Global (COP):",
            min_value=100000.0,
            max_value=50000000.0,
            value=float(config_actual.presupuesto_total_mensual),
            step=100000.0,
            format="%.0f",
        )
        if st.button("Guardar Presupuesto", icon=":material/save:"):
            config_actual.presupuesto_total_mensual = nuevo_presupuesto
            gestor.guardar_config(config_actual)
            st.success("¡Presupuesto actualizado!")
            st.rerun()

    st.markdown("### 🔔 Estado Rápido")
    metricas_sidebar = gestor.calcular_metricas()
    total_g = metricas_sidebar["total_gastado"]
    pres_g = metricas_sidebar["presupuesto_total"]
    pct_g = metricas_sidebar["porcentaje_consumido"]

    st.progress(min(pct_g / 100.0, 1.0))
    st.caption(f"Consumido: **{pct_g:.1f}%** de ${pres_g:,.0f} COP")

    if pct_g >= 90.0:
        st.error("⚠️ ¡Alerta Crítica! Has superado el 90% de tu presupuesto.")
    elif pct_g >= 70.0:
        st.warning("⚡ Advertencia: Has superado el 70% de tu presupuesto.")
    else:
        st.success("✅ Tu presupuesto se mantiene en zona saludable.")

    st.divider()
    st.caption("Plataforma SaaS Multimodal con Gemini 2.5/3.6")

# -----------------------------------------------------------------------------
# PESTAÑAS PRINCIPALES DE LA PLATAFORMA
# -----------------------------------------------------------------------------
tab_dashboard, tab_scanner, tab_transacciones, tab_coach, tab_correo = st.tabs([
    "📊 Dashboard Ejecutivo",
    "📸 Escáner de Recibos (IA)",
    "📋 Registro de Gastos",
    "🤖 Coach Financiero Gemini",
    "📧 Enviar Reporte por Correo",
])

# =============================================================================
# PESTAÑA 1: DASHBOARD EJECUTIVO
# =============================================================================
with tab_dashboard:
    st.header("📊 Dashboard de Control Financiero", divider="blue")

    # Filtros superiores
    with st.container(border=True):
        col_filtro1, col_filtro2, col_filtro3 = st.columns([1, 1, 2])
        with col_filtro1:
            meses_nombres = {
                1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
                7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
            }
            mes_actual = datetime.now().month
            mes_sel = st.selectbox(
                "Mes a Visualizar:",
                options=list(meses_nombres.keys()),
                format_func=lambda x: meses_nombres[x],
                index=mes_actual - 1,
            )
        with col_filtro2:
            anio_sel = st.selectbox("Año:", options=[2026, 2025, 2024], index=0)
        with col_filtro3:
            todas_cats = ["Todas"] + CATEGORIAS_PREDETERMINADAS
            cat_sel = st.selectbox("Filtrar por Categoría:", options=todas_cats, index=0)

    # Cálculo dinámico de métricas
    metricas = gestor.calcular_metricas(mes=mes_sel, anio=anio_sel, categoria_filtro=cat_sel)

    # 1. FILA DE KPIS PRINCIPALES
    with st.container(horizontal=True):
        st.metric(
            label="Total Gastado",
            value=f"${metricas['total_gastado']:,.0f} COP",
            delta=f"{metricas['porcentaje_consumido']:.1f}% del límite",
            delta_color="inverse",
            border=True,
        )
        st.metric(
            label="Presupuesto Disponible",
            value=f"${metricas['restante']:,.0f} COP",
            delta=f"Límite: ${metricas['presupuesto_total']:,.0f}",
            border=True,
        )
        st.metric(
            label="Transacciones",
            value=f"{metricas['total_gastos']} registros",
            border=True,
        )
        st.metric(
            label="Estado del Presupuesto",
            value=metricas["estado_global"],
            delta="Saludable" if metricas["estado_global"] == "SALUDABLE" else "Atención Requerida",
            delta_color="normal" if metricas["estado_global"] == "SALUDABLE" else "inverse",
            border=True,
        )

    # Alertas activas por categorías si las hay
    if metricas["alertas_categoria"]:
        with st.container(border=True):
            st.subheader("🔔 Alertas Específicas de Presupuesto")
            for al in metricas["alertas_categoria"]:
                if al["nivel"] == "CRÍTICO":
                    st.error(f"🔴 **{al['categoria']}**: {al['mensaje']}")
                else:
                    st.warning(f"🟡 **{al['categoria']}**: {al['mensaje']}")

    # 2. FILA DE GRÁFICOS INTERACTIVOS
    col_g1, col_g2 = st.columns(2)

    with col_g1:
        with st.container(border=True):
            st.subheader("Distribución de Gastos por Categoría")
            if metricas["por_categoria"]:
                df_cat = pd.DataFrame(
                    list(metricas["por_categoria"].items()),
                    columns=["Categoría", "Monto (COP)"],
                ).sort_values(by="Monto (COP)", ascending=False)
                st.bar_chart(df_cat, x="Categoría", y="Monto (COP)", color="#3b82f6")
            else:
                st.info("No hay gastos registrados para este periodo.")

    with col_g2:
        with st.container(border=True):
            st.subheader("Evolución Cronológica de Gastos")
            if metricas["por_dia"]:
                df_dias = pd.DataFrame(
                    list(metricas["por_dia"].items()),
                    columns=["Fecha", "Total Diario"],
                ).sort_values(by="Fecha")
                st.area_chart(df_dias, x="Fecha", y="Total Diario", color="#10b981")
            else:
                st.info("No hay transacciones registradas para este periodo.")

    # 3. TOP COMERCIOS
    with st.container(border=True):
        st.subheader("Establecimientos con Mayor Volumen de Compra")
        if metricas["top_comercios"]:
            df_com = pd.DataFrame(
                metricas["top_comercios"],
                columns=["Establecimiento / Comercio", "Monto Total (COP)"],
            )
            st.dataframe(df_com, width="stretch", hide_index=True)
        else:
            st.info("Sin comercios registrados aún.")

# =============================================================================
# PESTAÑA 2: ESCÁNER DE RECIBOS Y FACTURAS (IA MULTIMODAL)
# =============================================================================
with tab_scanner:
    st.header("📸 Escaneo Inteligente de Comprobantes", divider="blue")
    st.markdown(
        "Sube una foto o captura de tu **factura, recibo de compra o comprobante bancario**. "
        "Gemini analizará la imagen y extraerá automáticamente el comercio, fecha, monto, "
        "categoría sugerida y desglose de items."
    )

    col_subida, col_resultado = st.columns([1, 1], gap="medium")

    with col_subida:
        with st.container(border=True):
            archivo_subido = st.file_uploader(
                "Selecciona una imagen de recibo o comprobante:",
                type=["png", "jpg", "jpeg", "webp"],
                help="Formatos admitidos: PNG, JPG, JPEG, WEBP",
            )

            if archivo_subido is not None:
                img_subida = Image.open(archivo_subido)
                st.image(img_subida, caption="Vista previa del comprobante", width="stretch")

                boton_procesar = st.button(
                    "Extraer Datos con Gemini",
                    type="primary",
                    icon=":material/document_scanner:",
                )
                if boton_procesar:
                    with st.spinner("Analizando comprobante con visión artificial..."):
                        recibo_extraido = extractor.extraer_desde_imagen(img_subida)
                        st.session_state["recibo_pendiente"] = recibo_extraido
                        st.success("¡Datos extraídos con éxito! Revisa y confirma a la derecha.")
            else:
                st.info("Sube una foto para activar el analizador multimodal.")

    with col_resultado:
        with st.container(border=True):
            st.subheader("Verificación y Registro")
            if "recibo_pendiente" in st.session_state:
                r = st.session_state["recibo_pendiente"]

                with st.form("form_confirmacion_gasto"):
                    conf_comercio = st.text_input("Comercio / Establecimiento:", value=r.comercio)
                    col_f1, col_f2 = st.columns(2)
                    with col_f1:
                        conf_monto = st.number_input("Monto Total (COP):", value=float(r.monto_total), min_value=0.0, step=1000.0)
                    with col_f2:
                        conf_fecha = st.text_input("Fecha (YYYY-MM-DD):", value=r.fecha)

                    col_c1, col_c2 = st.columns(2)
                    with col_c1:
                        idx_cat = CATEGORIAS_PREDETERMINADAS.index(r.categoria_sugerida) if r.categoria_sugerida in CATEGORIAS_PREDETERMINADAS else 0
                        conf_categoria = st.selectbox("Categoría:", options=CATEGORIAS_PREDETERMINADAS, index=idx_cat)
                    with col_c2:
                        conf_metodo = st.selectbox(
                            "Método de Pago:",
                            options=["Tarjeta de Crédito", "Tarjeta Débito", "Transferencia Bancaria", "Efectivo"],
                            index=0,
                        )

                    conf_desc = st.text_area("Descripción / Detalle:", value=r.descripcion)
                    st.caption(f"Nivel de confianza de la IA: **{r.confianza * 100:.0f}%**")

                    btn_guardar = st.form_submit_button("Guardar en Presupuesto", icon=":material/check_circle:")
                    if btn_guardar:
                        nuevo_gasto = Gasto(
                            comercio=conf_comercio,
                            fecha=conf_fecha,
                            monto=conf_monto,
                            categoria=conf_categoria,
                            metodo_pago=conf_metodo,
                            descripcion=conf_desc,
                            tipo_documento=r.tipo_documento,
                            confianza_extraccion=r.confianza,
                            items=r.items,
                        )
                        gestor.agregar_gasto(nuevo_gasto)
                        del st.session_state["recibo_pendiente"]
                        st.toast("¡Gasto registrado con éxito en el presupuesto!", icon="💳")
                        st.success("¡Transacción guardada exitosamente!")
                        st.rerun()
            else:
                st.write("Aquí podrás verificar y editar los datos antes de guardarlos.")

# =============================================================================
# PESTAÑA 3: REGISTRO DE GASTOS Y FACTURAS
# =============================================================================
with tab_transacciones:
    st.header("📋 Historial de Transacciones Registradas", divider="blue")

    gastos_todos = gestor.cargar_gastos()

    if gastos_todos:
        # Convertir a DataFrame para visualización
        df_gastos = pd.DataFrame([g.to_dict() for g in gastos_todos])
        df_mostrar = df_gastos[[
            "id", "fecha", "comercio", "categoria", "monto", "metodo_pago", "descripcion"
        ]].copy()
        df_mostrar.columns = ["ID Transacción", "Fecha", "Comercio", "Categoría", "Monto (COP)", "Método Pago", "Descripción"]

        # Buscador y filtro
        col_b1, col_b2 = st.columns([3, 1])
        with col_b1:
            texto_busqueda = st.text_input("🔍 Buscar por comercio o concepto:", placeholder="Ej. Éxito, Gasolina, Terpel...")
        with col_b2:
            st.metric("Total Transacciones", f"{len(df_mostrar)}")

        if texto_busqueda:
            filtro = (
                df_mostrar["Comercio"].str.contains(texto_busqueda, case=False, na=False) |
                df_mostrar["Descripción"].str.contains(texto_busqueda, case=False, na=False) |
                df_mostrar["Categoría"].str.contains(texto_busqueda, case=False, na=False)
            )
            df_mostrar = df_mostrar[filtro]

        st.dataframe(
            df_mostrar,
            width="stretch",
            hide_index=True,
            column_config={
                "Monto (COP)": st.column_config.NumberColumn(format="$%.0f COP"),
            },
        )

        # Acciones de gestión (Eliminar registro)
        with st.expander("🗑️ Eliminar una transacción específica", expanded=False):
            ids_disponibles = [g.id for g in gastos_todos]
            id_a_eliminar = st.selectbox("Selecciona ID de transacción a eliminar:", options=ids_disponibles)
            if st.button("Eliminar Transacción", type="secondary", icon=":material/delete:"):
                if gestor.eliminar_gasto(id_a_eliminar):
                    st.success(f"Transacción {id_a_eliminar} eliminada correctamente.")
                    st.rerun()

        # Exportar datos
        csv_data = df_mostrar.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Descargar Historial en CSV",
            data=csv_data,
            file_name="gastos_foto_y_control.csv",
            mime="text/csv",
            icon=":material/download:",
        )
    else:
        st.info("No hay transacciones registradas actualmente.")

# =============================================================================
# PESTAÑA 4: COACH FINANCIERO GEMINI (CHAT CONSULTIVO)
# =============================================================================
with tab_coach:
    # Inyección de estilos CSS para fijar la estructura y estilizar el scroll del chat
    st.markdown(
        """
        <style>
            /* Evitar scroll general en el fondo y fijar estructura */
            .stApp {
                overflow-x: hidden;
            }

            /* Scrollbar minimalista y moderna tipo SaaS para contenedores con scroll */
            div[data-testid="stVerticalBlockBorderWrapper"] ::-webkit-scrollbar {
                width: 6px;
                height: 6px;
            }
            div[data-testid="stVerticalBlockBorderWrapper"] ::-webkit-scrollbar-track {
                background: transparent;
            }
            div[data-testid="stVerticalBlockBorderWrapper"] ::-webkit-scrollbar-thumb {
                background: rgba(148, 163, 184, 0.4);
                border-radius: 4px;
            }
            div[data-testid="stVerticalBlockBorderWrapper"] ::-webkit-scrollbar-thumb:hover {
                background: rgba(100, 116, 139, 0.7);
            }

            /* Contenedor del chat con desplazamiento suave */
            [data-testid="stChatMessageContainer"] {
                scroll-behavior: smooth;
            }

            /* Input de chat fijado sin interferencias de scroll */
            div[data-testid="stChatInput"] {
                position: relative;
                z-index: 100;
                margin-top: 8px;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.header("🤖 Coach de Ahorro y Asesor Financiero Gemini", divider="blue")
    st.caption("Gemini analiza tus cifras reales de gastos en vivo para darte consejos prácticos de ahorro y optimización.")

    # 1. ELEMENTOS ESTRUCTURALES ESTÁTICOS (Botones de consultas frecuentes rápidas)
    with st.container(border=True):
        st.markdown("**Consultas sugeridas para tu coach:**")
        col_p1, col_p2, col_p3 = st.columns(3)
        pregunta_rapida = None
        with col_p1:
            if st.button("💡 ¿Dónde puedo recortar gastos?", icon=":material/savings:", width="stretch"):
                pregunta_rapida = "¿En qué categorías estoy gastando más y cómo puedo recortar gastos este mes de forma realista?"
        with col_p2:
            if st.button("📊 Dame un balance ejecutivo", icon=":material/analytics:", width="stretch"):
                pregunta_rapida = "Dame un resumen ejecutivo de cómo voy este mes con respecto a mi presupuesto disponible."
        with col_p3:
            if st.button("🔍 Identificar 'gastos hormiga'", icon=":material/search:", width="stretch"):
                pregunta_rapida = "Analiza mis transacciones e identifica si tengo fugas de dinero o gastos hormiga innecesarios."

    # 2. CONTENEDOR DE CHAT CON SCROLL INDEPENDIENTE (Altura fija de 480px)
    chat_container = st.container(height=480, border=True)
    with chat_container:
        for msg in st.session_state.mensajes_coach:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    # 3. ENTRADA DE CHAT ESTÁTICA FUERA DEL CONTENEDOR DESPLAZABLE
    entrada_usuario = st.chat_input("Escribe tu consulta financiera...", submit_mode="disable")
    pregunta_final = pregunta_rapida or entrada_usuario

    if pregunta_final:
        # Registrar mensaje del usuario
        st.session_state.mensajes_coach.append({"role": "user", "content": pregunta_final})

        # Renderizar mensaje del usuario y respuesta dentro del contenedor con scroll
        with chat_container:
            with st.chat_message("user"):
                st.markdown(pregunta_final)

            metricas_actuales = gestor.calcular_metricas()
            with st.chat_message("assistant"):
                respuesta_stream = asistente.responder_consulta(
                    mensaje_usuario=pregunta_final,
                    metricas=metricas_actuales,
                )
                respuesta_completa = st.write_stream(respuesta_stream)

        # Guardar respuesta del asistente y actualizar
        st.session_state.mensajes_coach.append({"role": "assistant", "content": respuesta_completa})
        st.rerun()

# =============================================================================
# PESTAÑA 5: ENVÍO DE REPORTE POR CORREO ELECTRÓNICO (SMTP)
# =============================================================================
with tab_correo:
    st.header("📧 Despacho de Reporte Financiero por Correo", divider="blue")
    st.markdown(
        "Envía un **balance ejecutivo consolidado con diseño profesional** a tu correo electrónico "
        "utilizando el protocolo SMTP."
    )

    with st.container(border=True):
        metricas_envio = gestor.calcular_metricas()

        col_c1, col_c2 = st.columns([2, 1])
        with col_c1:
            correo_destino = st.text_input(
                "Correo electrónico del destinatario:",
                value=os.getenv("SMTP_USER", "scuadrod@gmail.com"),
                placeholder="ejemplo@correo.com",
            )
            asunto_personalizado = st.text_input(
                "Asunto del correo:",
                value=f"📊 Reporte Financiero Mensual - {datetime.now().strftime('%B %Y')}",
            )
        with col_c2:
            st.markdown("### Configuración Activa")
            st.caption(f"Servidor SMTP: **{gestor_correo.servidor}:{gestor_correo.puerto}**")
            st.caption(f"Remitente: **{gestor_correo.usuario or 'No configurado'}**")

        st.markdown("#### Vista Previa del Reporte:")
        with st.expander("Ver diseño del correo a enviar", expanded=False):
            html_preview = gestor_correo.generar_cuerpo_html(metricas_envio)
            st.html(html_preview)

        btn_enviar_correo = st.button(
            "Enviar Reporte por Correo Ahora",
            type="primary",
            icon=":material/send:",
        )

        if btn_enviar_correo:
            if not correo_destino:
                st.error("Por favor ingresa una dirección de correo válida.")
            else:
                with st.spinner(f"Enviando reporte a {correo_destino} mediante SMTP..."):
                    exito, mensaje_envio = gestor_correo.enviar_reporte(
                        destinatario=correo_destino,
                        metricas=metricas_envio,
                        asunto=asunto_personalizado,
                    )
                    if exito:
                        st.success(f"✅ ¡{mensaje_envio}")
                        st.toast("Reporte despachado exitosamente por correo", icon="📬")
                    else:
                        st.error(f"❌ {mensaje_envio}")
