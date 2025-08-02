from .news_utils import fetch_news
from .odds_utils import fetch_tennis_odds, generate_mock_odds
from .odds_utils import generate_mock_odds
from .player_utils import fetch_atp_rankings
from .player_utils import fetch_recent_matches
from .player_utils import fetch_surface_winrate
from .player_utils import fetch_head_to_head
from .player_utils import fetch_injury_reports
from .sentiment_utils import fetch_reddit_sentiment
from .sentiment_utils import fetch_reddit_sentiment
from .tournament_utils import fetch_tournament_info
from .tournament_utils import get_mock_data
from .weather_utils import fetch_weather_forecast

import requests
import os

def get_news(query: str, curr_date: str) -> str:
    """
    Interfaz que prepara y formatea las noticias obtenidas desde Google News.
    """
    noticias = fetch_news(query, curr_date)

    if not noticias:
        result = f"No se encontraron noticias sobre '{query}' para la fecha {curr_date}."
        return result
    
    return noticias


def get_atp_news(curr_date: str) -> str:
    """
    Obtiene noticias recientes sobre el circuito ATP desde una API (NewsAPI).
    """
    noticias = fetch_news("ATP tennis", curr_date)

    if not noticias:
        return f"No se encontraron noticias sobre ATP en la fecha {curr_date}."

    noticias_str = f"## Noticias sobre ATP para el {curr_date}:\n\n"
    for noticia in noticias:
        noticias_str += f"### {noticia['title']}\n"
        noticias_str += f"{noticia['description']}\n"
        noticias_str += f"[Enlace]({noticia['url']})\n\n"

    return noticias_str


def get_tennisworld_news(curr_date: str) -> str:
    """
    Busca noticias recientes sobre tenis relacionadas con TennisWorld u otras fuentes relevantes usando NewsAPI.
    """
    noticias = fetch_news("tennis news", curr_date)

    if not noticias:
        return f"No se encontraron noticias relevantes en la fecha {curr_date}."

    noticias_str = f"## Noticias tipo TennisWorld del {curr_date}:\n\n"
    for noticia in noticias:
        noticias_str += f"### {noticia['title']}\n"
        noticias_str += f"{noticia['description']}\n"
        noticias_str += f"[Leer más]({noticia['url']})\n\n"

    return noticias_str


def get_tennis_odds(tournament_key: str) -> str:
    """
    Consulta las cuotas de apuestas reales para un torneo específico usando una API.
    """
    import json
    
    odds_data = fetch_tennis_odds(tournament_key)
    return json.dumps(odds_data, indent=2)

def get_mock_odds_data(player1: str, player2: str) -> str:
    """
    Devuelve una simulación realista de cuotas para un partido entre dos jugadores.
    """
    odds_data = generate_mock_odds(player1, player2)

    result = f"## Cuotas simuladas para {player1} vs {player2}:\n\n"
    for bookmaker, cuota in odds_data.items():
        result += f"- **{bookmaker}**: {player1} → {cuota['player1']}, {player2} → {cuota['player2']}\n"
    return result


def get_atp_rankings() -> str:
    """
    Consulta el ranking ATP actual y lo devuelve formateado.
    """
    rankings = fetch_atp_rankings()

    if not rankings:
        return "No se pudo obtener el ranking ATP."

    result = "## Ranking ATP actual:\n\n"
    for jugador in rankings:
        result += f"{jugador['rank']}. {jugador['name']} ({jugador['country']}) - {jugador['points']} pts\n"
    
    return result


def get_recent_matches(player_name: str, num_matches: int = 5) -> str:
    """
    Devuelve los últimos partidos jugados por el jugador especificado.
    """
    matches = fetch_recent_matches(player_name, num_matches)

    if not matches:
        return f"No se encontraron partidos recientes para {player_name}."

    result = f"## Últimos {num_matches} partidos de {player_name}:\n\n"
    for m in matches:
        result += f"- {m['date']} | {m['tournament']} | vs {m['opponent']} | Resultado: {m['result']} | Superficie: {m['surface']}\n"

    return result


def get_surface_winrate(player_name: str, surface: str) -> str:
    """
    Devuelve el porcentaje de victorias del jugador en una superficie específica.
    """
    stats = fetch_surface_winrate(player_name, surface)

    if not stats:
        return f"No se encontraron datos sobre {player_name} en {surface}."

    return (
        f"## Rendimiento de {player_name} en {surface}:\n\n"
        f"- Partidos ganados: {stats['wins']}\n"
        f"- Partidos perdidos: {stats['losses']}\n"
        f"- Winrate: {stats['winrate']}%"
    )


def get_head_to_head(player1: str, player2: str) -> str:
    """
    Devuelve el historial H2H entre dos jugadores de tenis.
    """
    data = fetch_head_to_head(player1, player2)

    if not data:
        return f"No se encontró historial H2H entre {player1} y {player2}."

    resumen = f"## Historial H2H entre {player1} y {player2}:\n\n"
    resumen += f"- Victorias de {player1}: {data['wins_p1']}\n"
    resumen += f"- Victorias de {player2}: {data['wins_p2']}\n"
    resumen += f"- Total de enfrentamientos: {data['total']}\n\n"

    resumen += "### Últimos partidos:\n"
    for match in data["recent_matches"]:
        resumen += (
            f"- {match['date']} | {match['tournament']} | {match['winner']} ganó en {match['score']} "
            f"(Superficie: {match['surface']})\n"
        )

    return resumen

def get_injury_reports(player_name: str) -> str:
    data = fetch_injury_reports(player_name)
    if not data:
        return f"No se encontraron registros de lesión o retorno para {player_name}."
    
    formatted = "\n".join([
        f"{entry['date']}: {entry['player']} ({entry['status']}) - {entry['tournament']} - {entry['reason']}"
        for entry in data
    ])
    return formatted


def get_twitter_posts(player_name: str) -> str:
    """
    Usa NewsAPI para simular un análisis de sentimiento como si fuese de Twitter.
    """
    newsapi_key = os.getenv("NEWS_API_KEY")
    if not newsapi_key:
        return "La clave de API de NewsAPI no está configurada. No se puede obtener el sentimiento de Twitter."

    url = "https://newsapi.org/v2/everything"
    params = {
        "q": player_name,
        "language": "en",
        "sortBy": "relevancy",
        "pageSize": 10,
        "apiKey": newsapi_key,
    }

    try:
        response = requests.get(url, params=params)
        if response.status_code != 200:
            return f"[ERROR] Fallo al obtener noticias: {response.text}"
    except Exception as e:
        return f"[ERROR] Error al conectar con la API de noticias: {e}"

    articles = response.json().get("articles", [])
    if not articles:
        return f"No se encontraron noticias recientes sobre {player_name}."

    sentiments = []
    for article in articles:
        text = f"{article.get('title', '')} {article.get('description', '')}"
        # Simple sentiment analysis based on positive/negative keywords
        positive_words = ['victory', 'win', 'success', 'great', 'excellent', 'amazing', 'outstanding']
        negative_words = ['defeat', 'loss', 'injury', 'poor', 'bad', 'terrible', 'disappointing']
        
        text_lower = text.lower()
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        if positive_count > negative_count:
            sentiment = 0.3
        elif negative_count > positive_count:
            sentiment = -0.3
        else:
            sentiment = 0.0
            
        sentiments.append(sentiment)

    average_sentiment = sum(sentiments) / len(sentiments)

    if average_sentiment > 0.2:
        mood = "positivo"
    elif average_sentiment < -0.2:
        mood = "negativo"
    else:
        mood = "neutral"

    return f"El sentimiento medio en noticias recientes sobre {player_name} es {mood} (polaridad media: {average_sentiment:.2f})."


def get_tennis_forum_sentiment(player_name: str) -> str:
    sentiment_data = fetch_reddit_sentiment(player_name)

    if not sentiment_data:
        return f"No se encontraron publicaciones recientes sobre {player_name}."

    resumen = f"Sentimiento general en foros sobre {player_name}:\n"
    resumen += f"- Positivos: {sentiment_data['positive']}\n"
    resumen += f"- Negativos: {sentiment_data['negative']}\n"
    resumen += f"- Neutros: {sentiment_data['neutral']}\n"
    resumen += f"\nComentarios destacados:\n"
    for post in sentiment_data["examples"]:
        resumen += f"• {post['text']} (→ {post['sentiment']})\n"
    return resumen

def get_reddit_posts(subreddit_name: str, player_name: str) -> str:

    sentiment_data = fetch_reddit_sentiment(player_name, subreddit=subreddit_name)

    if not sentiment_data:
        return f"No se encontraron publicaciones recientes sobre {player_name} en r/{subreddit_name}."

    resumen = f"Sentimiento en Reddit sobre {player_name} (subreddit: r/{subreddit_name}):\n"
    resumen += f"- Positivos: {sentiment_data['positive']}\n"
    resumen += f"- Negativos: {sentiment_data['negative']}\n"
    resumen += f"- Neutros: {sentiment_data['neutral']}\n"
    resumen += "\nComentarios destacados:\n"
    for post in sentiment_data["examples"]:
        resumen += f"• {post['text']} (→ {post['sentiment']})\n"

    return resumen


def get_tournaments(tournament: str, year: int) -> str:
    data = fetch_tournament_info(tournament, year)

    if not data:
        return f"No se encontró información sobre el torneo '{tournament}' en {year}."

    resumen = f" {data['name']} ({year})\n"
    resumen += f"- Ubicación: {data['location']}\n"
    resumen += f"- Superficie: {data['surface']}\n"
    resumen += f"- Fecha de inicio: {data['start_date']}\n"
    resumen += f"- Fecha de final: {data['end_date']}\n"
    resumen += f"- Ganador: {data['winner']}\n"
    resumen += f"- Finalista: {data['runner_up']}\n"
    resumen += f"- Participantes destacados: {', '.join(data['notables'])}\n"

    return resumen


def get_mock_tournament_data(tournament: str, year: int) -> str:
    data = get_mock_data(tournament, year)

    resumen = f" {data['name']} ({year})\n"
    resumen += f"- Ubicación: {data['location']}\n"
    resumen += f"- Superficie: {data['surface']}\n"
    resumen += f"- Fecha de inicio: {data['start_date']}\n"
    resumen += f"- Fecha de final: {data['end_date']}\n"
    resumen += f"- Ganador: {data['winner']}\n"
    resumen += f"- Finalista: {data['runner_up']}\n"
    resumen += f"- Participantes destacados: {', '.join(data['notables'])}\n"

    return resumen


def get_weather_forecast(latitude: float, longitude: float, start_date: str, end_date: str) -> str:
    forecast = fetch_weather_forecast(latitude, longitude, start_date, end_date)

    if not forecast:
        return "No se pudo obtener el pronóstico del tiempo."

    texto = f"- Pronóstico del {start_date}:\n"
    texto += f"- Temperatura máxima: {forecast['temp_max']}°C\n"
    texto += f"- Temperatura mínima: {forecast['temp_min']}°C\n"
    texto += f"- Precipitación: {forecast['precip']} mm\n"
    texto += f"- Viento: {forecast['wind']} km/h\n"
    texto += f"- Cielo: {forecast['description']}\n"

    return texto

import random

def get_mock_weather_data(location: str) -> str:
    forecast = {
        "location": location,
        "temp_max": round(random.uniform(22, 35), 1),
        "temp_min": round(random.uniform(12, 21), 1),
        "precip": round(random.uniform(0, 10), 1),
        "wind": round(random.uniform(5, 25), 1),
        "description": random.choice(["Despejado", "Parcialmente nublado", "Lluvia ligera", "Tormenta"]),
    }

    return (
        f" [SIMULADO] Pronóstico en {forecast['location']}:\n"
        f"- Temp. Máx: {forecast['temp_max']}°C\n"
        f"- Temp. Mín: {forecast['temp_min']}°C\n"
        f"- Precipitación: {forecast['precip']} mm\n"
        f"- Viento: {forecast['wind']} km/h\n"
        f"- Cielo: {forecast['description']}"
    )
