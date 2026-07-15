from dotenv import load_dotenv

from tennisAgents.dataflows.llm_utils import invoke_chat_llm
from tennisAgents.dataflows.atp_h2h_utils import format_atp_h2h_report
from tennisAgents.dataflows.tennis_abstract_utils import (
    format_profiles_report,
    format_recent_matches_report,
    format_surface_report,
)
from tennisAgents.dataflows.flashscore_scraper.injuries import format_injury_reports
from tennisAgents.dataflows.web_search_utils import perform_web_search

load_dotenv()


def _llm_with_web_search(system_prompt: str, search_query: str) -> str:
    search_context = perform_web_search(search_query)
    user_content = (
        "Usa los siguientes resultados de búsqueda web para elaborar tu respuesta. "
        "Cita fuentes cuando sea posible.\n\n"
        f"{search_context}"
    )
    return invoke_chat_llm(system_prompt, user_content)


def fetch_injury_reports(player1_name: str, player2_name: str) -> str:
    try:
        return format_injury_reports(player1_name, player2_name)
    except Exception as e:
        return f"Error al obtener reportes de lesiones: {str(e)}"


def fetch_atp_rankings(player1_name: str, player2_name: str) -> str:
    try:
        profile_report = format_profiles_report(player1_name, player2_name)
        if profile_report:
            return profile_report

        return _llm_with_web_search(
            f"Resume el ranking ATP actual y el mejor ranking de carrera de {player1_name} "
            f"y {player2_name}. No inventes datos si no aparecen en las fuentes.",
            f"ATP ranking {player1_name} {player2_name} career high current ranking",
        )
    except Exception as e:
        return f"Error al obtener rankings ATP: {str(e)}"


def fetch_recent_matches(player1_name: str, player2_name: str, num_matches: int = 30) -> str:
    try:
        report = format_recent_matches_report(player1_name, player2_name, num_matches)
        if report:
            return report

        return _llm_with_web_search(
            f"Analiza los últimos {num_matches} partidos de {player1_name} y {player2_name}. "
            "Incluye solo datos presentes en los resultados web. "
            "Si no hay fechas/resultados concretos, dilo explícitamente y no infieras tendencias.",
            (
                f"{player1_name} {player2_name} recent tennis matches results last {num_matches} "
                "Tennis Abstract Flashscore ATP"
            ),
        )
    except Exception as e:
        return f"Error al obtener partidos recientes: {str(e)}"


def fetch_surface_winrate(player_name: str, surface: str) -> str:
    try:
        from tennisAgents.dataflows.tournament_utils import resolve_tournament_surface

        candidates: list[str] = []
        for value in (surface, resolve_tournament_surface(surface)):
            if value and value not in candidates:
                candidates.append(value)

        report = ""
        for candidate in candidates:
            report = format_surface_report(player_name, candidate)
            skip_web_search_markers = (
                "No hay estadísticas",
                "No se encontró perfil",
                "Error al consultar",
            )
            if report and not any(marker in report for marker in skip_web_search_markers):
                return report

        skip_web_search_markers = (
            "No hay estadísticas",
            "No se encontró perfil",
            "Error al consultar",
        )
        if report and not any(marker in report for marker in skip_web_search_markers):
            return report

        return _llm_with_web_search(
            f"Resume el rendimiento de {player_name} en superficie {surface}. "
            "Incluye solo winrate, títulos o métricas cuantitativas presentes en los resultados. "
            "No inventes porcentajes ni estadísticas si no aparecen en las fuentes.",
            f"{player_name} tennis win rate stats {surface} court surface Tennis Abstract Ultimate Tennis Statistics",
        )
    except Exception as e:
        return f"Error al obtener winrate en superficie: {str(e)}"


def fetch_head_to_head(player1_name: str, player2_name: str) -> str:
    try:
        report = format_atp_h2h_report(player1_name, player2_name)
        if report and "Error al consultar" not in report:
            return report

        return _llm_with_web_search(
            f"Resume el historial head-to-head entre {player1_name} y {player2_name}. "
            "Si no aparece un H2H explícito en las fuentes, responde que no hay H2H confirmado.",
            f"{player1_name} vs {player2_name} head to head tennis record ATP Tour",
        )
    except Exception as e:
        return f"Error al obtener head-to-head: {str(e)}"
