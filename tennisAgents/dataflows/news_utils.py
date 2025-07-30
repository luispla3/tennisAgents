import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
load_dotenv()  # Carga variables desde .env al entorno



def fetch_news(query: str, curr_date: str) -> list:
    """
    Consulta la API de NewsAPI para obtener noticias sobre un tema específico.
    """
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

    response = requests.get(base_url, params=params)
    data = response.json()

    if response.status_code != 200 or data.get("status") != "ok":
        print(f"[ERROR] No se pudo obtener noticias: {data}")
        return []

    noticias = []
    for article in data["articles"]:
        noticias.append({
            "title": article["title"],
            "description": article.get("description", ""),
            "url": article["url"]
        })

    return noticias
