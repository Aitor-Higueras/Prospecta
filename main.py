import os
import glob
import streamlit as st
from datetime import datetime
from dotenv import load_dotenv

from utils import (
    AI_PROVIDERS,
    load_user_settings,
    save_user_settings,
    parse_prospecting_output,
    extract_email_address,
    leads_to_dataframe
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
    # Si hay variables en el entorno (.env), usarlas como respaldo
    if not st.session_state.settings.get("ai_api_key"):
        if os.environ.get("GOOGLE_API_KEY"):
            st.session_state.settings["ai_api_key"] = os.environ.get("GOOGLE_API_KEY")
            st.session_state.settings["ai_provider"] = "Google Gemini (Recomendado / Gratis)"
        elif os.environ.get("OPENAI_API_KEY"):
            st.session_state.settings["ai_api_key"] = os.environ.get("OPENAI_API_KEY")
            st.session_state.settings["ai_provider"] = "OpenAI (ChatGPT)"
            st.session_state.settings["ai_model"] = "openai/gpt-4o-mini"
        elif os.environ.get("DEEPSEEK_API_KEY"):
            st.session_state.settings["ai_api_key"] = os.environ.get("DEEPSEEK_API_KEY")
            st.session_state.settings["ai_provider"] = "DeepSeek"
            st.session_state.settings["ai_model"] = "deepseek/deepseek-chat"

if "current_leads" not in st.session_state:
    st.session_state.current_leads = []
if "current_raw" not in st.session_state:
    st.session_state.current_raw = ""
if "sent_logs" not in st.session_state:
    st.session_state.sent_logs = []

active_ai_provider = st.session_state.settings.get("ai_provider", "Google Gemini (Recomendado / Gratis)")
active_ai_model = st.session_state.settings.get("ai_model", "gemini/gemini-2.5-flash")
has_ai_key = bool(st.session_state.settings.get("ai_api_key", "").strip())
has_email = bool(st.session_state.settings.get("email_user") and st.session_state.settings.get("email_password"))

# --- BARRA LATERAL (ESTADO RÁPIDO) ---
with st.sidebar:
    st.image("https://api.iconify.design/lucide:bot.svg?color=%234f46e5&width=56", width=56)
    st.title("Prospecta AI")
    st.caption("Plataforma Multi-Proveedor B2B y Envíos de Email")
    
    st.markdown("### 🚦 Estado del Sistema")
    if has_ai_key:
        st.success(f"✅ **IA Conectada:** {active_ai_provider.split('(')[0].strip()}")
    else:
        st.warning("⚠️ **Falta la clave de IA** (ve a ⚙️ Configuración)")

    if has_email:
        st.success(f"✅ **Correo Conectado:**\n`{st.session_state.settings.get('email_user')}`")
    else:
        st.info("ℹ️ Correo no configurado (modo solo redacción)")

    st.markdown("---")
    st.markdown("💡 **Cero ataduras:** Puedes cambiar de proveedor de IA (Gemini, ChatGPT, DeepSeek, Claude, Groq...) en cualquier momento en la pestaña **⚙️ 3. Configuración**.")

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
    
    # Cartel informativo del modelo activo
    if has_ai_key:
        st.caption(f"🧠 Motor de IA activo: **{active_ai_provider}** | Modelo: `{active_ai_model}`")
    else:
        st.warning("⚠️ Recuerda añadir tu API Key en la pestaña '⚙️ 3. Configuración de Cuentas' antes de comenzar.")

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
        col_t1, col_t2 = st.columns([1, 1])
        with col_t1:
            tone_options = (
                "Directo hacia el ROI y Profesional",
                "Desenfadado y Cercano",
                "Curioso y Provocativo",
                "Formal y Corporativo"
            )
            current_tone = st.session_state.settings.get("default_tone", tone_options[0])
            tone_index = tone_options.index(current_tone) if current_tone in tone_options else 0
            tone = st.selectbox("Tono del email", tone_options, index=tone_index)
        with col_t2:
            leads_count = st.selectbox(
                "Nº de Prospectos",
                [3, 5, 8, 10],
                index=0,
                help="Número de empresas reales que los agentes buscarán e investigarán."
            )

    value_prop = st.text_area(
        "¿Cuál es tu Propuesta de Valor? (¿Qué vendes y qué problema resuelves?)",
        value=st.session_state.settings.get("default_value_prop", ""),
        placeholder="Ej: Automatizamos el agendamiento de citas de pacientes con IA para evitar ausencias y aumentar la facturación un 20% sin contratar más personal.",
        help="Los agentes usarán esta descripción para encontrar el mejor ángulo comercial para cada empresa investigada."
    )

    st.markdown("<br>", unsafe_allow_html=True)
    start_btn = st.button("🚀 Iniciar Prospección Autónoma", type="primary", use_container_width=True)

    if start_btn:
        api_key = st.session_state.settings.get("ai_api_key", "").strip()
        model_name = st.session_state.settings.get("ai_model", "gemini/gemini-2.5-flash").strip()
        base_url = st.session_state.settings.get("ai_base_url", "").strip()

        if not api_key and not ("ollama" in model_name):
            st.error(f"❌ Necesitas configurar la API Key para {active_ai_provider}. Ve a la pestaña '⚙️ 3. Configuración de Cuentas' para introducirla.")
        elif not niche_input or not value_prop:
            st.error("❌ Por favor completa el 'Nicho' y tu 'Propuesta de Valor' antes de iniciar.")
        else:
            # Inyectar variables de entorno según el proveedor para máxima compatibilidad
            provider_data = AI_PROVIDERS.get(active_ai_provider, {})
            env_var = provider_data.get("env_var", "AI_API_KEY")
            if env_var:
                os.environ[env_var] = api_key

            st.info(f"🤖 **Tripulación activada con {active_ai_provider} ({model_name}).** Investigando {leads_count} prospectos...")
            
            with st.spinner(f"Los agentes están buscando {leads_count} empresas, extrayendo datos web y redactando emails..."):
                try:
                    from orchestrator import SDRCrew
                    
                    crew_system = SDRCrew(
                        niche=niche_input,
                        value_proposition=value_prop,
                        tone=tone,
                        leads_count=leads_count,
                        ai_model=model_name,
                        api_key=api_key,
                        ai_base_url=base_url if base_url else None
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
        
        # Barra superior con estadísticas y botón de descarga en Excel / CSV
        df_leads = leads_to_dataframe(leads)
        csv_data = df_leads.to_csv(index=False, sep=";", encoding="utf-8-sig")
        
        col_hdr_info, col_hdr_dl = st.columns([2, 1])
        with col_hdr_info:
            emails_found = sum(1 for l in leads if l.get("email_destinatario"))
            st.markdown(f"Se han identificado **{len(leads)} prospectos** ({emails_found} con email detectado):")
        with col_hdr_dl:
            st.download_button(
                label="📊 Descargar Leads en Excel (.csv)",
                data=csv_data,
                file_name=f"leads_prospecta_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                type="secondary",
                use_container_width=True
            )

        email_user = st.session_state.settings.get("email_user", "")
        email_ready = bool(email_user and st.session_state.settings.get("email_password"))

        if not email_ready:
            st.warning("⚠️ **Aviso:** No has configurado tu cuenta de correo en '⚙️ 3. Configuración'. Podrás ver y editar los emails generados, pero para enviarlos directamente debes conectar tu correo.")

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
                                    "sender_name": st.session_state.settings.get("email_sender_name", ""),
                                    "signature": st.session_state.settings.get("email_signature", ""),
                                    "bcc_self": st.session_state.settings.get("email_bcc_self", False)
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

        # Sección para ver el informe completo
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
    st.subheader("⚙️ Configuración Personalizada (IA y Correo)")
    st.markdown("Configura aquí el proveedor de Inteligencia Artificial que prefieras y tu cuenta de correo. **Estos datos se guardan exclusivamente en tu navegador o archivo local.**")

    col_ai, col_mail = st.columns(2)

    with col_ai:
        st.markdown("### 🧠 Inteligencia Artificial")
        
        provider_list = list(AI_PROVIDERS.keys())
        saved_ai_prov = st.session_state.settings.get("ai_provider", provider_list[0])
        ai_prov_index = provider_list.index(saved_ai_prov) if saved_ai_prov in provider_list else 0
        
        selected_ai_provider = st.selectbox(
            "Proveedor de Inteligencia Artificial:",
            provider_list,
            index=ai_prov_index
        )
        
        prov_info = AI_PROVIDERS[selected_ai_provider]
        recommended_model = prov_info.get("default_model", "")
        
        # Entrada de API Key
        cfg_ai_api_key = st.text_input(
            f"Introduce tu clave (API Key):",
            value=st.session_state.settings.get("ai_api_key", ""),
            type="password",
            help=f"Clave provista por {selected_ai_provider.split('(')[0].strip()}."
        )

        # Enlace rápido y nota amigable
        if prov_info.get("key_url"):
            st.markdown(f"👉 **[Haz clic aquí para obtener tu clave en {selected_ai_provider.split('(')[0].strip()}]({prov_info['key_url']})**")
        st.caption(f"ℹ️ {prov_info['note']}")

        # Opciones avanzadas ocultas para no abrumar al usuario
        with st.expander("⚙️ Opciones avanzadas de modelo (Opcional)"):
            cfg_model = st.text_input(
                "Modelo seleccionado automáticamente:",
                value=st.session_state.settings.get("ai_model", recommended_model),
                help="El sistema ya ha elegido el mejor modelo por ti. No necesitas cambiarlo."
            )
            cfg_base_url = st.text_input(
                "Base URL (solo para servidores locales / Ollama):",
                value=st.session_state.settings.get("ai_base_url", ""),
                placeholder="http://localhost:11434"
            )

        st.markdown("---")
        st.markdown("### 📝 Propuesta de Valor Predeterminada")
        cfg_default_vp = st.text_area(
            "Tu Propuesta de Valor por defecto:",
            value=st.session_state.settings.get("default_value_prop", ""),
            height=90
        )

    with col_mail:
        st.markdown("### ✉️ Cuenta de Correo (Para Envíos)")
        
        mail_providers = list(EMAIL_PROVIDERS.keys())
        saved_mail_prov = st.session_state.settings.get("email_provider", "Gmail")
        mail_idx = mail_providers.index(saved_mail_prov) if saved_mail_prov in mail_providers else 0
        
        cfg_provider = st.selectbox("Proveedor de Correo:", mail_providers, index=mail_idx)
        mail_info = EMAIL_PROVIDERS[cfg_provider]
        st.caption(f"ℹ️ {mail_info['note']}")

        cfg_sender_name = st.text_input(
            "Tu Nombre o Empresa (Remitente visible):",
            value=st.session_state.settings.get("email_sender_name", ""),
            placeholder="Ej: Carlos Gómez - Asesor Comercial"
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
            help="Para Gmail/Yahoo usa una Contraseña de Aplicación de 16 caracteres."
        )

        cfg_signature = st.text_area(
            "Firma del Correo (Se añadirá automáticamente al final de tus emails):",
            value=st.session_state.settings.get("email_signature", ""),
            placeholder="Ej:\nUn saludo,\nCarlos Gómez | Asesor Comercial\nTel: +34 600 00 00 00\ncalendly.com/miempresa",
            height=90
        )

        cfg_bcc_self = st.checkbox(
            "Enviarme una copia oculta (BCC) a mi propio correo de cada email enviado",
            value=st.session_state.settings.get("email_bcc_self", False),
            help="Ideal para tener constancia en tu bandeja de entrada de los correos que envías a prospectos."
        )

        if cfg_provider == "Gmail":
            with st.expander("🔒 ¿Cómo crear una Contraseña de Aplicación en Gmail?"):
                st.markdown("""
                1. Ve a **[myaccount.google.com/security](https://myaccount.google.com/security)**.
                2. Activa la **Verificación en dos pasos** si no la tienes.
                3. En el buscador superior pon **'Contraseñas de aplicaciones'**.
                4. Crea una con nombre 'Prospecta' y pega la clave de 16 letras aquí.
                """)

        if cfg_provider == "Personalizado (SMTP)":
            cfg_smtp_host = st.text_input("Servidor SMTP:", value=st.session_state.settings.get("smtp_host", ""))
            cfg_smtp_port = st.number_input("Puerto SMTP:", value=st.session_state.settings.get("smtp_port", 587), step=1)
            cfg_smtp_tls = st.checkbox("Usar STARTTLS", value=st.session_state.settings.get("smtp_tls", True))
        else:
            cfg_smtp_host = mail_info["host"]
            cfg_smtp_port = mail_info["port"]
            cfg_smtp_tls = mail_info["use_tls"]

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
            "ai_provider": selected_ai_provider,
            "ai_model": cfg_model.strip(),
            "ai_api_key": cfg_ai_api_key.strip(),
            "ai_base_url": cfg_base_url.strip(),
            "email_provider": cfg_provider,
            "email_user": cfg_email_user.strip(),
            "email_password": cfg_email_pass.strip(),
            "email_sender_name": cfg_sender_name.strip(),
            "email_signature": cfg_signature.strip(),
            "email_bcc_self": cfg_bcc_self,
            "smtp_host": cfg_smtp_host,
            "smtp_port": int(cfg_smtp_port),
            "smtp_tls": cfg_smtp_tls,
            "default_value_prop": cfg_default_vp.strip()
        }
        st.session_state.settings.update(new_settings)
        if save_user_settings(new_settings):
            st.success("✅ ¡Configuración guardada correctamente! Todos tus ajustes están activos.")
            st.rerun()
        else:
            st.warning("Ajustes aplicados en la sesión actual.")

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

if st.session_state.sent_logs:
    st.markdown("---")
    st.subheader("📬 Correos Enviados en esta Sesión")
    for log in st.session_state.sent_logs:
        st.write(f"• **{log['empresa']}** ({log['email']}) — Enviado a las {log['fecha']}")

st.markdown("---")
st.caption("Prospecta AI Multi-IA | Compatible con Google Gemini, OpenAI, Claude, DeepSeek, Groq y Mistral")
