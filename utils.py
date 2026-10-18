import os
import json
import re
from typing import Dict, Any, List

SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "user_settings.json")

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
    "smtp_host": "smtp.gmail.com",
    "smtp_port": 587,
    "smtp_tls": True,
    # Textos
    "default_value_prop": "Automatizamos procesos y prospección comercial con Inteligencia Artificial.",
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
