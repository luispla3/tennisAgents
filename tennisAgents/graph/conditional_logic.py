# tennis_agents/graphs/conditional_logic.py

from tennis_agents.agents.utils.agent_states import AgentState


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

    def should_continue_debate(self, state: AgentState) -> str:
        """Determina si el debate estratégico sobre la apuesta debe continuar."""

        if state["investment_debate_state"]["count"] >= 2 * self.max_debate_rounds:
            return "Match Strategy Manager"
        if state["investment_debate_state"]["current_response"].startswith("PlayerA"):
            return "PlayerB Analyst"
        return "PlayerA Analyst"

    def should_continue_risk_analysis(self, state: AgentState) -> str:
        """Determina si la discusión sobre el riesgo debe continuar."""
        if state["risk_debate_state"]["count"] >= 3 * self.max_risk_discuss_rounds:
            return "Risk Referee"
        if state["risk_debate_state"]["latest_speaker"].startswith("Aggressive"):
            return "Conservative Analyst"
        if state["risk_debate_state"]["latest_speaker"].startswith("Conservative"):
            return "Neutral Analyst"
        return "Aggressive Analyst"
