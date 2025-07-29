# falta actualizar
from typing import Annotated, Dict
from .reddit_utils import fetch_top_from_category
from .yfin_utils import *
from .stockstats_utils import *
from .googlenews_utils import *
from .finnhub_utils import get_data_in_range
from dateutil.relativedelta import relativedelta
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import json
import os
import pandas as pd
from tqdm import tqdm
import yfinance as yf
from openai import OpenAI
from .config import get_config, set_config, DATA_DIR

# necesarias
import random
import requests
from datetime import datetime, timedelta

from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import quote

import praw
import openai


def get_tennis_news_openai(
    query: str,
    curr_date: str,
) -> str:
    """
    Obtiene las últimas noticias de tenis usando OpenAI.
    Args:
        query (str): Consulta de noticias de tenis.
        curr_date (str): Fecha en formato yyyy-mm-dd.
    Returns:
        str: Noticias encontradas en formato texto.
    """
    client = OpenAI()
    prompt = (
        f"Busca y resume las noticias más relevantes sobre tenis relacionadas con '{query}' "
        f"hasta la fecha {curr_date}. Devuelve un resumen breve y claro en español."
    )
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=500,
        temperature=0.7,
    )
    return response.choices[0].message.content.strip()  

def get_google_news(
    query: str,
    curr_date: str,
) -> str:
    """
    Obtiene noticias de Google News sobre tenis.
    Args:
        query (str): Consulta para buscar en Google News.
        curr_date (str): Fecha en formato yyyy-mm-dd.
    Returns:
        str: Noticias encontradas en formato texto.
    """
    news = getNewsData(query=query, date=curr_date)
    if not news:
        return "No se encontraron noticias relevantes en Google News para esa consulta y fecha."
    return news


def getNewsData(query: str, date: str, language: str = "es", max_articles: int = 5) -> str:
    """
    Recupera noticias relacionadas con tenis usando NewsAPI.org.
    Args:
        query (str): Término de búsqueda.
        date (str): Fecha en formato yyyy-mm-dd.
        language (str): Idioma de las noticias (por defecto 'es').
        max_articles (int): Máximo número de artículos a devolver.
    Returns:
        str: Cadena de texto con los titulares y descripciones de noticias.
    """
    # Convertir la fecha para usar un rango (día anterior a la fecha actual)
    from_date = (datetime.strptime(date, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
    to_date = date

    url = "https://newsapi.org/v2/everything"
    params = {
        "q": query,
        "from": from_date,
        "to": to_date,
        "language": language,
        "sortBy": "relevancy",
        "pageSize": max_articles,
        "apiKey": NEWS_API_KEY,
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        if not data.get("articles"):
            return ""

        noticias = []
        for articulo in data["articles"]:
            titulo = articulo.get("title", "")
            descripcion = articulo.get("description", "")
            noticias.append(f"- {titulo}: {descripcion}")

        return "\n".join(noticias)

    except requests.RequestException as e:
        return f"Error al consultar las noticias: {str(e)}"


def get_atp_news(
    curr_date: str,
) -> str:
    """
    Obtiene noticias recientes de la web oficial ATP.
    Args:
        curr_date (str): Fecha en formato yyyy-mm-dd.
    Returns:
        str: Noticias encontradas en formato texto.
    """
    news = fetch_atp_news(date=curr_date)
    if not news:
        return "No se encontraron noticias recientes en la web oficial ATP para esa fecha."
    return news


def fetch_atp_news(date: str, max_articles: int = 5) -> str:
    """
    Extrae noticias recientes de la web oficial de la ATP.
    Args:
        date (str): Fecha en formato yyyy-mm-dd.
        max_articles (int): Número máximo de noticias a devolver.
    Returns:
        str: Lista de noticias formateadas en texto.
    """
    url = "https://www.atptour.com/en/news"

    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        articles = soup.select(".article-card-wrapper")  # Clase típica de las tarjetas de noticia
        noticias = []
        parsed_date = datetime.strptime(date, "%Y-%m-%d")

        for article in articles:
            title_elem = article.select_one(".article-card-hero-title")
            date_elem = article.select_one(".article-card-meta-date")
            link_elem = article.select_one("a")

            if not (title_elem and date_elem):
                continue

            try:
                article_date = datetime.strptime(date_elem.text.strip(), "%d.%m.%Y")
            except ValueError:
                continue  # Fecha no parseable

            if article_date.date() > parsed_date.date():
                continue  # Solo queremos artículos publicados hasta esa fecha

            title = title_elem.text.strip()
            url = "https://www.atptour.com" + link_elem["href"] if link_elem else ""
            noticias.append(f"- {title} ({article_date.date()}): {url}")

            if len(noticias) >= max_articles:
                break

        return "\n".join(noticias) if noticias else ""

    except requests.RequestException as e:
        return f"Error al obtener noticias de la ATP: {str(e)}"


def get_tennisworld_news(
    curr_date: str,
) -> str:
    """
    Obtiene noticias recientes de TennisWorld.
    Args:
        curr_date (str): Fecha en formato yyyy-mm-dd.
    Returns:
        str: Noticias encontradas en formato texto.
    """
    news = fetch_tennisworld_news(date=curr_date)
    if not news:
        return "No se encontraron noticias recientes en TennisWorld para esa fecha."
    return news


def fetch_tennisworld_news(date: str, max_articles: int = 5) -> str:
    """
    Extrae noticias recientes de TennisWorld.
    Args:
        date (str): Fecha en formato yyyy-mm-dd.
        max_articles (int): Número máximo de noticias a devolver.
    Returns:
        str: Lista de noticias formateadas en texto.
    """
    url = "https://www.tennisworldusa.org/tennis/news/"

    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        articles = soup.select(".newsItem")  # Clase típica de los bloques de noticia
        noticias = []
        parsed_date = datetime.strptime(date, "%Y-%m-%d")

        for article in articles:
            title_elem = article.select_one("h2 a")
            date_elem = article.select_one(".newsDate")
            link_elem = title_elem

            if not (title_elem and date_elem):
                continue

            try:
                article_date = datetime.strptime(date_elem.text.strip(), "%b %d, %Y")
            except ValueError:
                continue

            if article_date.date() > parsed_date.date():
                continue

            title = title_elem.text.strip()
            url = "https://www.tennisworldusa.org" + link_elem["href"] if link_elem else ""
            noticias.append(f"- {title} ({article_date.date()}): {url}")

            if len(noticias) >= max_articles:
                break

        return "\n".join(noticias) if noticias else ""

    except requests.RequestException as e:
        return f"Error al obtener noticias de TennisWorld: {str(e)}"


def get_odds_data(
    player1: str,
    player2: str,
    match_date: str,
) -> str:
    """
    Obtiene cuotas reales para el partido.
    Args:
        player1 (str): Nombre del jugador 1.
        player2 (str): Nombre del jugador 2.
        match_date (str): Fecha del partido en formato yyyy-mm-dd.
    Returns:
        str: Cuotas encontradas en formato texto.
    """
    odds = fetch_tennis_odds(player1=player1, player2=player2, match_date=match_date)
    if not odds:
        return "No se encontraron cuotas reales para este partido."
    return odds 


def fetch_tennis_odds(player1: str, player2: str, match_date: str) -> str:
    """
    Busca las cuotas de apuestas para un partido de tenis usando The Odds API.
    """
    params = {
        "regions": "eu",  # Europa
        "markets": "h2h",  # head-to-head
        "oddsFormat": "decimal",
        "dateFormat": "iso",
        "apiKey": ODDS_API_KEY
    }

    try:
        response = requests.get(ODDS_BASE_URL, params=params)
        response.raise_for_status()
        matches = response.json()

        match_date_obj = datetime.strptime(match_date, "%Y-%m-%d").date()
        player1_lower = player1.lower()
        player2_lower = player2.lower()

        for match in matches:
            start_time = datetime.fromisoformat(match["commence_time"][:-1]).date()
            teams = [t.lower() for t in match.get("teams", [])]

            if (
                player1_lower in teams
                and player2_lower in teams
                and start_time == match_date_obj
            ):
                bookmaker = match["bookmakers"][0] if match["bookmakers"] else None
                if not bookmaker:
                    return ""

                markets = bookmaker["markets"]
                h2h_odds = next((m for m in markets if m["key"] == "h2h"), None)
                if not h2h_odds:
                    return ""

                outcomes = h2h_odds["outcomes"]
                odds_text = "\n".join([f"{o['name']}: cuota {o['price']}" for o in outcomes])
                return f"Cuotas de {bookmaker['title']}:\n{odds_text}"

        return ""

    except requests.RequestException as e:
        return f"Error al obtener cuotas: {str(e)}"


def get_mock_odds_data(
    player1: str,
    player2: str,
) -> str:
    """
    Devuelve cuotas simuladas para pruebas.
    Args:
        player1 (str): Nombre del jugador 1.
        player2 (str): Nombre del jugador 2.
    Returns:
        str: Cuotas simuladas en formato texto.
    """
    odds = fetch_mock_odds_data(player1=player1, player2=player2)
    if not odds:
        return "No se pudieron generar cuotas simuladas para este partido."
    return odds


def fetch_mock_odds_data(player1: str, player2: str) -> str:
    """
    Genera cuotas simuladas entre dos jugadores.
    """
    # Asignamos aleatoriamente cuotas realistas
    cuota1 = round(random.uniform(1.2, 3.5), 2)
    cuota2 = round(random.uniform(1.2, 3.5), 2)

    # Aseguramos que no haya empate de cuotas (por variedad)
    while abs(cuota1 - cuota2) < 0.1:
        cuota2 = round(random.uniform(1.2, 3.5), 2)

    return f"Cuotas simuladas:\n{player1}: cuota {cuota1}\n{player2}: cuota {cuota2}"


def get_player_profile_openai(
    player_name: str,
) -> str:
    """
    Obtiene el perfil del jugador usando OpenAI.
    Args:
        player_name (str): Nombre del jugador.
    Returns:
        str: Perfil del jugador en formato texto.
    """
    profile = fetch_player_stats_tennisabstract(player_name)
    if not profile:
        return f"No se encontró perfil para el jugador {player_name}."
    return profile


def fetch_player_stats_tennisabstract(player_name: str) -> str:
    """
    Extrae estadísticas del jugador desde Tennis Abstract mediante scraping.
    """
    # Reemplazar espacios por guiones y formar la URL del perfil
    name_url = player_name.lower().replace(" ", "")
    url = f"https://www.tennisabstract.com/cgi-bin/player-classic.cgi?p={name_url}"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        return f"Error al acceder a Tennis Abstract: {e}"

    soup = BeautifulSoup(response.text, "html.parser")

    # Buscar bloques con información relevante
    info = []
    
    # Extraer el título (nombre completo del jugador)
    header = soup.find("title")
    if header:
        info.append(f"Perfil de jugador: {header.get_text(strip=True)}")

    # Buscar secciones típicas (como la tabla de estadísticas resumen)
    stats_tables = soup.find_all("table")
    for table in stats_tables[:1]:  # Limitamos a la primera tabla (resumen)
        rows = table.find_all("tr")
        for row in rows:
            cells = row.find_all(["td", "th"])
            line = " | ".join(cell.get_text(strip=True) for cell in cells)
            info.append(line)

    if not info:
        return f"No se encontró información relevante para el jugador '{player_name}' en Tennis Abstract."

    return "\n".join(info)


def get_atp_rankings() -> str:
    """
    Obtiene el ranking ATP actual.
    Returns:
        str: Ranking ATP en formato texto.
    """
    rankings = fetch_atp_rankings()
    if not rankings:
        return "No se pudo obtener el ranking ATP actual."
    return rankings


def fetch_atp_rankings() -> str:
    """
    Realiza scraping del ranking ATP desde la web oficial.
    Returns:
        str: Cadena con los 10 primeros jugadores del ranking.
    """
    url = "https://www.atptour.com/en/rankings/singles"

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        return f"Error al acceder a la web de ATP: {e}"

    soup = BeautifulSoup(response.text, "html.parser")
    rows = soup.select("table.mega-table tbody tr")[:10]

    ranking_list = []
    for row in rows:
        rank = row.select_one("td.rank-cell").get_text(strip=True)
        player = row.select_one("td.player-cell a").get_text(strip=True)
        points = row.select_one("td.points-cell").get_text(strip=True)
        ranking_list.append(f"{rank}. {player} - {points} puntos")

    if not ranking_list:
        return "No se encontraron datos de ranking ATP."

    return "\n".join(ranking_list)


def get_recent_matches(
    player_name: str,
    num_matches: int = 5,
) -> str:
    """
    Obtiene los últimos partidos jugados por el jugador.
    Args:
        player_name (str): Nombre del jugador.
        num_matches (int): Número de partidos recientes a consultar (por defecto 5).
    Returns:
        str: Lista de partidos recientes en formato texto.
    """
    matches = fetch_recent_matches(player_name, num_matches)
    if not matches:
        return f"No se encontraron partidos recientes para el jugador {player_name}."
    return matches  


def fetch_recent_matches(player_name: str, num_matches: int = 5) -> str:
    """
    Hace scraping en TennisAbstract para obtener los últimos partidos de un jugador.
    Args:
        player_name (str): Nombre del jugador.
        num_matches (int): Número de partidos a devolver.
    Returns:
        str: Lista formateada de partidos recientes.
    """
    base_url = "https://www.tennisabstract.com/cgi-bin/player.cgi?p="
    player_encoded = quote(player_name)
    url = f"{base_url}{player_encoded}"

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        return f"Error al acceder al perfil del jugador: {e}"

    soup = BeautifulSoup(response.text, "html.parser")
    
    match_table = soup.find("table", {"id": "matches"})
    if not match_table:
        return "No se encontró la tabla de partidos."

    rows = match_table.find_all("tr")[1:num_matches + 1]  # Excluir cabecera

    match_list = []
    for row in rows:
        cells = row.find_all("td")
        if len(cells) >= 7:
            date = cells[0].text.strip()
            opponent = cells[2].text.strip()
            result = cells[3].text.strip()
            tournament = cells[6].text.strip()
            match_list.append(f"{date} - vs {opponent} ({result}) en {tournament}")

    return "\n".join(match_list) if match_list else "No se encontraron partidos recientes."


def get_surface_winrate(
    player_name: str,
    surface: str,
) -> str:
    """
    Obtiene el winrate del jugador en una superficie dada.
    Args:
        player_name (str): Nombre del jugador.
        surface (str): Superficie (clay, hard, grass).
    Returns:
        str: Winrate del jugador en la superficie indicada en formato texto.
    """
    winrate = fetch_surface_winrate(player_name, surface)
    if not winrate:
        return f"No se pudo obtener el winrate de {player_name} en la superficie {surface}."
    return winrate  


def fetch_surface_winrate(player_name: str, surface: str) -> str:
    """
    Extrae el porcentaje de victorias del jugador en una superficie desde TennisAbstract.
    Args:
        player_name (str): Nombre del jugador.
        surface (str): Superficie (clay, hard, grass).
    Returns:
        str: Winrate formateado.
    """
    base_url = "https://www.tennisabstract.com/cgi-bin/player.cgi?p="
    player_encoded = quote(player_name)
    url = f"{base_url}{player_encoded}"

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        return f"Error al acceder a la página del jugador: {e}"

    soup = BeautifulSoup(response.text, "html.parser")
    
    # Buscar la tabla de estadísticas por superficie
    stats_table = soup.find("table", {"class": "matches"})
    if not stats_table:
        return "No se encontró la tabla de superficies."

    surface = surface.lower()
    surface_map = {"clay": "Clay", "hard": "Hard", "grass": "Grass"}

    rows = stats_table.find_all("tr")
    for row in rows:
        cells = row.find_all("td")
        if len(cells) >= 5 and cells[0].text.strip() == surface_map.get(surface, ""):
            winrate = cells[4].text.strip()
            return f"{player_name} tiene un winrate de {winrate} en superficie {surface_map[surface]}."

    return f"No se encontró información sobre el winrate de {player_name} en {surface}."


def get_head_to_head(
    player1: str,
    player2: str,
) -> str:
    """
    Obtiene el historial H2H entre dos jugadores.
    Args:
        player1 (str): Nombre del jugador 1.
        player2 (str): Nombre del jugador 2.
    Returns:
        str: Historial de enfrentamientos directos (H2H) en formato texto.
    """
    h2h = fetch_head_to_head(player1, player2)
    if not h2h:
        return f"No se encontró historial H2H entre {player1} y {player2}."
    return h2h


def fetch_head_to_head(player1: str, player2: str) -> str:
    """
    Extrae el historial de enfrentamientos H2H entre dos jugadores desde TennisAbstract.
    Args:
        player1 (str): Nombre del primer jugador.
        player2 (str): Nombre del segundo jugador.
    Returns:
        str: Historial H2H en formato texto.
    """
    # Construcción de la URL (solo es posible buscar H2H desde el perfil de un jugador)
    player_encoded = quote(player1)
    url = f"https://www.tennisabstract.com/cgi-bin/player.cgi?p={player_encoded}"

    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        return f"Error al acceder a TennisAbstract: {e}"

    soup = BeautifulSoup(response.text, "html.parser")

    # Buscar sección H2H
    table = soup.find("table", {"id": "matches"})
    if not table:
        return "No se encontró la tabla de partidos."

    rows = table.find_all("tr")
    h2h_matches = []
    for row in rows:
        cells = row.find_all("td")
        if not cells or len(cells) < 6:
            continue
        opponent = cells[2].text.strip()
        if opponent.lower() == player2.lower():
            result = cells[1].text.strip()
            surface = cells[4].text.strip()
            date = cells[0].text.strip()
            h2h_matches.append(f"{date}: {result} en {surface}")

    if not h2h_matches:
        return f"No hay enfrentamientos directos recientes entre {player1} y {player2}."

    resumen = (
        f"Historial H2H entre {player1} y {player2}:\n"
        + "\n".join(h2h_matches)
    )
    return resumen


def get_injury_reports(
    player_name: str,
) -> str:
    """
    Obtiene reportes de lesiones del jugador.
    Args:
        player_name (str): Nombre del jugador.
    Returns:
        str: Reportes de lesiones en formato texto.
    """
    reports = fetch_injury_reports(player_name)
    if not reports:
        return f"No se encontraron reportes de lesiones para el jugador {player_name}."
    return reports


def fetch_injury_reports(player_name: str) -> str:
    """
    Extrae reportes de lesiones del jugador desde TennisExplorer.
    Args:
        player_name (str): Nombre del jugador.
    Returns:
        str: Informe de lesiones del jugador.
    """
    url = "https://www.tennisexplorer.com/injuries/"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        return f"Error al acceder a TennisExplorer: {e}"

    soup = BeautifulSoup(response.text, "html.parser")
    table = soup.find("table", class_="result")
    if not table:
        return "No se encontró información de lesiones en TennisExplorer."

    rows = table.find_all("tr")[1:]  # Saltar cabecera
    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 4:
            continue
        name = cols[0].text.strip()
        if player_name.lower() in name.lower():
            injury = cols[1].text.strip()
            status = cols[3].text.strip()
            return f"{name} está lesionado por: {injury}. Estado: {status}."

    return f"No se encontraron reportes de lesiones recientes para {player_name}."


def get_social_sentiment_openai(
    player_name: str,
) -> str:
    """
    Analiza sentimiento social usando OpenAI.
    Args:
        player_name (str): Nombre del jugador.
    Returns:
        str: Análisis de sentimiento social en formato texto.
    """
    sentiment = fetch_social_sentiment_openai(player_name)
    if not sentiment:
        return f"No se pudo obtener el análisis de sentimiento social para {player_name}."
    return sentiment

import openai

def fetch_social_sentiment_openai(player_name: str) -> str:
    """
    Usa OpenAI para simular un análisis de sentimiento social reciente sobre un jugador de tenis.
    No accede a redes sociales reales; el análisis se basa en conocimiento general reciente del modelo.
    
    Args:
        player_name (str): Nombre del jugador.

    Returns:
        str: Análisis de sentimiento en formato texto.
    """
    openai.api_key = OPENAI_API_KEY  # O usa os.getenv si lo gestionas por entorno

    prompt = (
        f"Eres un experto en análisis de redes sociales deportivas. "
        f"Simula un análisis de sentimiento social basado en publicaciones recientes en Twitter y Reddit "
        f"sobre el jugador de tenis '{player_name}'. Describe el sentimiento general (positivo, negativo o mixto) "
        f"y menciona posibles causas (forma reciente, polémicas, resultados, etc.). Responde en español."
    )

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Eres un analista social experto en deportes."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error al obtener análisis de sentimiento: {str(e)}"


def get_twitter_sentiment(
    player_name: str,
) -> str:
    """
    Analiza sentimiento en Twitter sobre el jugador.
    Args:
        player_name (str): Nombre del jugador.
    Returns:
        str: Análisis de sentimiento en Twitter en formato texto.
    """
    sentiment = fetch_twitter_posts(player_name)
    if not sentiment:
        return f"No se pudo obtener el análisis de sentimiento en Twitter para {player_name}."
    return sentiment    

import requests
import openai

BEARER_TOKEN = TWITTER_BEARER_TOKEN
openai.api_key = OPENAI_API_KEY  

def fetch_twitter_posts(player_name: str) -> str:
    """
    Busca tweets recientes sobre el jugador y resume el sentimiento usando OpenAI.
    Requiere acceso real a la API de Twitter v2.

    Args:
        player_name (str): Nombre del jugador.

    Returns:
        str: Análisis del sentimiento en Twitter sobre el jugador.
    """
    # Paso 1: Buscar tweets recientes
    search_url = "https://api.twitter.com/2/tweets/search/recent"
    query_params = {
        "query": f'"{player_name}" lang:en -is:retweet',  # puedes cambiar a lang:es si lo deseas
        "max_results": 10,  # puedes subir hasta 100 (recomendado: entre 10 y 50)
        "tweet.fields": "text"
    }

    headers = {
        "Authorization": f"Bearer {BEARER_TOKEN}"
    }

    response = requests.get(search_url, headers=headers, params=query_params)

    if response.status_code != 200:
        return f"Error al obtener tweets: {response.status_code} - {response.text}"

    tweets_data = response.json().get("data", [])

    if not tweets_data:
        return f"No se encontraron tweets recientes sobre {player_name}."

    # Paso 2: Concatenar textos de los tweets
    tweet_texts = "\n".join([tweet["text"] for tweet in tweets_data])

    # Paso 3: Enviar a OpenAI para análisis de sentimiento
    prompt = (
        f"A continuación tienes una colección de tweets sobre el jugador de tenis {player_name}:\n\n"
        f"{tweet_texts}\n\n"
        f"Analiza estos tweets y proporciona un resumen en español del sentimiento general (positivo, negativo, mixto), "
        f"indicando los temas más mencionados y una breve conclusión."
    )

    try:
        chat_response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Eres un experto en análisis de redes sociales deportivas."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.7,
        )
        return chat_response.choices[0].message.content.strip()

    except Exception as e:
        return f"Error al analizar sentimiento con OpenAI: {str(e)}"


def get_tennis_forum_sentiment(
    player_name: str,
) -> str:
    """
    Analiza sentimiento en foros de tenis.
    Args:
        player_name (str): Nombre del jugador.
    Returns:
        str: Análisis de sentimiento en foros de tenis en formato texto.
    """
    sentiment = fetch_tennis_forum_sentiment(player_name)
    if not sentiment:
        return f"No se pudo obtener el análisis de sentimiento en foros de tenis para {player_name}."
    return sentiment    



# Configuración de Reddit API
reddit = praw.Reddit(
    client_id=REDDIT_CLIENT_ID,
    client_secret=REDDIT_CLIENT_SECRET,
    user_agent="tennis_sentiment_analyzer"
)

# Configuración de OpenAI
openai.api_key = OPENAI_API_KEY 

def fetch_tennis_forum_sentiment(player_name: str) -> str:
    """
    Busca en Reddit (subreddits de tenis) y analiza el sentimiento general sobre un jugador.
    """
    try:
        subreddit = reddit.subreddit("tennis")
        posts = subreddit.search(player_name, limit=10)

        texts = []
        for post in posts:
            texts.append(f"{post.title}\n{post.selftext}")

        if not texts:
            return f"No se encontraron publicaciones en Reddit sobre {player_name}."

        forum_content = "\n---\n".join(texts)

        prompt = (
            f"A continuación tienes una serie de publicaciones en foros de tenis sobre el jugador {player_name}:\n\n"
            f"{forum_content}\n\n"
            f"Analiza el sentimiento general en español (positivo, negativo o mixto), "
            f"describe los argumentos y temas más frecuentes, y concluye con una valoración."
        )

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Eres un experto en análisis de foros deportivos."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.7,
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        return f"Error al obtener o analizar publicaciones de foros: {str(e)}"


def get_reddit_sentiment(
    player_name: str,
) -> str:
    """
    Analiza sentimiento en Reddit sobre el jugador.
    Args:
        player_name (str): Nombre del jugador.
    Returns:
        str: Análisis de sentimiento en Reddit en formato texto.
    """
    sentiment = fetch_reddit_posts("tennis", player_name)
    if not sentiment:
        return f"No se pudo obtener el análisis de sentimiento en Reddit para {player_name}."
    return sentiment    


def fetch_reddit_posts(subreddit_name: str, player_name: str) -> str:
    """
    Busca publicaciones sobre un jugador en un subreddit dado y analiza el sentimiento con OpenAI.
    """
    try:
        subreddit = reddit.subreddit(subreddit_name)
        posts = subreddit.search(player_name, limit=10)

        contents = []
        for post in posts:
            contents.append(f"{post.title}\n{post.selftext}")

        if not contents:
            return None

        combined_text = "\n---\n".join(contents)

        prompt = (
            f"Las siguientes publicaciones provienen de Reddit sobre el jugador de tenis {player_name}:\n\n"
            f"{combined_text}\n\n"
            f"Analiza el sentimiento general (positivo, negativo o mixto), "
            f"explica los motivos que destacan los usuarios y proporciona una conclusión clara en español."
        )

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Eres un analista de sentimiento experto en foros deportivos."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.7,
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        return f"Error al obtener o analizar publicaciones de Reddit: {str(e)}"


def get_tournament_info(
    tournament: str,
    year: int,
) -> str:
    """
    Obtiene información y estadísticas del torneo.
    Args:
        tournament (str): Nombre del torneo.
        year (int): Año del torneo.
    Returns:
        str: Información y estadísticas del torneo en formato texto.
    """
    info = fetch_tournaments(tournament, year)
    if not info:
        return f"No se encontró información para el torneo {tournament} en el año {year}."
    return info



# Diccionario de torneos conocidos: nombre → id
TOURNAMENT_IDS = {
    "Roland Garros": "sr:tournament:21",
    "Wimbledon": "sr:tournament:15",
    "US Open": "sr:tournament:8",
    "Australian Open": "sr:tournament:16",
    # Añade más si lo necesitas
}


def fetch_tournaments(tournament: str, year: int) -> str:
    """
    Llama a la API de Sportradar para obtener información del torneo.
    """
    try:
        tournament_id = TOURNAMENT_IDS.get(tournament)
        if not tournament_id:
            return f"El torneo '{tournament}' no está en la lista de torneos disponibles."

        url = f"https://api.sportradar.com/tennis/trial/v3/en/tournaments/{tournament_id}/schedule.json?api_key={SPORTRADAR_API_KEY}"
        response = requests.get(url)
        if response.status_code != 200:
            return f"No se pudo obtener información del torneo. Código de estado: {response.status_code}"

        data = response.json()

        tournament_name = data.get("tournament", {}).get("name", "Desconocido")
        category = data.get("tournament", {}).get("category", {}).get("name", "N/A")
        matches = data.get("sport_events", [])

        resumen = f"Información del torneo: {tournament_name} ({category}), Año: {year}\n"
        resumen += f"Número de partidos programados: {len(matches)}\n"
        resumen += "Ejemplos de partidos:\n"

        for match in matches[:5]:
            players = match.get("competitors", [])
            if len(players) == 2:
                resumen += f"- {players[0]['name']} vs {players[1]['name']} ({match.get('scheduled')})\n"

        return resumen

    except Exception as e:
        return f"Error al obtener datos del torneo: {str(e)}"


def get_mock_tournament_data(
    tournament: str,
    year: int,
) -> str:
    """
    Obtiene datos reales del torneo desde la API de Sportradar.

    Args:
        tournament (str): Nombre o ID del torneo (slug, por ejemplo: "australian-open").
        year (int): Año del torneo.

    Returns:
        str: Datos del torneo en formato texto.
    """
    info = fetch_tournaments(tournament, year)
    if not info:
        return f"No se encontró información para el torneo {tournament} en el año {year}."
    return info

def fetch_tournaments(tournament: str, year: int) -> str:

    url = f"https://api.sportradar.com/tennis/trial/v3/en/tournaments/{tournament}/{year}/summary.json"
    params = {"api_key": SPORTRADAR_API_KEY}

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        name = data.get("tournament", {}).get("name", "Nombre no disponible")
        category = data.get("tournament", {}).get("category", {}).get("name", "Categoría no disponible")
        surface = data.get("season", {}).get("surface", "Superficie no disponible")
        rounds = data.get("season", {}).get("tournament_rounds", [])

        summary = f"Torneo: {name}\nCategoría: {category}\nSuperficie: {surface}\n"
        summary += f"Total de rondas: {len(rounds)}"

        return summary
    except Exception as e:
        return f"Error al obtener información del torneo: {str(e)}"


def get_weather_forecast(
    latitude: float,
    longitude: float,
    match_date: str,
) -> str:
    """
    Obtiene la previsión meteorológica para el partido.
    Args:
        latitude (float): Latitud.
        longitude (float): Longitud.
        match_date (str): Fecha del partido en formato yyyy-mm-dd.
    Returns:
        str: Previsión meteorológica en formato texto.
    """
    forecast = fetch_weather_forecast(latitude, longitude, start_date=match_date, end_date=match_date)
    if not forecast:
        return f"No se pudo obtener la previsión meteorológica para la fecha {match_date}."
    return forecast

import requests

def fetch_weather_forecast(
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str
) -> str:
    """
    Llama a la API de Open-Meteo para obtener la previsión diaria.

    Args:
        latitude (float): Latitud.
        longitude (float): Longitud.
        start_date (str): Fecha de inicio.
        end_date (str): Fecha de fin.

    Returns:
        str: Resumen de previsión meteorológica.
    """
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,windspeed_10m_max",
        "timezone": "auto"
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        daily = data["daily"]
        temp_max = daily["temperature_2m_max"][0]
        temp_min = daily["temperature_2m_min"][0]
        precipitation = daily["precipitation_sum"][0]
        wind = daily["windspeed_10m_max"][0]

        summary = (
            f"Previsión para {start_date}:\n"
            f"- Temperatura máxima: {temp_max}°C\n"
            f"- Temperatura mínima: {temp_min}°C\n"
            f"- Precipitación: {precipitation} mm\n"
            f"- Viento máximo: {wind} km/h"
        )

        return summary
    except Exception as e:
        return f"Error al obtener datos meteorológicos: {str(e)}"

def get_mock_weather_data(
    location: str,
) -> str:
    """
    Devuelve datos meteorológicos simulados para pruebas.
    Args:
        location (str): Ubicación textual o ciudad.
    Returns:
        str: Datos meteorológicos simulados en formato texto.
    """
    data = fetch_mock_weather_data(location)
    if not data:
        return f"No se pudieron generar datos meteorológicos simulados para la ubicación {location}."
    return data

import requests

def fetch_mock_weather_data(location: str) -> str:
    """
    Genera una previsión meteorológica simulada para una ubicación dada.

    Args:
        location (str): Nombre de la ciudad o ubicación.

    Returns:
        str: Datos meteorológicos falsos para pruebas.
    """
    return (
        f"Datos simulados para {location}:\n"
        f"- Temperatura máxima: 25°C\n"
        f"- Temperatura mínima: 15°C\n"
        f"- Precipitación: 0.0 mm\n"
        f"- Viento: 12 km/h"
    )
