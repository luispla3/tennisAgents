from dotenv import load_dotenv

from tennisAgents.dataflows.config import get_config
from tennisAgents.dataflows.llm_utils import get_llm_client
from tennisAgents.dataflows.web_search_utils import perform_web_search

load_dotenv()


def _llm_with_web_search(system_prompt: str, search_query: str) -> str:
    client = get_llm_client()
    config = get_config()
    search_context = perform_web_search(search_query)

    response = client.chat.completions.create(
        model=config["quick_think_llm"],
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": (
                    "Usa los siguientes resultados de búsqueda web para elaborar tu respuesta. "
                    "Cita fuentes cuando sea posible.\n\n"
                    f"{search_context}"
                ),
            },
        ],
        temperature=1,
        max_tokens=4096,
    )
    return response.choices[0].message.content or ""


def fetch_injury_reports() -> str:
    try:
        return _llm_with_web_search(
            "Eres un analista deportivo especializado en tenis. Resume lesiones recientes, "
            "recuperaciones y bajas relevantes del circuito ATP/WTA.",
            "tennis ATP WTA injury reports players returning from injury 2025",
        )
    except Exception as e:
        return f"Error al obtener reportes de lesiones: {str(e)}"


def fetch_atp_rankings(player1_name: str, player2_name: str) -> str:
    try:
        return _llm_with_web_search(
            f"Resume el ranking ATP actual y el mejor ranking de carrera de {player1_name} "
            f"y {player2_name}.",
            f"ATP ranking {player1_name} {player2_name} career high current ranking",
        )
    except Exception as e:
        return f"Error al obtener rankings ATP: {str(e)}"


def fetch_recent_matches(player1_name: str, player2_name: str, num_matches: int = 30) -> str:
    try:
        return _llm_with_web_search(
            f"Analiza los últimos {num_matches} partidos de {player1_name} y {player2_name}. "
            "Incluye fechas, torneos, resultados, superficies y tendencias.",
            f"{player1_name} {player2_name} recent tennis matches results last {num_matches} matches",
        )
    except Exception as e:
        return f"Error al obtener partidos recientes: {str(e)}"


def fetch_surface_winrate(player_name: str, surface: str) -> str:
    try:
        return _llm_with_web_search(
            f"Resume el rendimiento de {player_name} en superficie {surface}. "
            "Incluye winrate, títulos y datos cuantitativos.",
            f"{player_name} tennis win rate stats {surface} court surface",
        )
    except Exception as e:
        return f"Error al obtener winrate en superficie: {str(e)}"


def fetch_head_to_head(player1_name: str, player2_name: str) -> str:
    try:
        return _llm_with_web_search(
            f"Resume el historial head-to-head entre {player1_name} y {player2_name}.",
            f"{player1_name} vs {player2_name} head to head tennis record",
        )
    except Exception as e:
        return f"Error al obtener head-to-head: {str(e)}"
