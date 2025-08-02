import random
import requests
import time
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from langchain_openai import OpenAI
from matplotlib.dates import relativedelta
from tennisAgents.dataflows.config import get_config


def fetch_news(query: str, curr_date: str) -> str:
    """
    Consulta el feed RSS de Google News para obtener noticias sobre un tema específico.
    """
    query_encoded = query.replace(" ", "+")

    start_date = datetime.strptime(curr_date, "%Y-%m-%d")
    before = start_date - relativedelta(days=7)
    before_str = before.strftime("%Y-%m-%d")

    # Obtener resultados del feed RSS
    news_results = getNewsData(query_encoded)

    if not news_results:
        return ""

    # Construir texto de salida
    news_str = ""
    for news in news_results:
        news_str += (
            f"### {news['title']} (source: {news['source']})\n\n"
            f"{news['snippet']}\n\n"
            f"Link: {news['link']}\n\n"
        )

    result = f"## {query} Google News RSS, desde {before_str} hasta {curr_date}:\n\n{news_str}"
    return result


def getNewsData(query: str) -> list:
    """
    Obtiene noticias desde el feed RSS de Google News para una query dada.
    """
    
    rss_url = f"https://news.google.com/rss/search?q={query}&hl=es&gl=ES&ceid=ES:es"
    
    try:
        time.sleep(random.uniform(1, 3))  # retraso aleatorio para evitar bloqueos
        response = requests.get(rss_url, headers={"User-Agent": "Mozilla/5.0"})

        if response.status_code != 200:
            return []
        
        soup = BeautifulSoup(response.content, "xml")
        items = soup.find_all("item")

        
        news_results = []
        for i, item in enumerate(items):
            try:
                title = item.title.text
                link = item.link.text
                snippet = item.description.text
                source = item.source.text if item.source else "Desconocido"
                pub_date = item.pubDate.text if item.pubDate else "Sin fecha"

                news_results.append({
                    "title": title,
                    "link": link,
                    "snippet": snippet,
                    "date": pub_date,
                    "source": source
                })
            except Exception as e:
                continue

        return news_results
    
    except Exception as e:
        return []
