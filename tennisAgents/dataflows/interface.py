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
    Consulta el ranking ATP actual y lo devuelve formateado con los IDs de los jugadores.
    """
    rankings = fetch_atp_rankings()

    if not rankings:
        return "No se pudo obtener el ranking ATP."

    result = "## Ranking ATP actual (con IDs de jugadores):\n\n"
    for jugador in rankings:
        player_id = jugador.get('id', 'N/D')
        result += f"{jugador['position']}. {jugador['name']} (ID: {player_id}) - {jugador['point']} pts\n"
    
    result += "\n**Nota**: Usa estos IDs para llamar a get_recent_matches con los IDs correctos de los jugadores."
    return result


def get_recent_matches(player_id:int, opponent_id:int, num_matches: int = 30) -> str:
    """
    Devuelve los últimos partidos jugados entre dos jugadores específicos.
    Utiliza el endpoint getH2HMatches de la API de tenis.
    """
    matches = fetch_recent_matches(player_id, opponent_id, num_matches)

    if not matches:
        return f"No se encontraron partidos recientes entre los jugadores con IDs {player_id} y {opponent_id}."

    result = f"## Últimos {len(matches)} partidos entre jugadores (IDs: {player_id} vs {opponent_id}):\n\n"
    for m in matches:
        result += f"- **{m['date']}** | {m['tournament']} | vs {m['opponent']} | **Resultado: {m['result']}** | Superficie: {m['surface']} | Ganador: {m['winner']}\n"

    
    return result


def get_surface_winrate(player_id: int, surface: str) -> str:
    """
    Devuelve el porcentaje de victorias del jugador en una superficie específica.
    Usa directamente el ID del jugador proporcionado.
    """
    # Usar directamente el ID proporcionado para obtener los datos de superficie
    stats = fetch_surface_winrate(player_id, surface)

    if not stats:
        return f"No se encontraron datos sobre el jugador con ID {player_id} en {surface}."

    return (
        f"## Rendimiento del jugador (ID: {player_id}) en {surface}:\n\n"
        f"- Partidos ganados: {stats['wins']}\n"
        f"- Partidos perdidos: {stats['losses']}\n"
        f"- Winrate: {stats['winrate']}%"
    )


def get_head_to_head(player1: int, player2: int) -> str:
    """
    Devuelve las estadísticas H2H entre dos jugadores de tenis.
    """
    data = fetch_head_to_head(player1, player2)
    
    if not data:
        return f"No se encontraron estadísticas H2H entre los jugadores {player1} y {player2}."
    
    matches_count = data.get("matches_count", "0")
    player1_stats = data.get("player1_stats", {})
    player2_stats = data.get("player2_stats", {})
    
    # Formatear estadísticas del jugador 1
    p1_formatted = ""
    if player1_stats:
        p1_formatted = f"**Jugador 1 (ID: {player1}):**\n"
        p1_formatted += f"- Partidos jugados: {player1_stats.get('statMatchesPlayed', 'N/A')}\n"
        p1_formatted += f"- Partidos ganados: {player1_stats.get('matchesWon', 'N/A')}\n"
        p1_formatted += f"- Porcentaje victorias: {round((player1_stats.get('matchesWon', 0) / player1_stats.get('statMatchesPlayed', 1)) * 100, 1)}%\n"
        p1_formatted += f"- Primer servicio: {player1_stats.get('firstServe', 'N/A')}/{player1_stats.get('firstServeOf', 'N/A')} ({player1_stats.get('firstServePercentage', 'N/A')}%)\n"
        p1_formatted += f"- Aces: {player1_stats.get('aces', 'N/A')}\n"
        p1_formatted += f"- Dobles faltas: {player1_stats.get('doubleFaults', 'N/A')}\n"
        p1_formatted += f"- Errores no forzados: {player1_stats.get('unforcedErrors', 'N/A')}\n"
        p1_formatted += f"- Winners: {player1_stats.get('winners', 'N/A')}\n"
        p1_formatted += f"- Break points convertidos: {player1_stats.get('breakPointsConverted', 'N/A')}/{player1_stats.get('breakPointsConvertedOf', 'N/A')} ({player1_stats.get('breakpointsWonPercentage', 'N/A')}%)\n"
        p1_formatted += f"- Sets ganados: {player1_stats.get('setsWon', 'N/A')}\n"
        p1_formatted += f"- Juegos ganados: {player1_stats.get('gamesWon', 'N/A')}\n"
        p1_formatted += f"- Títulos: {player1_stats.get('title', 'N/A')}\n"
        p1_formatted += f"- Grand Slams: {player1_stats.get('grandSlam', 'N/A')}\n"
        p1_formatted += f"- Masters: {player1_stats.get('masters', 'N/A')}\n"
        p1_formatted += f"- Superficies - Hard: {player1_stats.get('hard', 'N/A')}, Clay: {player1_stats.get('clay', 'N/A')}, Indoor: {player1_stats.get('iHard', 'N/A')}, Grass: {player1_stats.get('grass', 'N/A')}\n"
    
    # Formatear estadísticas del jugador 2
    p2_formatted = ""
    if player2_stats:
        p2_formatted = f"**Jugador 2 (ID: {player2}):**\n"
        p2_formatted += f"- Partidos jugados: {player2_stats.get('statMatchesPlayed', 'N/A')}\n"
        p2_formatted += f"- Partidos ganados: {player2_stats.get('matchesWon', 'N/A')}\n"
        p2_formatted += f"- Porcentaje victorias: {round((player2_stats.get('matchesWon', 0) / player2_stats.get('statMatchesPlayed', 1)) * 100, 1)}%\n"
        p2_formatted += f"- Primer servicio: {player2_stats.get('firstServe', 'N/A')}/{player2_stats.get('firstServeOf', 'N/A')} ({player2_stats.get('firstServePercentage', 'N/A')}%)\n"
        p2_formatted += f"- Aces: {player2_stats.get('aces', 'N/A')}\n"
        p2_formatted += f"- Dobles faltas: {player2_stats.get('doubleFaults', 'N/A')}\n"
        p2_formatted += f"- Errores no forzados: {player2_stats.get('unforcedErrors', 'N/A')}\n"
        p2_formatted += f"- Winners: {player2_stats.get('winners', 'N/A')}\n"
        p2_formatted += f"- Break points convertidos: {player2_stats.get('breakPointsConverted', 'N/A')}/{player2_stats.get('breakPointsConvertedOf', 'N/A')} ({player2_stats.get('breakpointsWonPercentage', 'N/A')}%)\n"
        p2_formatted += f"- Sets ganados: {player2_stats.get('setsWon', 'N/A')}\n"
        p2_formatted += f"- Juegos ganados: {player2_stats.get('gamesWon', 'N/A')}\n"
        p2_formatted += f"- Títulos: {player2_stats.get('title', 'N/A')}\n"
        p2_formatted += f"- Grand Slams: {player2_stats.get('grandSlam', 'N/A')}\n"
        p2_formatted += f"- Masters: {player2_stats.get('masters', 'N/A')}\n"
        p2_formatted += f"- Superficies - Hard: {player2_stats.get('hard', 'N/A')}, Clay: {player2_stats.get('clay', 'N/A')}, Indoor: {player2_stats.get('iHard', 'N/A')}, Grass: {player2_stats.get('grass', 'N/A')}\n"
    
    result = f"**Estadísticas Head-to-Head**\n"
    result += f"Total de partidos: {matches_count}\n\n"
    result += p1_formatted + "\n" + p2_formatted
    
    print(f"[DEBUG] Resultado final de get_head_to_head: {result}")
    return result

def get_injury_reports() -> str:
    data = fetch_injury_reports()
    if not data:
        return f"No se encontraron registros de lesión o retorno para ningún jugador."
    
    # Verificar si data tiene la estructura correcta
    if isinstance(data, dict) and 'injured_players' in data:
        # Nueva estructura de datos
        injured_players = data['injured_players']
        returning_players = data.get('returning_players', [])
        
        formatted = ""
        
        # Mostrar jugadores lesionados
        if injured_players:
            formatted += "🏥 JUGADORES LESIONADOS:\n"
            formatted += "-" * 40 + "\n"
            formatted += "\n".join([
                f"{entry['date']}: {entry['player_name']} - {entry['tournament']} - {entry['reason']}"
                for entry in injured_players[:15]  # Mostrar solo los primeros 15
            ])
            
            total_injured = data.get('total_injured', len(injured_players))
            formatted += f"\n\n📊 Total lesionados: {total_injured} jugadores"
        else:
            formatted += "🏥 No se encontraron jugadores lesionados.\n"
        
        # Mostrar jugadores que regresan
        if returning_players:
            formatted += "\n\n✅ JUGADORES QUE REGRESAN:\n"
            formatted += "-" * 40 + "\n"
            formatted += "\n".join([
                f"{entry['date']}: {entry['player_name']} - {entry['tournament']} - {entry['status']}"
                for entry in returning_players[:15]  # Mostrar solo los primeros 15
            ])
            
            total_returning = data.get('total_returning', len(returning_players))
            formatted += f"\n\n📊 Total que regresan: {total_returning} jugadores"
        else:
            formatted += "\n\n✅ No se encontraron jugadores que regresen de lesiones.\n"
        
        # Resumen general
        total_injured = data.get('total_injured', len(injured_players))
        total_returning = data.get('total_returning', len(returning_players))
        formatted += f"\n\n📈 RESUMEN GENERAL: {total_injured} lesionados, {total_returning} que regresan"
        
    else:
        # Estructura antigua (fallback)
        formatted = "\n".join([
            f"{entry['date']}: {entry.get('player_name', entry.get('player', 'N/A'))} - {entry.get('tournament', 'N/A')} - {entry.get('reason', 'N/A')}"
            for entry in data if isinstance(data, list)
        ])

    print(f"[DEBUG] Resultado final de get_injury_reports: {formatted}")
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
