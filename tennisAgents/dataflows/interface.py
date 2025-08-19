from tennisAgents.dataflows.config import get_config
from .news_utils import fetch_news
from .tournament_utils import get_tournament_surface as get_tournament_surface_impl
from .odds_utils import fetch_tennis_odds, generate_mock_odds
from .odds_utils import generate_mock_odds
from .player_utils import fetch_atp_rankings
from .player_utils import fetch_recent_matches
from .player_utils import fetch_surface_winrate
from .player_utils import fetch_head_to_head
from .player_utils import fetch_injury_reports
from .sentiment_utils import get_sentiment_openai
from .tournament_utils import get_tournament_info_openai
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
    result = fetch_atp_rankings()

    if not result or result.startswith("Error"):
        return "No se pudo obtener el ranking ATP."

    #debug
    print(f"[DEBUG] Resultado de get_atp_rankings: {result}")
    
    return result


def get_recent_matches(player1_name: str, player2_name: str, num_matches: int = 30) -> str:
    """
     Devuelve los últimos partidos jugados entre dos jugadores específicos.
     Usa OpenAI para obtener la información.
    """
    result = fetch_recent_matches(player1_name, player2_name, num_matches)
    
    if not result or result.startswith("Error"):
        return f"No se encontraron partidos recientes entre {player1_name} y {player2_name}."

    #debug
    print(f"[DEBUG] Resultado de get_recent_matches: {result}")
    return result


def get_surface_winrate(player_name: str, surface: str) -> str:
    """
    Devuelve el porcentaje de victorias del jugador en una superficie específica.
    Usa OpenAI para obtener la información.
    """
    result = fetch_surface_winrate(player_name, surface)

    if not result or result.startswith("Error"):
        return f"No se encontraron datos sobre {player_name} en {surface}."

    #debug
    print(f"[DEBUG] Resultado de get_surface_winrate: {result}")
    return result


def get_head_to_head(player1_name: str, player2_name: str) -> str:
    """
    Devuelve las estadísticas H2H entre dos jugadores de tenis.
    Usa OpenAI para obtener la información.
    """
    try:
        result = fetch_head_to_head(player1_name, player2_name)

        if not result or result.startswith("Error"):
            return f"No se encontró historial H2H entre {player1_name} y {player2_name}."

        return result
        
    except Exception as e:
        return f"Error al obtener historial H2H entre {player1_name} y {player2_name}: {str(e)}"

def get_injury_reports() -> str:
    try:
        result = fetch_injury_reports()
        if not result or result.startswith("Error"):
            return "No se encontraron registros de lesiones."
        
        #debug
        print(f"[DEBUG] Resultado de get_injury_reports: {result}")
        
        return result
        
    except Exception as e:
        return f"Error al obtener reportes de lesiones: {str(e)}"
    
def get_sentiment(player_name: str) -> str:
    return get_sentiment_openai(player_name)


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


def get_tournament_data(tournament: str, category: str, date: str) -> str:
    """
    Obtiene la lista de torneos de la API de tenis, extrae el id del torneo específico y lo devuelve,
    para que se pueda usar en el siguiente endpoint para obtener los datos del torneo.
    
    Args:
        tournament (str): Nombre del torneo a buscar
        category (str): Categoría de torneos (atpgs, atp, gs, 1000, ch)
        date (str): Fecha del torneo en formato "yyyy-mm-dd"
    
    Returns:
        str: ID del torneo si se encuentra, mensaje de error si no se encuentra
    """
    
    response = get_tournament_info_openai(tournament, category, date)

    return response
    
    


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
