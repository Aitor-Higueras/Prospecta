import requests
from bs4 import BeautifulSoup
from crewai.tools import tool

@tool("Scrape Website")
def scrape_website(website_url: str) -> str:
    """Útil para leer el texto principal de una página web (por ejemplo, la URL de una empresa).
    El input debe ser una URL válida completa, incluyendo el prefijo http o https (ejemplo: 'https://www.ejemplo.com' o 'http://ejemplo.com').
    Nunca pases dominios sueltos como 'ejemplo.com' sin el protocolo."""
    # Se añade autocompletado de https en caso de que el modelo solo envíe el texto plano
    if not website_url.startswith('http'):
        website_url = 'https://' + website_url

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(website_url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        # Eliminar tags problemáticos para el text (scripts, styles, head)
        for script in soup(["script", "style", "noscript", "meta"]):
            script.extract()

        # Extraemos texto limpio
        text = soup.get_text(separator=' ', strip=True)
        
        # Limitamos la lectura de páginas excesivamente grandes para no colapsar tokens
        return text[:5000]
        
    except requests.exceptions.Timeout:
        return f"Error de Timeout intentando acceder a la web: {website_url}"
    except Exception as e:
        return f"Error al extraer la información de la web {website_url}: {e}"
