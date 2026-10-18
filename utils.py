import os
import json
import re
from typing import Dict, Any, List

SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "user_settings.json")

DEFAULT_SETTINGS = {
    "google_api_key": "",
    "groq_api_key": "",
    "email_provider": "Gmail",
    "email_user": "",
    "email_password": "",
    "email_sender_name": "",
    "smtp_host": "smtp.gmail.com",
    "smtp_port": 587,
    "smtp_tls": True,
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
    # Dividir por bloques de 'FICHA DEL LEAD' o separadores '---'
    # Intentamos separar por 'FICHA DEL LEAD'
    sections = re.split(r'(?i)(?:---+|\bFICHA DEL LEAD\b)', raw_text)
    
    current_block = ""
    for sec in sections:
        sec = sec.strip()
        if not sec:
            continue
        
        # Si contiene 'Asunto:' o 'Email:', probablemente es un lead
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
            
            # Buscar Empresa
            emp_match = re.search(r'(?i)(?:Empresa|Nombre)[:\s]+([^\n\r]+)', sec)
            if emp_match:
                lead_info["empresa"] = emp_match.group(1).strip(" -*#[]")
                
            # Buscar Contacto o Email
            cont_match = re.search(r'(?i)(?:Contacto|Email|Correo)[:\s]+([^\n\r]+)', sec)
            if cont_match:
                lead_info["contacto"] = cont_match.group(1).strip(" -*#[]")
                found_email = extract_email_address(lead_info["contacto"])
                if found_email:
                    lead_info["email_destinatario"] = found_email
            
            # Si no encontró email en contacto, buscar en todo el bloque
            if not lead_info["email_destinatario"]:
                lead_info["email_destinatario"] = extract_email_address(sec)

            # Buscar Asunto
            asunto_match = re.search(r'(?i)(?:Asunto|Subject)[:\s]+([^\n\r]+)', sec)
            if asunto_match:
                lead_info["asunto"] = asunto_match.group(1).strip(" -*#[]")

            # Buscar Cuerpo
            cuerpo_match = re.search(r'(?i)(?:Cuerpo|Body)[:\s]+([\s\S]+)', sec)
            if cuerpo_match:
                lead_info["cuerpo"] = cuerpo_match.group(1).strip()
            else:
                # Si no tiene etiqueta 'Cuerpo:', tomamos el texto posterior al asunto
                if asunto_match:
                    lead_info["cuerpo"] = sec[asunto_match.end():].strip()
                else:
                    lead_info["cuerpo"] = sec

            # Limpiar posibles delimitadores markdown del cuerpo
            lead_info["cuerpo"] = re.sub(r'^(?:Email:|---|\n)+', '', lead_info["cuerpo"]).strip()

            leads.append(lead_info)

    # Si el regex no encontró bloques estructurados, devolver 1 lead con el contenido completo
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
