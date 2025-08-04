from .news_utils import fetch_news
from .tournament_utils import get_tournament_surface as get_tournament_surface_impl
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
from .weather_utils import fetch_weather_forecast, format_weather_report

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

def get_tournament_surface(tournament_key: str) -> str:
    """
    Obtiene la superficie de un torneo específico.
    """
    return get_tournament_surface_impl(tournament_key)

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
        result += f"{jugador['position']}. {jugador['name']} (ID: {jugador['id']}) - {jugador['point']} pts\n"
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


def get_head_to_head(player1: int, player2: int) -> str:
    """
    Devuelve el historial H2H entre dos jugadores de tenis.
    """
    try:
        data = fetch_head_to_head(player1, player2)

        if not data:
            return f"No se encontró historial H2H entre {player1} y {player2}."

        resumen = f"## Historial H2H entre jugadores {player1} y {player2}:\n\n"
        
        # Get match count
        matches_count = data.get('matches_count', 0)
        resumen += f"**Total de enfrentamientos:** {matches_count}\n\n"
        
        # Get player stats
        player1_stats = data.get('player1_stats')
        player2_stats = data.get('player2_stats')
        
        if player1_stats and player2_stats:
            # Overall H2H record
            p1_wins = player1_stats.get('matchesWon', 0)
            p2_wins = player2_stats.get('matchesWon', 0)
            resumen += f"**Record H2H:**\n"
            resumen += f"- Jugador {player1}: {p1_wins} victorias ({(p1_wins/int(matches_count)*100):.1f}%)\n"
            resumen += f"- Jugador {player2}: {p2_wins} victorias ({(p2_wins/int(matches_count)*100):.1f}%)\n\n"
            
            # Surface breakdown
            resumen += f"**Por superficie:**\n"
            resumen += f"- Jugador {player1}: Dura {player1_stats.get('hard', 0)}, Arcilla {player1_stats.get('clay', 0)}, Hierba {player1_stats.get('grass', 0)}, Indoor {player1_stats.get('iHard', 0)}\n"
            resumen += f"- Jugador {player2}: Dura {player2_stats.get('hard', 0)}, Arcilla {player2_stats.get('clay', 0)}, Hierba {player2_stats.get('grass', 0)}, Indoor {player2_stats.get('iHard', 0)}\n\n"
            
            # Serve statistics comparison
            resumen += f"**Estadísticas de servicio:**\n"
            resumen += f"- Jugador {player1}: {player1_stats.get('firstServePercentage', 0)}% primer servicio, {player1_stats.get('aces', 0)} aces, {player1_stats.get('doubleFaults', 0)} dobles faltas\n"
            resumen += f"- Jugador {player2}: {player2_stats.get('firstServePercentage', 0)}% primer servicio, {player2_stats.get('aces', 0)} aces, {player2_stats.get('doubleFaults', 0)} dobles faltas\n\n"
            
            # Break points and crucial moments
            resumen += f" **Momentos cruciales:**\n"
            resumen += f"- Jugador {player1}: {player1_stats.get('breakpointsWonPercentage', 0)}% break points convertidos, {player1_stats.get('decidingSetWinPercentage', 0)}% sets decisivos ganados\n"
            resumen += f"- Jugador {player2}: {player2_stats.get('breakpointsWonPercentage', 0)}% break points convertidos, {player2_stats.get('decidingSetWinPercentage', 0)}% sets decisivos ganados\n\n"
            
            # Tournament level breakdown
            resumen += f"**Por nivel de torneo:**\n"
            resumen += f"- Jugador {player1}: GS {player1_stats.get('grandSlam', 0)}, Masters {player1_stats.get('masters', 0)}, ATP {player1_stats.get('mainTour', 0)}\n"
            resumen += f"- Jugador {player2}: GS {player2_stats.get('grandSlam', 0)}, Masters {player2_stats.get('masters', 0)}, ATP {player2_stats.get('mainTour', 0)}\n\n"

        # Check if there are recent matches in raw_data
        raw_data = data.get('raw_data', {})
        if 'recentMatches' in raw_data and raw_data['recentMatches']:
            resumen += "**Últimos partidos:**\n"
            for match in raw_data['recentMatches']:
                date = match.get('date', 'N/A')
                tournament = match.get('tournament', 'N/A')
                winner = match.get('winner', 'N/A')
                score = match.get('score', 'N/A')
                surface = match.get('surface', 'N/A')
                resumen += f"- {date} | {tournament} | {winner} ganó {score} (Superficie: {surface})\n"
        else:
            resumen += "**Últimos partidos:** No hay información de partidos recientes disponible\n"

        return resumen
        
    except Exception as e:
        return f"Error al obtener historial H2H entre {player1} y {player2}: {str(e)}"

def get_injury_reports() -> str:
    try:
        data = fetch_injury_reports()
        if not data:
            return "No se encontraron registros de lesiones."
        
        result = []
        
        # Process injured players
        injured_players = data.get('injured_players', [])
        if injured_players:
            result.append("JUGADORES LESIONADOS:")
            for entry in injured_players:
                try:
                    player_name = entry.get('player_name', 'N/A')
                    reason = entry.get('reason', 'N/A')
                    date = entry.get('date', 'N/A')
                    tournament = entry.get('tournament', 'N/A')
                    result.append(f"- {player_name}: {reason} (Fecha: {date}, Torneo: {tournament})")
                except Exception as e:
                    result.append(f"- Error processing player data: {str(entry)}")
        
        # Process returning players
        returning_players = data.get('returning_players', [])
        if returning_players:
            result.append("\nJUGADORES EN REGRESO:")
            for entry in returning_players:
                try:
                    player_name = entry.get('player_name', 'N/A')
                    date = entry.get('date', 'N/A')
                    tournament = entry.get('tournament', 'N/A')
                    # Returning players don't have 'reason', they have 'status'
                    status = entry.get('status', 'returning from injury')
                    result.append(f"- {player_name}: {status} (Fecha: {date}, Torneo: {tournament})")
                except Exception as e:
                    result.append(f"- Error processing player data: {str(entry)}")
        
        if not result:
            return "No se encontraron registros de lesiones actuales."
        
        return "\n".join(result)
        
    except Exception as e:
        return f"Error al obtener reportes de lesiones: {str(e)}"
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


def get_tournaments(tournament: str, category: str) -> str:
    """
    Obtiene la lista de torneos de la API de tenis, extrae el id del torneo específico y lo devuelve,
    para que se pueda usar en el siguiente endpoint para obtener los datos del torneo.
    
    Args:
        tournament (str): Nombre del torneo a buscar
        category (str): Categoría de torneos (atpgs, atp, gs, 1000, ch)
    
    Returns:
        str: ID del torneo si se encuentra, mensaje de error si no se encuentra
    """
    # Usar el año 2025 para hacer la llamada a la API
    year = 2024
    
    # Obtener el ID del torneo específico
    tournament_id = fetch_tournament_info(tournament, year, category)
    
    if tournament_id:
        return f"ID del torneo '{tournament}': {tournament_id}"
    else:
        return f"No se encontró el torneo '{tournament}' en la categoría '{category}' para el año {year}."


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


def get_weather_forecast(tournament: str, fecha_hora: str, latitude: float, longitude: float) -> str:
    """
    Obtiene el pronóstico meteorológico para un partido específico.
    
    Args:
        tournament (str): Nombre del torneo
        fecha_hora (str): Fecha y hora del partido en formato "yyyy-mm-dd hh:mm"
        latitude (float): Latitud de la ubicación del torneo
        longitude (float): Longitud de la ubicación del torneo
    
    Returns:
        str: Reporte meteorológico formateado
    """
    
    weather_data = fetch_weather_forecast(latitude, longitude, fecha_hora, tournament)
    return format_weather_report(weather_data)

import random

def get_mock_weather_data(location: str) -> str:
    """
    Genera datos meteorológicos simulados realistas para pruebas.
    
    Args:
        location (str): Ubicación del torneo
    
    Returns:
        str: Reporte meteorológico simulado
    """
    # Simular diferentes condiciones meteorológicas
    weather_conditions = [
        {"description": "Despejado", "temp_max": (25, 32), "temp_min": (15, 22), "precip": (0, 1), "wind": (5, 15), "humidity": (40, 60)},
        {"description": "Parcialmente nublado", "temp_max": (22, 28), "temp_min": (12, 18), "precip": (0, 3), "wind": (8, 18), "humidity": (50, 70)},
        {"description": "Lluvia ligera", "temp_max": (18, 25), "temp_min": (10, 16), "precip": (2, 8), "wind": (10, 20), "humidity": (70, 85)},
        {"description": "Nublado", "temp_max": (20, 26), "temp_min": (12, 18), "precip": (1, 5), "wind": (8, 16), "humidity": (60, 75)},
        {"description": "Tormenta", "temp_max": (16, 22), "temp_min": (8, 14), "precip": (8, 20), "wind": (20, 35), "humidity": (80, 95)}
    ]
    
    condition = random.choice(weather_conditions)
    
    forecast = {
        "location": location,
        "temp_max": round(random.uniform(*condition["temp_max"]), 1),
        "temp_min": round(random.uniform(*condition["temp_min"]), 1),
        "precip": round(random.uniform(*condition["precip"]), 1),
        "wind": round(random.uniform(*condition["wind"]), 1),
        "humidity": round(random.uniform(*condition["humidity"]), 1),
        "description": condition["description"],
        "precipitation_prob": round(random.uniform(0, 100), 1) if condition["precip"][1] > 2 else 0
    }

    report = f"🌤️ **[SIMULADO] Pronóstico Meteorológico - {location}**\n\n"
    report += f"📊 **Condiciones Simuladas:**\n"
    report += f"• Temperatura máxima: {forecast['temp_max']}°C\n"
    report += f"• Temperatura mínima: {forecast['temp_min']}°C\n"
    report += f"• Precipitación: {forecast['precip']} mm\n"
    report += f"• Velocidad del viento: {forecast['wind']} km/h\n"
    report += f"• Humedad: {forecast['humidity']}%\n"
    report += f"• Probabilidad de lluvia: {forecast['precipitation_prob']}%\n"
    report += f"• Condiciones: {forecast['description']}\n\n"
    
    # Análisis para tenis
    report += "🎾 **Análisis para Tenis:**\n"
    
    temp_avg = (forecast['temp_max'] + forecast['temp_min']) / 2
    
    if temp_avg < 10:
        report += "• ⚠️ Temperatura baja - puede afectar el rendimiento\n"
    elif temp_avg > 35:
        report += "• ⚠️ Temperatura alta - riesgo de agotamiento\n"
    else:
        report += "• ✅ Temperatura óptima para el tenis\n"
    
    if forecast['precip'] > 5:
        report += "• ⚠️ Precipitación significativa - posible retraso\n"
    elif forecast['precip'] > 0:
        report += "• ⚠️ Lluvia ligera - condiciones húmedas\n"
    else:
        report += "• ✅ Sin precipitación - condiciones ideales\n"
    
    if forecast['wind'] > 20:
        report += "• ⚠️ Viento fuerte - puede afectar el juego\n"
    elif forecast['wind'] > 10:
        report += "• ⚠️ Viento moderado - condiciones variables\n"
    else:
        report += "• ✅ Viento suave - condiciones estables\n"
    
    return report
