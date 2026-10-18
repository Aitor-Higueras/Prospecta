import os
import json
import re
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional

from urllib.parse import quote_plus

SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "user_settings.json")
CONTACTED_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "contacted_leads.json")

# Lista completa de proveedores de IA compatibles vía CrewAI / LiteLLM
AI_PROVIDERS = {
    "Google Gemini (Recomendado / Gratis)": {
        "prefix": "gemini",
        "default_model": "gemini/gemini-2.5-flash",
        "models": [
            "gemini/gemini-2.5-flash",
            "gemini/gemini-1.5-flash",
            "gemini/gemini-2.0-flash",
            "gemini/gemini-1.5-pro"
        ],
        "env_var": "GOOGLE_API_KEY",
        "key_url": "https://aistudio.google.com/app/apikey",
        "free_tier": True,
        "note": "Totalmente gratis con tu cuenta de Google en AI Studio. Muy rápido y sin tarjeta de crédito."
    },
    "OpenAI (ChatGPT)": {
        "prefix": "openai",
        "default_model": "openai/gpt-4o-mini",
        "models": [
            "openai/gpt-4o-mini",
            "openai/gpt-4o",
            "openai/o3-mini"
        ],
        "env_var": "OPENAI_API_KEY",
        "key_url": "https://platform.openai.com/api-keys",
        "free_tier": False,
        "note": "Usa tu cuenta de desarrollador de OpenAI. gpt-4o-mini es ultra rápido y cuesta fracciones de céntimo."
    },
    "DeepSeek": {
        "prefix": "deepseek",
        "default_model": "deepseek/deepseek-chat",
        "models": [
            "deepseek/deepseek-chat",
            "deepseek/deepseek-reasoner"
        ],
        "env_var": "DEEPSEEK_API_KEY",
        "key_url": "https://platform.deepseek.com/api_keys",
        "free_tier": False,
        "note": "Excelente calidad de razonamiento y redacción comercial a uno de los precios más bajos del mercado."
    },
    "Anthropic (Claude)": {
        "prefix": "anthropic",
        "default_model": "anthropic/claude-3-5-haiku-20241022",
        "models": [
            "anthropic/claude-3-5-haiku-20241022",
            "anthropic/claude-3-5-sonnet-20241022"
        ],
        "env_var": "ANTHROPIC_API_KEY",
        "key_url": "https://console.anthropic.com/settings/keys",
        "free_tier": False,
        "note": "Claude es el rey de la redacción humana de emails sin sonar a robot."
    },
    "Groq (Llama ultra rápida)": {
        "prefix": "groq",
        "default_model": "groq/llama-3.3-70b-versatile",
        "models": [
            "groq/llama-3.3-70b-versatile",
            "groq/llama-3.1-8b-instant"
        ],
        "env_var": "GROQ_API_KEY",
        "key_url": "https://console.groq.com/keys",
        "free_tier": True,
        "note": "Velocidad extrema de procesamiento (más de 300 tokens/segundo). Incluye plan gratuito."
    },
    "Mistral AI": {
        "prefix": "mistral",
        "default_model": "mistral/mistral-small-latest",
        "models": [
            "mistral/mistral-small-latest",
            "mistral/mistral-large-latest"
        ],
        "env_var": "MISTRAL_API_KEY",
        "key_url": "https://console.mistral.ai/api-keys",
        "free_tier": False,
        "note": "Modelo europeo con excelente rendimiento y privacidad."
    },
    "Personalizado (Ollama / Proxy / Otro)": {
        "prefix": "custom",
        "default_model": "ollama/llama3",
        "models": ["ollama/llama3", "custom"],
        "env_var": "CUSTOM_API_KEY",
        "key_url": "",
        "free_tier": True,
        "note": "Configura cualquier modelo compatible con LiteLLM y tu propia URL de servidor."
    }
}

DEFAULT_SETTINGS = {
    "ai_provider": "Google Gemini (Recomendado / Gratis)",
    "ai_model": "gemini/gemini-2.5-flash",
    "ai_api_key": "",
    "ai_base_url": "",
    # Compatibilidad previa
    "google_api_key": "",
    "groq_api_key": "",
    # Correo
    "email_provider": "Gmail",
    "email_user": "",
    "email_password": "",
    "email_sender_name": "",
    "email_signature": "",
    "email_bcc_self": False,
    "smtp_host": "smtp.gmail.com",
    "smtp_port": 587,
    "smtp_tls": True,
    # Base de Datos Cloud (Google Sheets)
    "gsheets_url": "",
    # Textos
    "default_value_prop": "Servicio profesional de limpieza y mantenimiento para comunidades de propietarios y garajes. Garantizamos sustitución inmediata en menos de 2h ante bajas, supervisión periódica con fotos y presupuestos cerrados en 24h para tus juntas de vecinos.",
    "default_tone": "Directo hacia el ROI y Profesional"
}

def load_user_settings() -> Dict[str, Any]:
    """Carga los ajustes del usuario guardados localmente, o los valores por defecto."""
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                settings = DEFAULT_SETTINGS.copy()
                settings.update(saved)
                # Migración: si tenía google_api_key pero no ai_api_key
                if not settings.get("ai_api_key") and settings.get("google_api_key"):
                    settings["ai_api_key"] = settings["google_api_key"]
                return settings
        except Exception:
            pass
    return DEFAULT_SETTINGS.copy()

def save_user_settings(settings: Dict[str, Any]) -> bool:
    """Guarda las configuraciones en un archivo json local para persistencia segura."""
    try:
        current = load_user_settings()
        current.update(settings)
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(current, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error guardando user_settings: {e}")
        return False

def extract_email_address(text: str) -> str:
    """Intenta extraer la primera dirección de email válida en un texto."""
    if not text:
        return ""
    matches = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
    return matches[0] if matches else ""

def parse_prospecting_output(raw_text: str) -> List[Dict[str, Any]]:
    """
    Parsea la salida de texto de la Crew para extraer cada Lead con sus datos:
    Empresa, Contacto, Email, Asunto y Cuerpo del email.
    """
    if not raw_text or not isinstance(raw_text, str):
        return []

    leads = []
    sections = re.split(r'(?i)(?:---+|\bFICHA DEL LEAD\b)', raw_text)
    
    for sec in sections:
        sec = sec.strip()
        if not sec:
            continue
        
        if "asunto:" in sec.lower() or "empresa:" in sec.lower():
            lead_info = {
                "empresa": "Prospecto",
                "contacto": "",
                "email_destinatario": "",
                "direccion": "",
                "asunto": "Oportunidad de colaboración estratégica",
                "cuerpo": "",
                "raw": sec
            }
            
            emp_match = re.search(r'(?i)(?:Empresa|Nombre)[:\s]+([^\n\r]+)', sec)
            if emp_match:
                lead_info["empresa"] = emp_match.group(1).strip(" -*#[]")
                
            cont_match = re.search(r'(?i)(?:Contacto|Email|Correo)[:\s]+([^\n\r]+)', sec)
            if cont_match:
                lead_info["contacto"] = cont_match.group(1).strip(" -*#[]")
                found_email = extract_email_address(lead_info["contacto"])
                if found_email:
                    lead_info["email_destinatario"] = found_email
            
            if not lead_info["email_destinatario"]:
                lead_info["email_destinatario"] = extract_email_address(sec)

            asunto_match = re.search(r'(?i)(?:Asunto|Subject)[:\s]+([^\n\r]+)', sec)
            if asunto_match:
                lead_info["asunto"] = asunto_match.group(1).strip(" -*#[]")

            cuerpo_match = re.search(r'(?i)(?:Cuerpo|Body)[:\s]+([\s\S]+)', sec)
            if cuerpo_match:
                lead_info["cuerpo"] = cuerpo_match.group(1).strip()
            else:
                if asunto_match:
                    lead_info["cuerpo"] = sec[asunto_match.end():].strip()
                else:
                    lead_info["cuerpo"] = sec

            lead_info["cuerpo"] = re.sub(r'^(?:Email:|---|\n)+', '', lead_info["cuerpo"]).strip()
            leads.append(lead_info)

    if not leads and raw_text.strip():
        leads.append({
            "empresa": "Lead Prospectado",
            "contacto": "",
            "email_destinatario": extract_email_address(raw_text),
            "direccion": "",
            "asunto": "Propuesta personalizada",
            "cuerpo": raw_text.strip(),
            "raw": raw_text
        })

    return leads

def leads_to_dataframe(leads: List[Dict[str, Any]]):
    """Convierte la lista de prospectos en un DataFrame de pandas para exportar a Excel o CSV."""
    import pandas as pd
    
    rows = []
    for i, lead in enumerate(leads):
        rows.append({
            "Nº": i + 1,
            "Empresa": lead.get("empresa", ""),
            "Email Destinatario": lead.get("email_destinatario", ""),
            "Contacto / Teléfono": lead.get("contacto", ""),
            "Dirección": lead.get("direccion", ""),
            "Asunto del Email": lead.get("asunto", ""),
            "Cuerpo del Mensaje": lead.get("cuerpo", "")
        })
    return pd.DataFrame(rows)

def load_contacted_leads() -> List[Dict[str, Any]]:
    """Carga la lista histórica de empresas y emails ya contactados."""
    if os.path.exists(CONTACTED_FILE):
        try:
            with open(CONTACTED_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except Exception:
            return []
    return []

def sync_lead_to_gsheets(data_dict: Dict[str, Any], gsheets_url: str) -> bool:
    """Envía un registro a Google Sheets mediante la URL de Google Apps Script."""
    if not gsheets_url or not gsheets_url.startswith("http"):
        return False
    try:
        import requests
        requests.post(gsheets_url, json=data_dict, timeout=5)
        return True
    except Exception as e:
        print(f"Error sincronizando con Google Sheets: {e}")
        return False

def save_contacted_lead(
    empresa: str,
    email: str,
    asunto: str = "",
    nicho: str = "",
    estado: str = "Enviado",
    notas: str = "",
    gsheets_url: str = ""
) -> bool:
    """Registra de forma persistente un lead (en local y en Google Sheets si está configurado)."""
    try:
        leads = load_contacted_leads()
        new_entry = {
            "empresa": empresa.strip(),
            "email": email.strip().lower(),
            "asunto": asunto.strip(),
            "nicho": nicho.strip(),
            "estado": estado.strip() if estado else "Enviado",
            "notas": notas.strip() if notas else "",
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        # Evitar duplicados en el registro
        leads = [l for l in leads if not (l.get("email") == new_entry["email"] and l.get("empresa", "").lower() == new_entry["empresa"].lower())]
        leads.insert(0, new_entry)
        with open(CONTACTED_FILE, "w", encoding="utf-8") as f:
            json.dump(leads, f, indent=4, ensure_ascii=False)
            
        # Sincronizar en tiempo real con Google Sheets si existe URL
        if gsheets_url:
            sync_lead_to_gsheets(new_entry, gsheets_url)
            
        return True
    except Exception as e:
        print(f"Error guardando contacted_lead: {e}")
        return False

def update_lead_status_and_notes(email: str, empresa: str, nuevo_estado: str, nuevas_notas: str, gsheets_url: str = "") -> bool:
    """Actualiza las notas o el estado comercial de una empresa."""
    try:
        leads = load_contacted_leads()
        updated = False
        target_entry = None
        for l in leads:
            if l.get("email") == email and l.get("empresa") == empresa:
                l["estado"] = nuevo_estado
                l["notas"] = nuevas_notas
                updated = True
                target_entry = l.copy()
                break
        if updated:
            with open(CONTACTED_FILE, "w", encoding="utf-8") as f:
                json.dump(leads, f, indent=4, ensure_ascii=False)
            if gsheets_url and target_entry:
                sync_lead_to_gsheets(target_entry, gsheets_url)
        return updated
    except Exception as e:
        print(f"Error actualizando notas del lead: {e}")
        return False

def remove_contacted_lead(email: str, empresa: str) -> bool:
    """Elimina una empresa de la lista de contactados para permitir volver a contactarla."""
    try:
        leads = load_contacted_leads()
        leads = [l for l in leads if not (l.get("email") == email and l.get("empresa") == empresa)]
        with open(CONTACTED_FILE, "w", encoding="utf-8") as f:
            json.dump(leads, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        return False

def is_lead_already_contacted(empresa: str, email: str, contacted_list: List[Dict[str, Any]]) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Comprueba si una empresa o email ya ha sido contactada previamente."""
    clean_empresa = empresa.strip().lower() if empresa else ""
    clean_email = email.strip().lower() if email else ""
    
    for c in contacted_list:
        c_empresa = c.get("empresa", "").strip().lower()
        c_email = c.get("email", "").strip().lower()
        
        # Coincidencia por email exacto
        if clean_email and clean_email == c_email:
            return True, c
        
        # Coincidencia por nombre de empresa (si tiene más de 3 letras)
        if clean_empresa and len(clean_empresa) > 3 and c_empresa and len(c_empresa) > 3:
            if clean_empresa == c_empresa or clean_empresa in c_empresa or c_empresa in clean_empresa:
                return True, c
                
    return False, None

def get_maps_search_url(empresa: str, direccion: str = "") -> str:
    """Genera la URL para buscar la empresa o su oficina en Google Maps."""
    query = f"{empresa} {direccion}".strip()
    return f"https://www.google.com/maps/search/?api=1&query={quote_plus(query)}"

def get_google_search_url(empresa: str) -> str:
    """Genera una búsqueda en Google orientada a encontrar al Administrador de Fincas colegiado o LinkedIn."""
    return f"https://www.google.com/search?q={quote_plus('Administrador de fincas ' + empresa)}"
