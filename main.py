import os
import glob
import streamlit as st
from datetime import datetime
from dotenv import load_dotenv

from utils import (
    load_user_settings,
    save_user_settings,
    parse_prospecting_output,
    extract_email_address
)
from tools.email_tool import (
    EMAIL_PROVIDERS,
    send_email_smtp,
    test_smtp_connection
)

# Cargar variables locales iniciales si existen
load_dotenv()

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Prospecta AI - Agente Autónomo B2B",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Cargar configuraciones guardadas
saved_settings = load_user_settings()

# Inicializar Session State si no existe
if "settings" not in st.session_state:
    st.session_state.settings = saved_settings.copy()
    # Si hay variables en el entorno (.env), usarlas si las guardadas están vacías
    if not st.session_state.settings.get("google_api_key"):
        st.session_state.settings["google_api_key"] = os.environ.get("GOOGLE_API_KEY", "")
    if not st.session_state.settings.get("groq_api_key"):
        st.session_state.settings["groq_api_key"] = os.environ.get("GROQ_API_KEY", "")

if "current_leads" not in st.session_state:
    st.session_state.current_leads = []
if "current_raw" not in st.session_state:
    st.session_state.current_raw = ""
if "sent_logs" not in st.session_state:
    st.session_state.sent_logs = []

# --- BARRA LATERAL (ESTADO RÁPIDO) ---
with st.sidebar:
    st.image("https://api.iconify.design/lucide:bot.svg?color=%234f46e5&width=56", width=56)
    st.title("Prospecta AI")
    st.caption("Sistema Autónomo de Prospección B2B y Envío de Emails")
    
    # Estado de las claves y correo
    has_api_key = bool(st.session_state.settings.get("google_api_key"))
    has_email = bool(st.session_state.settings.get("email_user") and st.session_state.settings.get("email_password"))

    st.markdown("### 🚦 Estado del Sistema")
    if has_api_key:
        st.success("✅ Gemini API Key configurada")
    else:
        st.warning("⚠️ Falta Gemini API Key")

    if has_email:
        st.success(f"✅ Correo conectado ({st.session_state.settings.get('email_user')})")
    else:
        st.info("ℹ️ Correo no configurado (solo redactará)")

    st.markdown("---")
    st.markdown("💡 **Consejo rápido:** Puedes configurar tu propia API Key de Google (gratuita) y tu cuenta de correo en la pestaña **⚙️ Configuración**.")

# --- TÍTULO PRINCIPAL ---
st.title("🎯 Prospecta AI: Agentes de Prospección y Ventas")
st.markdown("Encuentra clientes potenciales, investiga a sus competidores, redacta correos hiperpersonalizados y envíalos con un solo clic.")

# PESTAÑAS PRINCIPALES
tab_prospect, tab_leads, tab_config, tab_history = st.tabs([
    "🚀 1. Nueva Prospección",
    "📨 2. Leads y Envíos de Email",
    "⚙️ 3. Configuración de Cuentas",
    "📜 4. Historial Guardado"
])

# ==========================================
# TAB 1: NUEVA PROSPECCIÓN
# ==========================================
with tab_prospect:
    st.subheader("Configura tu Campaña de Prospección")
    
    col_niche, col_tone = st.columns([2, 1])
    
    with col_niche:
        niche_input = st.text_input(
            "¿Qué nicho o sector quieres prospectar?",
            placeholder="Ej: Centros de fisioterapia en Valencia, Agencias de diseño en Barcelona...",
            help="Define la actividad comercial y la ubicación geográfica objetivo."
        )
        
        # Atajos rápidos con ejemplos
        st.caption("Sugerencias de ejemplo:")
        sugg_cols = st.columns(3)
        if sugg_cols[0].button("🏋️ Gimnasios en Madrid"):
            niche_input = "Gimnasios y centros de fitness en Madrid"
        if sugg_cols[1].button("🦷 Clínicas Dentales en Sevilla"):
            niche_input = "Clínicas dentales privadas en Sevilla"
        if sugg_cols[2].button("💻 Agencias Web en Barcelona"):
            niche_input = "Agencias de desarrollo web y marketing en Barcelona"

    with col_tone:
        tone_options = (
            "Directo hacia el ROI y Profesional",
            "Desenfadado y Cercano",
            "Curioso y Provocativo",
            "Formal y Corporativo"
        )
        current_tone = st.session_state.settings.get("default_tone", tone_options[0])
        tone_index = tone_options.index(current_tone) if current_tone in tone_options else 0
        tone = st.selectbox("Tono de los emails", tone_options, index=tone_index)

    value_prop = st.text_area(
        "¿Cuál es tu Propuesta de Valor? (¿Qué vendes y qué problema resuelves?)",
        value=st.session_state.settings.get("default_value_prop", ""),
        placeholder="Ej: Automatizamos el agendamiento de citas de pacientes con IA para evitar ausencias y aumentar la facturación un 20% sin contratar más personal.",
        help="Los agentes usarán esta descripción para encontrar el mejor ángulo comercial para cada empresa investigada."
    )

    st.markdown("<br>", unsafe_allow_html=True)
    start_btn = st.button("🚀 Iniciar Prospección Autónoma", type="primary", use_container_width=True)

    if start_btn:
        api_key = st.session_state.settings.get("google_api_key", "").strip()
        groq_key = st.session_state.settings.get("groq_api_key", "").strip()

        if not api_key:
            st.error("❌ Necesitas configurar tu Google Gemini API Key. Ve a la pestaña '⚙️ 3. Configuración de Cuentas' para introducirla (es gratuita).")
        elif not niche_input or not value_prop:
            st.error("❌ Por favor completa el 'Nicho' y tu 'Propuesta de Valor' antes de iniciar.")
        else:
            # Inyectar variables de entorno para la ejecución actual
            os.environ["GOOGLE_API_KEY"] = api_key
            if groq_key:
                os.environ["GROQ_API_KEY"] = groq_key

            st.info("🤖 **Tripulación de Agentes IA activada.** Investigando internet, analizando empresas y redactando emails personalizados...")
            
            with st.spinner("Los agentes están buscando empresas, extrayendo datos web, analizando competidores y creando la estrategia..."):
                try:
                    from orchestrator import SDRCrew
                    
                    crew_system = SDRCrew(
                        niche=niche_input,
                        value_proposition=value_prop,
                        tone=tone
                    )
                    
                    result = crew_system.run()
                    raw_text = getattr(result, "raw", str(result))
                    
                    # Guardar en sesión
                    st.session_state.current_raw = raw_text
                    st.session_state.current_leads = parse_prospecting_output(raw_text)
                    
                    st.success("✅ ¡Prospección completada con éxito! Ve a la pestaña '📨 2. Leads y Envíos de Email' para revisar y enviar los correos.")
                    st.balloons()
                    
                except Exception as e:
                    st.error(f"❌ Ocurrió un error durante la ejecución de los agentes: {str(e)}")

# ==========================================
# TAB 2: LEADS Y ENVÍOS DE EMAIL
# ==========================================
with tab_leads:
    st.subheader("Resultados Obtenidos y Gestión de Envíos")

    if not st.session_state.current_leads and not st.session_state.current_raw:
        st.info("Aún no has ejecutado ninguna prospección en esta sesión. Completa los datos en la pestaña '🚀 1. Nueva Prospección' o abre un reporte desde '📜 4. Historial Guardado'.")
    else:
        leads = st.session_state.current_leads
        st.write(f"Se han identificado **{len(leads)} prospecto(s)** listos para contactar:")

        email_user = st.session_state.settings.get("email_user", "")
        email_ready = bool(email_user and st.session_state.settings.get("email_password"))

        if not email_ready:
            st.warning("⚠️ **Aviso:** No has configurado tu cuenta de correo en '⚙️ 3. Configuración'. Podrás ver y editar los emails generados, pero para enviarlos directamente debes configurar tu correo.")

        for i, lead in enumerate(leads):
            empresa = lead.get("empresa", f"Prospecto #{i+1}")
            with st.expander(f"🏢 {empresa}", expanded=True):
                col_info, col_action = st.columns([3, 2])

                with col_info:
                    st.markdown(f"**Empresa:** {lead.get('empresa', 'N/D')}")
                    if lead.get("contacto"):
                        st.markdown(f"**Contacto detectado:** {lead.get('contacto')}")
                    if lead.get("direccion"):
                        st.markdown(f"**Dirección:** {lead.get('direccion')}")

                # Inputs editables para asunto y destinatario
                recipient_email = st.text_input(
                    f"Email destinatario ({empresa})",
                    value=lead.get("email_destinatario", ""),
                    key=f"recip_{i}",
                    placeholder="ejemplo@empresa.com"
                )

                email_subject = st.text_input(
                    f"Asunto del Email ({empresa})",
                    value=lead.get("asunto", "Propuesta de colaboración"),
                    key=f"subj_{i}"
                )

                email_body = st.text_area(
                    f"Cuerpo del mensaje ({empresa})",
                    value=lead.get("cuerpo", ""),
                    height=220,
                    key=f"body_{i}"
                )

                # Botón de envío directo
                col_btn, col_msg = st.columns([1, 2])
                with col_btn:
                    send_btn = st.button(f"📨 Enviar este Email", key=f"send_btn_{i}", type="primary", disabled=not email_ready)

                with col_msg:
                    if send_btn:
                        if not recipient_email or "@" not in recipient_email:
                            st.error("❌ Por favor indica un email de destino válido antes de enviar.")
                        else:
                            with st.spinner(f"Enviando correo a {recipient_email}..."):
                                smtp_config = {
                                    "host": st.session_state.settings.get("smtp_host", "smtp.gmail.com"),
                                    "port": st.session_state.settings.get("smtp_port", 587),
                                    "user": st.session_state.settings.get("email_user", ""),
                                    "password": st.session_state.settings.get("email_password", ""),
                                    "use_tls": st.session_state.settings.get("smtp_tls", True),
                                    "sender_name": st.session_state.settings.get("email_sender_name", "")
                                }
                                success, msg = send_email_smtp(
                                    to_email=recipient_email,
                                    subject=email_subject,
                                    body=email_body,
                                    smtp_config=smtp_config
                                )
                                if success:
                                    st.success(f"✅ {msg}")
                                    st.session_state.sent_logs.append({
                                        "empresa": empresa,
                                        "email": recipient_email,
                                        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                    })
                                else:
                                    st.error(f"❌ {msg}")

        # Sección para ver el texto completo bruto y descargarlo
        st.markdown("---")
        with st.expander("📄 Ver y Descargar Informe Completo en Bruto"):
            st.text_area("Contenido completo generado por los agentes:", value=st.session_state.current_raw, height=300)
            st.download_button(
                label="📥 Descargar Informe (.txt)",
                data=st.session_state.current_raw,
                file_name=f"informe_prospeccion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain"
            )

# ==========================================
# TAB 3: CONFIGURACIÓN DE CUENTAS
# ==========================================
with tab_config:
    st.subheader("⚙️ Configuración Personalizada")
    st.markdown("Configura aquí tus claves de Inteligencia Artificial y tu cuenta de correo. **Estos datos se guardan en tu propia máquina/sesión para que nadie consuma tus tokens.**")

    col_ai, col_mail = st.columns(2)

    with col_ai:
        st.markdown("### 🧠 Inteligencia Artificial")
        
        cfg_gemini = st.text_input(
            "Google Gemini API Key (Requerido)",
            value=st.session_state.settings.get("google_api_key", ""),
            type="password",
            help="Clave de Google Gemini. Es 100% gratuita."
        )

        with st.expander("❓ ¿Cómo conseguir tu clave gratis de Gemini en 1 minuto?"):
            st.markdown("""
            1. Entra en **[Google AI Studio (aistudio.google.com)](https://aistudio.google.com/app/apikey)** con tu cuenta de Google.
            2. Haz clic en el botón azul **'Create API Key'** (o 'Get API Key').
            3. Copia el código que te da y pégalo en esta casilla.
            4. ¡Listo! Ya tienes acceso gratuito sin tarjeta de crédito.
            """)

        cfg_groq = st.text_input(
            "Groq API Key (Opcional)",
            value=st.session_state.settings.get("groq_api_key", ""),
            type="password",
            help="Opcional. Permite acelerar el redactor con modelos Llama ultra rápidos."
        )

        st.markdown("---")
        st.markdown("### 📝 Textos y Plantillas Predeterminadas")
        cfg_default_vp = st.text_area(
            "Tu Propuesta de Valor por defecto:",
            value=st.session_state.settings.get("default_value_prop", ""),
            height=100
        )

    with col_mail:
        st.markdown("### ✉️ Cuenta de Correo (Para Envíos)")
        
        provider_names = list(EMAIL_PROVIDERS.keys())
        saved_provider = st.session_state.settings.get("email_provider", "Gmail")
        prov_index = provider_names.index(saved_provider) if saved_provider in provider_names else 0
        
        cfg_provider = st.selectbox("Proveedor de Correo:", provider_names, index=prov_index)
        provider_info = EMAIL_PROVIDERS[cfg_provider]
        st.caption(f"ℹ️ {provider_info['note']}")

        cfg_sender_name = st.text_input(
            "Tu Nombre o Nombre de tu Empresa (Visible para el cliente):",
            value=st.session_state.settings.get("email_sender_name", ""),
            placeholder="Ej: Carlos Gómez - Asesor B2B"
        )

        cfg_email_user = st.text_input(
            "Tu Dirección de Correo Electrónico:",
            value=st.session_state.settings.get("email_user", ""),
            placeholder="micorreo@gmail.com"
        )

        cfg_email_pass = st.text_input(
            "Contraseña o Contraseña de Aplicación:",
            value=st.session_state.settings.get("email_password", ""),
            type="password",
            help="Si usas Gmail o Yahoo, usa una Contraseña de Aplicación de 16 caracteres, no tu contraseña normal."
        )

        if cfg_provider == "Gmail":
            with st.expander("🔒 ¿Cómo crear una Contraseña de Aplicación en Gmail?"):
                st.markdown("""
                Google exige una contraseña de aplicación para que programas externos envíen correos de forma segura:
                1. Ve a tu cuenta de Google: **[myaccount.google.com/security](https://myaccount.google.com/security)**.
                2. Asegúrate de tener activada la **Verificación en dos pasos**.
                3. En el buscador superior escribe **'Contraseñas de aplicaciones'** (o ve a Seguridad -> Verificación en 2 pasos -> Contraseñas de aplicaciones).
                4. Escribe un nombre (ej: 'Prospecta') y pulsa **Crear**.
                5. Copia la clave de 16 letras amarillas y pégala aquí.
                """)

        if cfg_provider == "Personalizado (SMTP)":
            cfg_smtp_host = st.text_input("Servidor SMTP:", value=st.session_state.settings.get("smtp_host", ""))
            cfg_smtp_port = st.number_input("Puerto SMTP:", value=st.session_state.settings.get("smtp_port", 587), step=1)
            cfg_smtp_tls = st.checkbox("Usar STARTTLS", value=st.session_state.settings.get("smtp_tls", True))
        else:
            cfg_smtp_host = provider_info["host"]
            cfg_smtp_port = provider_info["port"]
            cfg_smtp_tls = provider_info["use_tls"]

        # Botón para probar la conexión
        if st.button("🔌 Probar Conexión de Correo"):
            if not cfg_email_user or not cfg_email_pass:
                st.error("Introduce tu correo y contraseña antes de probar.")
            else:
                test_conf = {
                    "host": cfg_smtp_host,
                    "port": cfg_smtp_port,
                    "user": cfg_email_user,
                    "password": cfg_email_pass,
                    "use_tls": cfg_smtp_tls
                }
                with st.spinner("Probando conexión con el servidor de correo..."):
                    ok, msg = test_smtp_connection(test_conf)
                    if ok:
                        st.success(f"✅ {msg}")
                    else:
                        st.error(f"❌ {msg}")

    st.markdown("---")
    if st.button("💾 Guardar Toda la Configuración", type="primary", use_container_width=True):
        new_settings = {
            "google_api_key": cfg_gemini.strip(),
            "groq_api_key": cfg_groq.strip(),
            "email_provider": cfg_provider,
            "email_user": cfg_email_user.strip(),
            "email_password": cfg_email_pass.strip(),
            "email_sender_name": cfg_sender_name.strip(),
            "smtp_host": cfg_smtp_host,
            "smtp_port": int(cfg_smtp_port),
            "smtp_tls": cfg_smtp_tls,
            "default_value_prop": cfg_default_vp.strip()
        }
        st.session_state.settings.update(new_settings)
        if save_user_settings(new_settings):
            st.success("✅ ¡Configuración guardada correctamente! No tendrás que volver a introducirla.")
        else:
            st.error("No se pudo guardar en el archivo local, pero se mantendrá activo en esta sesión.")

# ==========================================
# TAB 4: HISTORIAL GUARDADO
# ==========================================
with tab_history:
    st.subheader("📜 Historial de Prospecciones Realizadas")
    st.markdown("Accede a las prospecciones guardadas en cualquier momento para volver a revisar datos o enviar correos pendientes.")

    base_dir = os.path.dirname(os.path.abspath(__file__))
    txt_files = sorted(glob.glob(os.path.join(base_dir, "prospeccion_*.txt")), reverse=True)

    if not txt_files:
        st.info("No hay archivos de prospección previos todavía.")
    else:
        selected_file = st.selectbox(
            "Selecciona una prospección anterior:",
            txt_files,
            format_func=lambda x: os.path.basename(x)
        )

        if selected_file:
            try:
                # Intentar leer en utf-8, fallback a utf-16 si es antiguo
                try:
                    with open(selected_file, "r", encoding="utf-8") as f:
                        content = f.read()
                except UnicodeDecodeError:
                    with open(selected_file, "r", encoding="utf-16") as f:
                        content = f.read()

                col_h1, col_h2 = st.columns([1, 1])
                with col_h1:
                    if st.button("📂 Cargar esta Prospección en la Pestaña de Envíos"):
                        st.session_state.current_raw = content
                        st.session_state.current_leads = parse_prospecting_output(content)
                        st.success("✅ Prospección cargada. Ve a la pestaña '📨 2. Leads y Envíos de Email' para gestionarla.")

                with col_h2:
                    st.download_button(
                        label="📥 Descargar Archivo",
                        data=content,
                        file_name=os.path.basename(selected_file),
                        mime="text/plain",
                        key=f"dl_{os.path.basename(selected_file)}"
                    )

                st.text_area("Vista previa del contenido:", value=content, height=250)
            except Exception as e:
                st.error(f"Error al leer el archivo: {e}")

# Historial de correos enviados en la sesión
if st.session_state.sent_logs:
    st.markdown("---")
    st.subheader("📬 Correos Enviados en esta Sesión")
    for log in st.session_state.sent_logs:
        st.write(f"• **{log['empresa']}** ({log['email']}) — Enviado a las {log['fecha']}")

st.markdown("---")
st.caption("Prospecta AI | Arquitectura: Streamlit + CrewAI Multi-Agente + SMTP + Google Gemini Flash")
