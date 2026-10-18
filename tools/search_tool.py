import os
from crewai.tools import tool
from langchain_community.tools import DuckDuckGoSearchRun

@tool("Search Internet")
def search_internet(query: str) -> str:
    """Útil para buscar información en internet sobre un nicho o empresa usando DuckDuckGo. 
    El input debe ser una consulta de búsqueda clara, como 'mejores agencias de software en madrid'."""
    try:
        search = DuckDuckGoSearchRun()
        result = search.run(query)
        return result
    except Exception as e:
        return f"Error al buscar en internet: {e}"
