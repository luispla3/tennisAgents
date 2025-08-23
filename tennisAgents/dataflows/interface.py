from tennisAgents.dataflows.config import get_config
from .odds_utils import fetch_tennis_odds, mock_tennis_odds as fetch_mock_odds
from .match_live_utils import fetch_match_live_data, format_match_live_report, mock_match_live_data, format_mock_match_live_report
from .news_utils import fetch_news
from .player_utils import fetch_atp_rankings, fetch_recent_matches, fetch_surface_winrate, fetch_head_to_head, fetch_injury_reports
from .weather_utils import fetch_weather_forecast, format_weather_report
from .sentiment_utils import get_sentiment_openai
from .tournament_utils import get_tournament_info_openai



# NEWS ANALYST TOOLS


def get_news(query: str, curr_date: str) -> str:
    """
    Interfaz que prepara y formatea las noticias obtenidas desde Google News.
    """
    noticias = fetch_news(query, curr_date)

    if not noticias:
        result = f"No se encontraron noticias sobre '{query}' para la fecha {curr_date}."
        return result
    
    return noticias


# ODDS ANALYST TOOLS


def get_tennis_odds(player_a: str, player_b: str, tournament: str) -> str:
    """
    Consulta las cuotas de apuestas de Betfair para un partido específico usando OpenAI.
    """
    odds_data = fetch_tennis_odds(player_a, player_b, tournament)
    
    if not odds_data or odds_data.get("success") == False:
        error_msg = odds_data.get("error", "Error desconocido") if odds_data else "No se pudieron obtener datos"
        result = f"Error al obtener cuotas para {player_a} vs {player_b} en {tournament}: {error_msg}"
        return result
    
    # Formatear los datos de cuotas
    result = f"## Cuotas de Apuestas - {tournament}\n\n"
    result += f"**Partido:** {player_a} vs {player_b}\n\n"
    
    # Mostrar cada mercado disponible
    for market_name, market_data in odds_data.items():
        if market_name in ["success", "fetched_at"]:
            continue
            
        result += f"### {market_name}\n"
        
        if market_data == "No disponible":
            result += "**Estado:** No disponible para este partido\n\n"
        elif isinstance(market_data, dict):
            for key, value in market_data.items():
                result += f"**{key}:** {value}\n"
            result += "\n"
        else:
            result += f"**Cuota:** {market_data}\n\n"
    
    result += f"\n**Obtenido el:** {odds_data.get('fetched_at', 'N/A')}\n"
    
    return result


def mock_tennis_odds(player_a: str, player_b: str, tournament: str) -> str:
    """
    Genera cuotas ficticias de apuestas para un partido específico.
    """
    odds_data = fetch_mock_odds(player_a, player_b, tournament)
    
    if not odds_data or odds_data.get("success") == False:
        error_msg = odds_data.get("error", "Error desconocido") if odds_data else "No se pudieron generar datos"
        result = f"Error al generar cuotas ficticias para {player_a} vs {player_b} en {tournament}: {error_msg}"
        return result
    
    # Formatear los datos de cuotas ficticias
    result = f"## Cuotas de Apuestas (Ficticias) - {tournament}\n\n"
    result += f"**Partido:** {player_a} vs {player_b}\n\n"
    result += f"**Favorito:** {odds_data.get('favorite', 'N/A')}\n"
    result += f"**Underdog:** {odds_data.get('underdog', 'N/A')}\n\n"
    
    # Mostrar cada mercado disponible
    for market_name, market_data in odds_data.items():
        if market_name in ["success", "fetched_at", "player_a", "player_b", "tournament", "favorite", "underdog", "note"]:
            continue
            
        result += f"### {market_name}\n"
        
        if market_data == "No disponible":
            result += "**Estado:** No disponible para este partido\n\n"
        elif isinstance(market_data, dict):
            for key, value in market_data.items():
                result += f"**{key}:** {value}\n"
            result += "\n"
        else:
            result += f"**Cuota:** {market_data}\n\n"
    
    result += f"\n**Obtenido el:** {odds_data.get('fetched_at', 'N/A')}\n"
    result += f"\n**Nota:** {odds_data.get('note', '')}\n"
    
    return result


# PLAYER ANALYST TOOLS

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


# TOURNAMENT ANALYST TOOLS


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
    

def get_weather_forecast(tournament: str, fecha_hora: str, location: str) -> str:
    """
    Obtiene el pronóstico meteorológico para un partido específico.
    
    Args:
        tournament (str): Nombre del torneo
        fecha_hora (str): Fecha y hora del partido en formato "yyyy-mm-dd hh:mm"
        location (str): Ubicación del torneo (ciudad, país, etc.)
    
    Returns:
        str: Reporte meteorológico formateado
    """
    
    weather_data = fetch_weather_forecast(location, fecha_hora, tournament)
    return format_weather_report(weather_data)


# MATCH LIVE ANALYST TOOLS


def get_match_live_data(player_a: str, player_b: str, tournament: str) -> str:
    """
    Obtiene datos en tiempo real del partido actual incluyendo score, estadísticas y momentum.
    
    Args:
        player_a (str): Nombre del primer jugador
        player_b (str): Nombre del segundo jugador
        tournament (str): Nombre del torneo
    
    Returns:
        str: Reporte en tiempo real del partido con estadísticas y análisis
    """
    
    try:
        # Obtener datos del partido usando las utilidades
        match_data = fetch_match_live_data(player_a, player_b, tournament)
        
        if not match_data or match_data.get("success") == False:
            return f"Error al obtener datos del partido en vivo entre {player_a} y {player_b} en {tournament}."
        
        # Formatear el reporte
        result = format_match_live_report(match_data)
        
        return result
        
    except Exception as e:
        return f"Error al obtener datos del partido en vivo: {str(e)}"


def get_mock_match_live_data(player_a: str, player_b: str, tournament: str) -> str:
    """
    Genera datos ficticios de partido en vivo para un partido específico.
    
    Args:
        player_a (str): Nombre del primer jugador
        player_b (str): Nombre del segundo jugador
        tournament (str): Nombre del torneo
    
    Returns:
        str: Reporte en tiempo real ficticio del partido con estadísticas y análisis
    """
    
    try:
        # Obtener datos ficticios del partido usando las utilidades
        match_data = mock_match_live_data(player_a, player_b, tournament)
        
        if not match_data or match_data.get("success") == False:
            return f"Error al generar datos ficticios del partido en vivo entre {player_a} y {player_b} en {tournament}."
        
        # Formatear el reporte
        result = format_mock_match_live_report(match_data)
        
        return result
        
    except Exception as e:
        return f"Error al generar datos ficticios del partido en vivo: {str(e)}"