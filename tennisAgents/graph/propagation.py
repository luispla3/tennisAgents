# tennis_agents/graphs/propagation.py

from typing import Dict, Any
from tennis_agents.agents.utils.agent_states import (
    AgentState,
    InvestDebateState,
    RiskDebateState,
)


class Propagator:
    """Gestiona la inicialización y propagación del estado a lo largo del grafo."""

    def __init__(self, max_recur_limit=100):
        """Inicializa los parámetros de configuración."""
        self.max_recur_limit = max_recur_limit

    def create_initial_state(
        self, match_identifier: str, match_date: str
    ) -> Dict[str, Any]:
        """
        Crea el estado inicial del grafo de agentes.

        Args:
            match_identifier: string que representa el enfrentamiento entre jugadores.
            match_date: fecha del partido (str).
        """
        return {
            "messages": [("human", match_identifier)],
            "company_of_interest": match_identifier,  # mantenemos clave por compatibilidad
            "trade_date": str(match_date),
            "investment_debate_state": InvestDebateState(
                {"history": "", "current_response": "", "count": 0}
            ),
            "risk_debate_state": RiskDebateState(
                {
                    "history": "",
                    "current_risky_response": "",
                    "current_safe_response": "",
                    "current_neutral_response": "",
                    "count": 0,
                }
            ),
            "market_report": "",        # aquí representará rendimiento en pista
            "fundamentals_report": "",  # info histórica y técnica del jugador
            "sentiment_report": "",     # redes sociales, opiniones
            "news_report": "",          # contexto del torneo, lesiones, etc.
        }

    def get_graph_args(self) -> Dict[str, Any]:
        """Obtiene los argumentos para la ejecución del grafo."""
        return {
            "stream_mode": "values",
            "config": {"recursion_limit": self.max_recur_limit},
        }
