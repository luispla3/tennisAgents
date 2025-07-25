# interface.py

# ─────────────────────────────────────────────
# 1. Imports y configuración general
# ─────────────────────────────────────────────

# 2. NewsAPI - Noticias deportivas
# 3. The Odds API - Cuotas de apuestas
# 4. TennisAbstract - Información de jugadores
# 5. Social Media - X (Twitter) y Reddit
# 6. Sportradar - Torneos y estadísticas
# 7. Open-Meteo - Condiciones climáticas

# 8. Funciones de ayuda comunes (parseo, limpieza, fechas...)
# 9. Función central de agregación del análisis

# ─────────────────────────────────────────────
# 1. IMPORTS Y CONFIGURACIÓN GENERAL
# ─────────────────────────────────────────────

import os
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

# Configuración de la clave API (puede venir de variable de entorno)
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "TU_API_KEY_AQUI")

# Endpoint base de NewsAPI
NEWS_API_ENDPOINT = "https://newsapi.org/v2/everything"


# ─────────────────────────────────────────────
# 2. NEWSAPI - FUNCIONES PARA NOTICIAS DEPORTIVAS
# ─────────────────────────────────────────────

def get_news_articles(
    query: str,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    language: str = "en",
    page_size: int = 20,
) -> List[Dict[str, Any]]:
    """
    Realiza una consulta a NewsAPI para obtener artículos recientes relacionados con el tenis.

    Args:
        query: Palabra clave de búsqueda (ej. nombre del jugador o torneo).
        from_date: Fecha inicial en formato YYYY-MM-DD. Si no se da, se usa 7 días antes.
        to_date: Fecha final en formato YYYY-MM-DD. Si no se da, se usa hoy.
        language: Idioma de los artículos (por defecto inglés).
        page_size: Número de artículos a recuperar (máx 100 por página).

    Returns:
        Lista de artículos relevantes como diccionarios.
    """
    if not from_date:
        from_date = (datetime.today() - timedelta(days=7)).strftime("%Y-%m-%d")
    if not to_date:
        to_date = datetime.today().strftime("%Y-%m-%d")

    params = {
        "q": query,
        "from": from_date,
        "to": to_date,
        "language": language,
        "pageSize": page_size,
        "apiKey": NEWS_API_KEY,
        "sortBy": "relevancy",
    }

    response = requests.get(NEWS_API_ENDPOINT, params=params)
    response.raise_for_status()
    return response.json().get("articles", [])


def extract_news_summary(articles: List[Dict[str, Any]]) -> str:
    """
    Extrae y resume los títulos y descripciones de los artículos obtenidos.

    Args:
        articles: Lista de artículos obtenidos desde NewsAPI.

    Returns:
        Cadena resumen con los titulares y descripciones.
    """
    if not articles:
        return "No se encontraron noticias relevantes."

    resumen = []
    for article in articles:
        titulo = article.get("title", "")
        descripcion = article.get("description", "")
        resumen.append(f"• {titulo}\n  {descripcion}")

    return "\n\n".join(resumen)


# ─────────────────────────────────────────────
# (Opcional) EJEMPLO DE USO
# ─────────────────────────────────────────────
# if __name__ == "__main__":
#     articles = get_news_articles("Carlos Alcaraz")
#     print(extract_news_summary(articles))


# ─────────────────────────────────────────────
# 3. THE ODDS API - FUNCIONES PARA CUOTAS DE APUESTAS
# ─────────────────────────────────────────────

ODDS_API_KEY = os.getenv("ODDS_API_KEY", "TU_API_KEY_ODDS_AQUI")
ODDS_API_ENDPOINT = "https://api.the-odds-api.com/v4/sports/tennis/odds"

def get_tennis_odds(
    regions: str = "eu",
    markets: str = "h2h",
    date_format: str = "iso",
    odds_format: str = "decimal",
    bookmakers: Optional[str] = None,
    event_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Consulta cuotas de apuestas de tenis usando The Odds API.

    Args:
        regions: Regiones de casas de apuestas (por defecto 'eu').
        markets: Tipo de mercado (por defecto 'h2h' - ganador del partido).
        date_format: Formato de fecha ('iso' o 'unix').
        odds_format: Formato de cuotas ('decimal' o 'american').
        bookmakers: (Opcional) Filtrar por casas de apuestas específicas.
        event_id: (Opcional) Consultar un evento específico.

    Returns:
        Lista de eventos con cuotas.
    """
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": regions,
        "markets": markets,
        "dateFormat": date_format,
        "oddsFormat": odds_format,
    }
    if bookmakers:
        params["bookmakers"] = bookmakers
    if event_id:
        url = f"{ODDS_API_ENDPOINT}/{event_id}"
    else:
        url = ODDS_API_ENDPOINT

    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()

def extract_odds_summary(events: List[Dict[str, Any]]) -> str:
    """
    Resume las cuotas principales de los eventos de tenis.

    Args:
        events: Lista de eventos con cuotas.

    Returns:
        Cadena resumen con partidos y cuotas principales.
    """
    if not events:
        return "No se encontraron cuotas de apuestas para tenis."

    resumen = []
    for event in events:
        teams = event.get("teams", [])
        commence_time = event.get("commence_time", "")
        bookmakers = event.get("bookmakers", [])
        if teams and bookmakers:
            odds = bookmakers[0]["markets"][0]["outcomes"]
            cuotas = " vs ".join([f"{o['name']}: {o['price']}" for o in odds])
            resumen.append(f"{teams[0]} vs {teams[1]} ({commence_time})\n  {cuotas}")

    return "\n\n".join(resumen)



from bs4 import BeautifulSoup

# ─────────────────────────────────────────────
# 4. TENNISABSTRACT - INFORMACIÓN DE JUGADORES
# ─────────────────────────────────────────────

def get_tennisabstract_player_url(player_name: str) -> str:
    """
    Genera la URL del perfil de un jugador en TennisAbstract.
    """
    # TennisAbstract usa el formato: https://www.tennisabstract.com/cgi-bin/player.cgi?p=NombreApellido
    # Ejemplo: Carlos Alcaraz -> CarlosAlcaraz
    nombre_url = player_name.replace(" ", "")
    return f"https://www.tennisabstract.com/cgi-bin/player.cgi?p={nombre_url}"

def get_player_stats_tennisabstract(player_name: str) -> Dict[str, Any]:
    """
    Extrae estadísticas básicas de un jugador desde TennisAbstract.

    Args:
        player_name: Nombre del jugador (ej. "Carlos Alcaraz").

    Returns:
        Diccionario con estadísticas clave.
    """
    url = get_tennisabstract_player_url(player_name)
    response = requests.get(url)
    if response.status_code != 200:
        return {"error": f"No se pudo acceder al perfil de {player_name}."}

    soup = BeautifulSoup(response.text, "html.parser")
    stats = {}

    # Ejemplo: extraer el ranking y el récord de victorias/derrotas
    try:
        # Ranking (puede variar el selector según el diseño de la web)
        ranking_tag = soup.find("span", string="Current rank:")
        if ranking_tag:
            stats["ranking"] = ranking_tag.find_next("b").text.strip()
        # Récord de victorias/derrotas
        record_tag = soup.find("b", string="W-L")
        if record_tag:
            stats["record"] = record_tag.next_sibling.strip()
    except Exception as e:
        stats["error"] = f"Error extrayendo datos: {e}"

    stats["perfil_url"] = url
    return stats

def extract_player_stats_summary(stats: Dict[str, Any]) -> str:
    """
    Resume la información clave de un jugador obtenida de TennisAbstract.

    Args:
        stats: Diccionario de estadísticas.

    Returns:
        Cadena resumen.
    """
    if "error" in stats:
        return stats["error"]
    resumen = f"Ranking actual: {stats.get('ranking', 'N/D')}\n"
    resumen += f"Récord W-L: {stats.get('record', 'N/D')}\n"
    resumen += f"Perfil completo: {stats.get('perfil_url')}"
    return resumen


import os

# ─────────────────────────────────────────────
# 5. SOCIAL MEDIA - X (TWITTER) Y REDDIT
# ─────────────────────────────────────────────

# --- X (Twitter) ---
import requests

TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN", "TU_TOKEN_AQUI")
TWITTER_SEARCH_URL = "https://api.twitter.com/2/tweets/search/recent"

def get_twitter_posts(query: str, max_results: int = 10) -> list:
    """
    Busca tweets recientes relacionados con el query.
    """
    headers = {"Authorization": f"Bearer {TWITTER_BEARER_TOKEN}"}
    params = {
        "query": query,
        "max_results": max_results,
        "tweet.fields": "created_at,text,author_id"
    }
    response = requests.get(TWITTER_SEARCH_URL, headers=headers, params=params)
    if response.status_code != 200:
        return []
    return response.json().get("data", [])

def extract_twitter_summary(tweets: list) -> str:
    """
    Resume los tweets encontrados.
    """
    if not tweets:
        return "No se encontraron tweets relevantes."
    resumen = []
    for tweet in tweets:
        resumen.append(f"• {tweet.get('text')}")
    return "\n\n".join(resumen)

# --- Reddit ---
import praw

REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID", "TU_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "TU_CLIENT_SECRET")
REDDIT_USER_AGENT = "tennisAgents/0.1"

def get_reddit_posts(subreddit: str, query: str, limit: int = 10) -> list:
    """
    Busca posts recientes en un subreddit relacionados con el query.
    """
    reddit = praw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        user_agent=REDDIT_USER_AGENT
    )
    posts = []
    for submission in reddit.subreddit(subreddit).search(query, limit=limit, sort="new"):
        posts.append({"title": submission.title, "url": submission.url})
    return posts

def extract_reddit_summary(posts: list) -> str:
    """
    Resume los posts de Reddit encontrados.
    """
    if not posts:
        return "No se encontraron posts relevantes en Reddit."
    resumen = []
    for post in posts:
        resumen.append(f"• {post['title']}\n  {post['url']}")
    return "\n\n".join(resumen)


# ─────────────────────────────────────────────
# 6. SPORTRADAR - TORNEOS Y ESTADÍSTICAS
# ─────────────────────────────────────────────

SPORTRADAR_API_KEY = os.getenv("SPORTRADAR_API_KEY", "TU_API_KEY_SPORTSRADAR")
SPORTRADAR_BASE_URL = "https://api.sportradar.com/tennis/trial/v3/en"

def get_tournaments(year: int = datetime.today().year) -> List[Dict[str, Any]]:
    """
    Obtiene la lista de torneos de tenis para un año usando Sportradar.

    Args:
        year: Año de los torneos (por defecto el actual).

    Returns:
        Lista de torneos como diccionarios.
    """
    url = f"{SPORTRADAR_BASE_URL}/tournaments.json"
    params = {"api_key": SPORTRADAR_API_KEY, "year": year}
    response = requests.get(url, params=params)
    if response.status_code != 200:
        return []
    return response.json().get("tournaments", [])

def get_tournament_statistics(tournament_id: str) -> Dict[str, Any]:
    """
    Obtiene estadísticas de un torneo específico.

    Args:
        tournament_id: ID del torneo.

    Returns:
        Diccionario con estadísticas del torneo.
    """
    url = f"{SPORTRADAR_BASE_URL}/tournaments/{tournament_id}/summaries.json"
    params = {"api_key": SPORTRADAR_API_KEY}
    response = requests.get(url, params=params)
    if response.status_code != 200:
        return {"error": "No se pudo obtener información del torneo."}
    return response.json()

def extract_tournaments_summary(tournaments: List[Dict[str, Any]]) -> str:
    """
    Resume la lista de torneos.

    Args:
        tournaments: Lista de torneos.

    Returns:
        Cadena resumen.
    """
    if not tournaments:
        return "No se encontraron torneos."
    resumen = []
    for t in tournaments[:10]:  # Limita a los 10 primeros para el resumen
        resumen.append(f"{t.get('name', 'N/D')} ({t.get('id', 'N/D')})")
    return "\n".join(resumen)

def extract_tournament_stats_summary(stats: Dict[str, Any]) -> str:
    """
    Resume las estadísticas de un torneo.

    Args:
        stats: Diccionario de estadísticas.

    Returns:
        Cadena resumen.
    """
    if "error" in stats:
        return stats["error"]
    # Puedes personalizar este resumen según la estructura real de la respuesta
    return f"Resumen del torneo: {stats}"


# ─────────────────────────────────────────────
# 7. OPEN-METEO - CONDICIONES CLIMÁTICAS
# ─────────────────────────────────────────────

OPEN_METEO_ENDPOINT = "https://api.open-meteo.com/v1/forecast"

def get_weather_forecast(
    latitude: float,
    longitude: float,
    hourly: str = "temperature_2m,precipitation,wind_speed_10m",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    timezone: str = "auto"
) -> Dict[str, Any]:
    """
    Consulta la previsión meteorológica para unas coordenadas usando Open-Meteo.

    Args:
        latitude: Latitud del lugar.
        longitude: Longitud del lugar.
        hourly: Variables meteorológicas a consultar.
        start_date: Fecha de inicio (YYYY-MM-DD), por defecto hoy.
        end_date: Fecha de fin (YYYY-MM-DD), por defecto hoy.
        timezone: Zona horaria (por defecto 'auto').

    Returns:
        Diccionario con la previsión meteorológica.
    """
    if not start_date:
        start_date = datetime.today().strftime("%Y-%m-%d")
    if not end_date:
        end_date = start_date

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": hourly,
        "start_date": start_date,
        "end_date": end_date,
        "timezone": timezone
    }
    response = requests.get(OPEN_METEO_ENDPOINT, params=params)
    if response.status_code != 200:
        return {"error": "No se pudo obtener la previsión meteorológica."}
    return response.json()

def extract_weather_summary(weather: Dict[str, Any]) -> str:
    """
    Resume la previsión meteorológica.

    Args:
        weather: Diccionario con la previsión meteorológica.

    Returns:
        Cadena resumen.
    """
    if "error" in weather:
        return weather["error"]
    try:
        temps = weather["hourly"]["temperature_2m"]
        precs = weather["hourly"]["precipitation"]
        winds = weather["hourly"]["wind_speed_10m"]
        resumen = (
            f"Temperaturas (°C): {temps}\n"
            f"Precipitación (mm): {precs}\n"
            f"Viento (km/h): {winds}"
        )
        return resumen
    except Exception:
        return "No se pudo extraer el resumen meteorológico."


# ─────────────────────────────────────────────
# 8. FUNCIONES DE AYUDA COMUNES (PARSEO, LIMPIEZA, FECHAS...)
# ─────────────────────────────────────────────

import re
import unicodedata

def clean_text(text: str) -> str:
    """
    Limpia un texto eliminando saltos de línea, espacios extra y caracteres especiales.
    """
    if not isinstance(text, str):
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = re.sub(r"\s+", " ", text)
    text = text.strip()
    return text

def parse_date(date_str: str, fmt: str = "%Y-%m-%d") -> Optional[datetime]:
    """
    Parsea una cadena de fecha a objeto datetime.
    """
    try:
        return datetime.strptime(date_str, fmt)
    except Exception:
        return None

def format_date(date_obj: datetime, fmt: str = "%Y-%m-%d") -> str:
    """
    Formatea un objeto datetime a cadena.
    """
    if not isinstance(date_obj, datetime):
        return ""
    return date_obj.strftime(fmt)

def safe_get(d: dict, keys: list, default=None):
    """
    Acceso seguro a diccionarios anidados.
    """
    for key in keys:
        if isinstance(d, dict) and key in d:
            d = d[key]
        else:
            return default
    return d

def normalize_player_name(name: str) -> str:
    """
    Normaliza el nombre de un jugador para búsquedas o URLs.
    """
    name = clean_text(name)
    name = name.title()
    name = name.replace(" ", "")
    return name


# ─────────────────────────────────────────────
# 9. FUNCIÓN CENTRAL DE AGREGACIÓN DEL ANÁLISIS
# ─────────────────────────────────────────────

def aggregate_tennis_analysis(
    player_name: str,
    tournament_year: Optional[int] = None,
    location: Optional[Dict[str, float]] = None,
    news_language: str = "en",
    subreddit: str = "tennis"
) -> Dict[str, Any]:
    """
    Agrega y resume toda la información relevante de un jugador y contexto de partido.

    Args:
        player_name: Nombre del jugador.
        tournament_year: Año de torneos a consultar (opcional).
        location: Diccionario con 'latitude' y 'longitude' (opcional).
        news_language: Idioma para las noticias.
        subreddit: Subreddit para buscar en Reddit.

    Returns:
        Diccionario con el análisis agregado.
    """
    analysis = {}

    # Noticias
    articles = get_news_articles(player_name, language=news_language)
    analysis["noticias"] = extract_news_summary(articles)

    # Cuotas de apuestas
    odds = get_tennis_odds()
    analysis["cuotas"] = extract_odds_summary(odds)

    # Estadísticas del jugador
    stats = get_player_stats_tennisabstract(player_name)
    analysis["estadisticas_jugador"] = extract_player_stats_summary(stats)

    # Social Media
    tweets = get_twitter_posts(player_name)
    analysis["twitter"] = extract_twitter_summary(tweets)
    reddit_posts = get_reddit_posts(subreddit, player_name)
    analysis["reddit"] = extract_reddit_summary(reddit_posts)

    # Torneos y estadísticas
    if tournament_year:
        tournaments = get_tournaments(tournament_year)
    else:
        tournaments = get_tournaments()
    analysis["torneos"] = extract_tournaments_summary(tournaments)
    # Ejemplo: estadísticas del primer torneo encontrado
    if tournaments:
        tournament_id = tournaments[0].get("id")
        if tournament_id:
            tournament_stats = get_tournament_statistics(tournament_id)
            analysis["estadisticas_torneo"] = extract_tournament_stats_summary(tournament_stats)
        else:
            analysis["estadisticas_torneo"] = "No disponible."
    else:
        analysis["estadisticas_torneo"] = "No disponible."

    # Clima
    if location and "latitude" in location and "longitude" in location:
        weather = get_weather_forecast(location["latitude"], location["longitude"])
        analysis["clima"] = extract_weather_summary(weather)
    else:
        analysis["clima"] = "No se proporcionó ubicación."

    return analysis
