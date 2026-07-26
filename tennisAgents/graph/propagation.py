from typing import Dict, Any

from tennisAgents.dataflows.tournament_utils import (
    build_analyst_tournament_context,
    resolve_tournament_identity,
)
from tennisAgents.utils.enumerations import REPORTS, STATE


class Propagator:
    """Gestiona la inicialización y propagación del estado en el grafo de agentes."""

    def __init__(self, max_recur_limit=100):
        """Inicializa el propagador con un límite de recursión."""
        self.max_recur_limit = max_recur_limit

    def create_initial_state(
        self,
        player_name: str,
        opponent_name: str,
        match_date: str,
        tournament: str,
        wallet_balance: float,
        context_path: str | None = None,
        *,
        betfair_competition: str | None = None,
        flashscore_tournament: str | None = None,
    ) -> Dict[str, Any]:
        """Crea el estado inicial para el grafo de agentes deportivos."""
        tournament_identity = resolve_tournament_identity(
            betfair_competition=betfair_competition,
            flashscore_tournament=flashscore_tournament,
            stored=tournament,
        )
        tournament_context = build_analyst_tournament_context(
            tournament,
            betfair_competition=betfair_competition,
            flashscore_tournament=flashscore_tournament,
            stored=tournament,
        )
        return {
            STATE.messages: [("human", f"Análisis del partido entre {player_name} y {opponent_name}")],
            STATE.player_of_interest: player_name,
            STATE.opponent: opponent_name,
            STATE.match_date: str(match_date),
            STATE.tournament: tournament_identity.display_name,
            STATE.tournament_context: tournament_context,
            STATE.wallet_balance: wallet_balance,
            "scraper_snapshot": None,
            "context_path": context_path,
            "step_index": 0,
            "phase": "pre_match",
            "score": "",
            "current_set": None,
            "server": "",
            "game_score": "",
            "elapsed_minutes": None,
            "previous_actions": [],
            "open_positions": [],
            "available_balance": wallet_balance,
            "generalist_turns_log": None,
            "analyst_errors": {},
            "analysts_completed_count": 0,
            "analysts_expected_count": 0,
            "generalist_record": None,
            "generalist_error": None,
            "technical_fallback": False,
            "defer_generalist_persistence": False,
            REPORTS.players_report: "",
            REPORTS.news_report: "",
            REPORTS.sentiment_report: "",
            REPORTS.weather_report: "",
            REPORTS.tournament_report: "",
            STATE.final_bet_decision: "",
        }

    def get_graph_args(self) -> Dict[str, Any]:
        """Devuelve los argumentos para la ejecución del grafo."""
        return {
            "stream_mode": "values",
            "config": {"recursion_limit": self.max_recur_limit},
        }
