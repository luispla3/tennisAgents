from openai import OpenAI
from dotenv import load_dotenv

from tennisAgents.dataflows.config import get_config

load_dotenv()


def fetch_injury_reports() -> str:
    """
    Gets injury reports using OpenAI instead of web scraping.
    
    Returns:
        String containing injury reports information
    """
    config = get_config()
    client = OpenAI(base_url=config["backend_url"])

    try:
        response = client.responses.create(
            model=config["quick_think_llm"],
            input=[
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "input_text",
                            "text": "Busca información actualizada sobre jugadores de tenis lesionados y jugadores que están regresando de lesiones. Incluye nombres, tipos de lesiones, fechas, torneos afectados, y estado actual de recuperación. Enfócate en jugadores relevantes del circuito ATP.",
                        }
                    ],
                }
            ],
            text={"format": {"type": "text"}},
            reasoning={},
            tools=[
                {
                    "type": "web_search_preview",
                    "user_location": {"type": "approximate"},
                    "search_context_size": "medium",
                }
            ],
            temperature=1,
            max_output_tokens=4096,
            top_p=1,
            store=True,
        )
        return response.output[1].content[0].text
    except Exception as e:
        return f"Error al obtener reportes de lesiones: {str(e)}"



def fetch_atp_rankings(player1_name: str, player2_name: str) -> str:
    """
    Obtiene el ranking ATP actual y el mejor ranking de carrera para ambos jugadores.
    
    Args:
        player1_name: Nombre del primer jugador
        player2_name: Nombre del segundo jugador
    
    Returns:
        String con información del ranking ATP de ambos jugadores
    """
    config = get_config()
    client = OpenAI(base_url=config["backend_url"])

    try:
        response = client.responses.create(
            model=config["quick_think_llm"],
            input=[
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "input_text",
                            "text": f"Busca en la pagina web de la ATP el ranking ATP actual y el mejor ranking de su carrera para ambos jugadores: {player1_name} y {player2_name}.",
                        }
                    ],
                }
            ],
            text={"format": {"type": "text"}},
            reasoning={},
            tools=[
                {
                    "type": "web_search_preview",
                    "user_location": {"type": "approximate"},
                    "search_context_size": "low",
                }
            ],
            temperature=1,
            max_output_tokens=4096,
            top_p=1,
            store=True,
        )
        return response.output[1].content[0].text
    except Exception as e:
        return f"Error al obtener rankings ATP: {str(e)}"



def fetch_recent_matches(player1_name: str, player2_name: str, num_matches: int = 30) -> str:
    """
    Obtiene los partidos recientes entre dos jugadores usando OpenAI.
    """
    config = get_config()
    client = OpenAI(base_url=config["backend_url"])

    try:
        response = client.responses.create(
            model=config["quick_think_llm"],
            input=[
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "input_text",
                            "text": f"Busca información sobre los últimos {num_matches} partidos jugados por {player1_name} y {player2_name}. Incluye fechas, torneos, resultados, superficies y estadísticas relevantes. Devuelve un análisis detallado de su rendimiento reciente.",
                        }
                    ],
                }
            ],
            text={"format": {"type": "text"}},
            reasoning={},
            tools=[
                {
                    "type": "web_search_preview",
                    "user_location": {"type": "approximate"},
                    "search_context_size": "medium",
                }
            ],
            temperature=1,
            max_output_tokens=4096,
            top_p=1,
            store=True,
        )
        return response.output[1].content[0].text
    except Exception as e:
        return f"Error al obtener partidos recientes: {str(e)}"



def fetch_surface_winrate(player_name: str, surface: str) -> str:
    """
    Devuelve el winrate de un jugador en una superficie dada usando OpenAI.
    """
    config = get_config()
    client = OpenAI(base_url=config["backend_url"])

    try:
        response = client.responses.create(
            model=config["quick_think_llm"],
            input=[
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "input_text",
                            "text": f"Busca estadísticas específicas sobre el rendimiento de {player_name} en superficie {surface} (clay, hard, grass). Incluye winrate, partidos ganados/perdidos, títulos, y rendimiento histórico en esta superficie. Devuelve datos cuantitativos y análisis cualitativo.",
                        }
                    ],
                }
            ],
            text={"format": {"type": "text"}},
            reasoning={},
            tools=[
                {
                    "type": "web_search_preview",
                    "user_location": {"type": "approximate"},
                    "search_context_size": "medium",
                }
            ],
            temperature=1,
            max_output_tokens=4096,
            top_p=1,
            store=True,
        )
        return response.output[1].content[0].text
    except Exception as e:
        return f"Error al obtener winrate en superficie: {str(e)}"


def fetch_head_to_head(player1_name: str, player2_name: str) -> str:
    """
    Devuelve las estadísticas head-to-head entre dos jugadores usando OpenAI.
    """
    config = get_config()
    client = OpenAI(base_url=config["backend_url"])

    try:
        response = client.responses.create(
            model=config["quick_think_llm"],
            input=[
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "input_text",
                            "text": f"Busca el historial completo de enfrentamientos (head-to-head) entre {player1_name} y {player2_name}. Incluye total de partidos, victorias de cada uno, fechas, torneos, superficies, y análisis de patrones en sus enfrentamientos. Devuelve estadísticas detalladas y contexto histórico.",
                        }
                    ],
                }
            ],
            text={"format": {"type": "text"}},
            reasoning={},
            tools=[
                {
                    "type": "web_search_preview",
                    "user_location": {"type": "approximate"},
                    "search_context_size": "medium",
                }
            ],
            temperature=1,
            max_output_tokens=4096,
            top_p=1,
            store=True,
        )
        return response.output[1].content[0].text
    except Exception as e:
        return f"Error al obtener head-to-head: {str(e)}"




