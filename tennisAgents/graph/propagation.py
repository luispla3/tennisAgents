from typing import Dict, Any
from agents.utils.agent_states import (
    AgentState,
    InvestDebateState,
    RiskDebateState,
)


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
        surface: str,
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
            "investment_debate_state": InvestDebateState({
                "history": "",
                "current_response": "",
                "count": 0
            }),
            "risk_debate_state": RiskDebateState({
                "history": "",
                "current_risky_response": "",
                "current_safe_response": "",
                "current_neutral_response": "",
                "count": 0
            }),
            "player_stats_report": "",
            "opponent_stats_report": "",
            "head2head_report": "",
            "surface_analysis_report": "",
            "final_bet_decision": "",
        }

    def get_graph_args(self) -> Dict[str, Any]:
        """Devuelve los argumentos para la ejecución del grafo."""
        return {
            "stream_mode": "values",
            "config": {"recursion_limit": self.max_recur_limit},
        }
