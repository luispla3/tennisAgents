from typing import Dict, Any
from agents.utils.agent_states import (
    RiskDebateState,
)
from tennisAgents.utils.enumerations import *


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
    ) -> Dict[str, Any]:
        """Crea el estado inicial para el grafo de agentes deportivos."""
        return {
            "messages": [("human", f"Análisis del partido entre {player_name} y {opponent_name}")],
            "player_name": player_name,
            "opponent_name": opponent_name,
            "match_date": str(match_date),
            "surface": surface,
            "tournament": tournament,
            "risk_debate_state": RiskDebateState({
                HISTORYS.history: "",
                RESPONSES.aggressive: "",
                RESPONSES.safe: "",
                RESPONSES.neutral: "",
                RESPONSES.expected: "",
                "count": 0
            }),
            REPORTS.players_report: "",
            REPORTS.news_report: "",
            REPORTS.odds_report: "",
            REPORTS.sentiment_report: "",
            REPORTS.weather_report: "",
            REPORTS.tournament_report: "",
            REPORTS.risk_analysis_report: "",
            "final_bet_decision": "",
        }

    def get_graph_args(self) -> Dict[str, Any]:
        """Devuelve los argumentos para la ejecución del grafo."""
        return {
            "stream_mode": "values",
            "config": {"recursion_limit": self.max_recur_limit},
        }
