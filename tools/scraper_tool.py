import re
import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from crewai.tools import tool

EMAIL_REGEX = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
PHONE_REGEX = re.compile(r'(?:\+34\s?|0034\s?)?(?:[6789]\d{2}[\s.-]?\d{3}[\s.-]?\d{3}|[6789]\d{1}[\s.-]?\d{3}[\s.-]?\d{2}[\s.-]?\d{2})')

# Extensiones a ignorar en enlaces
IGNORE_EXTS = ('.png', '.jpg', '.jpeg', '.gif', '.pdf', '.css', '.js', '.zip', '.svg', '.webp')

def find_emails_in_soup(soup: BeautifulSoup) -> set:
    """Extrae emails de enlaces mailto y del texto."""
    emails = set()
    # 1. Enlaces mailto:
    for a in soup.find_all('a', href=True):
        href = a['href'].strip()
        if href.lower().startswith('mailto:'):
            clean_email = href.split('?')[0].replace('mailto:', '').strip()
            if '@' in clean_email and '.' in clean_email:
                emails.add(clean_email.lower())
    
    # 2. Regex en el texto visible
    text = soup.get_text(separator=' ', strip=True)
    for match in EMAIL_REGEX.findall(text):
        # Filtrar extensiones falsas comunes como ejemplo@2x.png
        if not match.lower().endswith(IGNORE_EXTS):
            emails.add(match.lower())
            
    return emails

def find_contact_links(soup: BeautifulSoup, base_url: str) -> list:
    """Encuentra enlaces que apunten a páginas de contacto, aviso legal o sobre nosotros."""
    contact_keywords = ('contacto', 'contact', 'aviso-legal', 'legal', 'nosotros', 'quienes-somos', 'sobre-nosotros')
    found_urls = []
    base_domain = urlparse(base_url).netloc
    
    for a in soup.find_all('a', href=True):
        href = a['href'].strip()
        link_text = a.get_text().strip().lower()
        
        # Comprobar si el texto o href contiene palabras de contacto
        if any(kw in href.lower() or kw in link_text for kw in contact_keywords):
            full_url = urljoin(base_url, href)
            # Solo navegar si pertenece al mismo dominio
            if urlparse(full_url).netloc == base_domain and full_url not in found_urls:
                found_urls.append(full_url)
                if len(found_urls) >= 2:
                    break
    return found_urls

@tool("Scrape Website")
def scrape_website(website_url: str) -> str:
    """Útil para leer el contenido principal de una página web y extraer automáticamente
    correos electrónicos de contacto, teléfonos y datos de la empresa.
    El input debe ser una URL válida (ej: 'https://ejemplo.com')."""
    if not website_url.startswith('http'):
        website_url = 'https://' + website_url

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                      'AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/120.0.0.0 Safari/537.36'
    }

    try:
        response = requests.get(website_url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 1. Extraer emails de la página principal
        extracted_emails = find_emails_in_soup(soup)
        
        # 2. Si no hay emails en la portada, buscar en página de /contacto o /aviso-legal
        if not extracted_emails:
            contact_urls = find_contact_links(soup, website_url)
            for c_url in contact_urls:
                try:
                    c_resp = requests.get(c_url, headers=headers, timeout=8)
                    if c_resp.status_code == 200:
                        c_soup = BeautifulSoup(c_resp.content, 'html.parser')
                        c_emails = find_emails_in_soup(c_soup)
                        if c_emails:
                            extracted_emails.update(c_emails)
                            break
                except Exception:
                    continue

        # 3. Extraer teléfonos
        raw_text = soup.get_text(separator=' ', strip=True)
        phones = list(set(PHONE_REGEX.findall(raw_text)))[:3]

        # 4. Limpiar tags problemáticos para el texto principal
        for tag in soup(["script", "style", "noscript", "meta", "svg", "header", "footer"]):
            tag.extract()

        clean_text = soup.get_text(separator=' ', strip=True)
        
        # Formatear salida con datos de contacto destacados
        contact_header = "=== DATOS DE CONTACTO DETECTADOS ===\n"
        contact_header += f"Emails de contacto: {', '.join(extracted_emails) if extracted_emails else 'No encontrado directamente (buscar en redes o directorios)'}\n"
        contact_header += f"Teléfonos: {', '.join(phones) if phones else 'No detectado'}\n"
        contact_header += "=== CONTENIDO PRINCIPAL DE LA WEB ===\n"

        return contact_header + clean_text[:4000]

    except requests.exceptions.Timeout:
        return f"Error de Timeout intentando acceder a la web: {website_url}"
    except Exception as e:
        return f"Error al extraer la información de la web {website_url}: {e}"
