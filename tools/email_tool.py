import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Tuple, Dict, Any, Optional
from crewai.tools import tool

# Proveedores de correo preconfigurados
EMAIL_PROVIDERS = {
    "Gmail": {
        "host": "smtp.gmail.com",
        "port": 587,
        "use_tls": True,
        "note": "Usa tu dirección de Gmail y una 'Contraseña de Aplicación' de 16 letras generada en tu cuenta de Google."
    },
    "Outlook / Hotmail": {
        "host": "smtp.office365.com",
        "port": 587,
        "use_tls": True,
        "note": "Usa tu cuenta de Outlook/Hotmail y tu contraseña o contraseña de aplicación."
    },
    "Yahoo": {
        "host": "smtp.mail.yahoo.com",
        "port": 587,
        "use_tls": True,
        "note": "Requiere una contraseña de aplicación generada en la seguridad de Yahoo."
    },
    "Personalizado (SMTP)": {
        "host": "",
        "port": 587,
        "use_tls": True,
        "note": "Configura el servidor SMTP de tu empresa o proveedor de hosting."
    }
}

def send_email_smtp(
    to_email: str,
    subject: str,
    body: str,
    smtp_config: Dict[str, Any],
    is_html: bool = False
) -> Tuple[bool, str]:
    """
    Envía un correo electrónico utilizando los datos del servidor SMTP provistos.
    Devuelve (éxito: bool, mensaje: str).
    """
    host = smtp_config.get("host", "").strip()
    port = int(smtp_config.get("port", 587))
    user = smtp_config.get("user", "").strip()
    password = smtp_config.get("password", "").strip()
    use_tls = smtp_config.get("use_tls", True)
    sender_name = smtp_config.get("sender_name", "").strip()

    if not host or not user or not password:
        return False, "Faltan credenciales del servidor de correo (servidor, usuario o contraseña)."

    if not to_email or "@" not in to_email:
        return False, f"La dirección de correo destinatario '{to_email}' no es válida."

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{sender_name} <{user}>" if sender_name else user
        msg["To"] = to_email

        # Adjuntar cuerpo (texto plano o html)
        subtype = "html" if is_html else "plain"
        msg.attach(MIMEText(body, subtype, "utf-8"))

        if port == 465:
            # Conexión SSL directa
            with smtplib.SMTP_SSL(host, port, timeout=15) as server:
                server.login(user, password)
                server.sendmail(user, [to_email], msg.as_string())
        else:
            # Conexión STARTTLS (puerto 587 común)
            with smtplib.SMTP(host, port, timeout=15) as server:
                server.ehlo()
                if use_tls:
                    server.starttls()
                    server.ehlo()
                server.login(user, password)
                server.sendmail(user, [to_email], msg.as_string())

        return True, f"Correo enviado exitosamente a {to_email}"
    except smtplib.SMTPAuthenticationError:
        return False, "Error de autenticación: El correo o la contraseña son incorrectos. Si usas Gmail, asegúrate de usar una 'Contraseña de Aplicación'."
    except Exception as e:
        return False, f"Error al enviar el correo: {str(e)}"


def test_smtp_connection(smtp_config: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Verifica la conexión y autenticación con el servidor SMTP sin enviar ningún correo.
    """
    host = smtp_config.get("host", "").strip()
    port = int(smtp_config.get("port", 587))
    user = smtp_config.get("user", "").strip()
    password = smtp_config.get("password", "").strip()
    use_tls = smtp_config.get("use_tls", True)

    if not host or not user or not password:
        return False, "Por favor completa el servidor, tu correo y la contraseña."

    try:
        if port == 465:
            with smtplib.SMTP_SSL(host, port, timeout=10) as server:
                server.login(user, password)
        else:
            with smtplib.SMTP(host, port, timeout=10) as server:
                server.ehlo()
                if use_tls:
                    server.starttls()
                    server.ehlo()
                server.login(user, password)
        return True, "¡Conexión exitosa! Las credenciales de correo son válidas."
    except smtplib.SMTPAuthenticationError:
        return False, "Error de autenticación: Correo o contraseña incorrectos. Revisa si necesitas una 'Contraseña de Aplicación'."
    except Exception as e:
        return False, f"Fallo al conectar con {host}:{port} -> {str(e)}"
