import requests
import os
from datetime import datetime, timedelta


def fetch_news(query: str, curr_date: str) -> list:
    """
    Consulta la API de NewsAPI para obtener noticias sobre un tema específico.
    """
    # Get API key from environment variable
    NEWS_API_KEY = os.getenv("NEWS_API_KEY")
    
    if not NEWS_API_KEY:
        # Return mock data if API key is not available
        return _get_mock_news(query, curr_date)
    
    base_url = "https://newsapi.org/v2/everything"

    # Configura rango de fechas
    from_date = curr_date
    to_date = curr_date

    params = {
        "q": query,
        "from": from_date,
        "to": to_date,
        "language": "es",
        "sortBy": "relevancy",
        "pageSize": 5,
        "apiKey": NEWS_API_KEY,
    }

    try:
        response = requests.get(base_url, params=params)
        data = response.json()

        if response.status_code != 200 or data.get("status") != "ok":
            print(f"[ERROR] No se pudo obtener noticias: {data}")
            return _get_mock_news(query, curr_date)

        noticias = []
        for article in data["articles"]:
            noticias.append({
                "title": article["title"],
                "description": article.get("description", ""),
                "url": article["url"]
            })

        return noticias
    except Exception as e:
        print(f"[ERROR] Error al obtener noticias: {e}")
        return _get_mock_news(query, curr_date)


def _get_mock_news(query: str, curr_date: str) -> list:
    """
    Genera noticias simuladas cuando la API no está disponible.
    """
    mock_news = [
        {
            "title": f"Noticias simuladas sobre {query}",
            "description": f"Información simulada sobre {query} para la fecha {curr_date}. Esta es una respuesta de prueba cuando la API de noticias no está disponible.",
            "url": "https://example.com/mock-news"
        },
        {
            "title": f"Análisis de tenis - {query}",
            "description": f"Análisis detallado sobre {query} y su rendimiento reciente. Datos simulados para propósitos de prueba.",
            "url": "https://example.com/tennis-analysis"
        },
        {
            "title": f"Actualizaciones del circuito - {query}",
            "description": f"Últimas actualizaciones sobre {query} en el circuito profesional. Información simulada.",
            "url": "https://example.com/circuit-updates"
        }
    ]
    
    return mock_news
