# tennisAgents/graphs/conditional_logic.py

from tennisAgents.agents.utils.agent_states import AgentState
from tennisAgents.utils.enumerations import *


class ConditionalLogic:
    """Gestiona la lógica condicional para decidir el flujo del grafo."""

    def __init__(self, max_debate_rounds=1, max_risk_discuss_rounds=1):
        """Inicializa los parámetros de configuración."""
        self.max_debate_rounds = max_debate_rounds
        self.max_risk_discuss_rounds = max_risk_discuss_rounds

    def should_continue_match_analysis(self, state: AgentState):
        """Determina si el análisis de rendimiento en pista debe continuar."""
        messages = state["messages"]
        last_message = messages[-1]
        if last_message.tool_calls:
            return "tools_match"
        return "Msg Clear Match"

    def should_continue_social(self, state: AgentState):
        """Determina si el análisis de redes sociales debe continuar."""
        messages = state["messages"]
        last_message = messages[-1]
        if last_message.tool_calls:
            return "tools_social"
        return "Msg Clear Social"

    def should_continue_news(self, state: AgentState):
        """Determina si el análisis de noticias debe continuar."""
        messages = state["messages"]
        last_message = messages[-1]
        if last_message.tool_calls:
            return "tools_news"
        return "Msg Clear News"

    def should_continue_fundamentals(self, state: AgentState):
        """Determina si el análisis fundamental del jugador debe continuar."""
        messages = state["messages"]
        last_message = messages[-1]
        if last_message.tool_calls:
            return "tools_fundamentals"
        return "Msg Clear Fundamentals"

    def should_continue_risk_analysis(self, state: AgentState) -> str:
        """Determina si la discusión sobre el riesgo debe continuar."""
        if state["risk_debate_state"]["count"] >= 4 * self.max_risk_discuss_rounds:
            return ANALYSTS.judge

        last_speaker = state["risk_debate_state"].get("latest_speaker", "")

        if last_speaker == SPEAKERS.aggressive:
            return ANALYSTS.safe
        elif last_speaker == SPEAKERS.safe:
            return ANALYSTS.neutral
        elif last_speaker == SPEAKERS.neutral:
            return ANALYSTS.expected
        else:
            return ANALYSTS.aggressive

