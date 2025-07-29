from tennisAgents.agents.utils.agent_states import AgentState
from tennisAgents.utils.enumerations import ANALYSTS, SPEAKERS, STATE

class ConditionalLogic:
    """Gestiona la lógica condicional para determinar el flujo del grafo de agentes."""

    def __init__(self, max_debate_rounds=1, max_risk_discuss_rounds=1):
        """Inicializa con parámetros de configuración."""
        self.max_debate_rounds = max_debate_rounds
        self.max_risk_discuss_rounds = max_risk_discuss_rounds

    def should_continue_news(self, state: AgentState):
        """Determina si el análisis de noticias debe continuar."""
        messages = state["messages"]
        last_message = messages[-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools_news"
        return "Msg Clear News"

    def should_continue_odds(self, state: AgentState):
        """Determina si el análisis de cuotas debe continuar."""
        messages = state["messages"]
        last_message = messages[-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools_odds"
        return "Msg Clear Odds"

    def should_continue_players(self, state: AgentState):
        """Determina si el análisis de jugadores debe continuar."""
        messages = state["messages"]
        last_message = messages[-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools_players"
        return "Msg Clear Players"

    def should_continue_social(self, state: AgentState):
        """Determina si el análisis de redes sociales debe continuar."""
        messages = state["messages"]
        last_message = messages[-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools_social"
        return "Msg Clear Social"

    def should_continue_tournament(self, state: AgentState):
        """Determina si el análisis de torneo debe continuar."""
        messages = state["messages"]
        last_message = messages[-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools_tournament"
        return "Msg Clear Tournament"

    def should_continue_weather(self, state: AgentState):
        """Determina si el análisis de clima debe continuar."""
        messages = state["messages"]
        last_message = messages[-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools_weather"
        return "Msg Clear Weather"

    def should_continue_risk_analysis(self, state: AgentState) -> str:
        """Determina el siguiente paso en el debate de riesgo."""
        risk_state = state.get(STATE.risk_debate_state, {})
        count = risk_state.get(STATE.count, 0)
        latest_speaker = risk_state.get(STATE.latest_speaker, "")

        # Finaliza el debate si se supera el número de rondas
        if count >= 3 * self.max_risk_discuss_rounds:
            return ANALYSTS.judge
        # Flujo entre analistas de riesgo según el último hablante
        if latest_speaker == SPEAKERS.aggressive:
            return ANALYSTS.safe
        if latest_speaker == SPEAKERS.safe:
            return ANALYSTS.expected
        if latest_speaker == SPEAKERS.expected:
            return ANALYSTS.neutral
        if latest_speaker == SPEAKERS.neutral:
            return ANALYSTS.aggressive
        return ANALYSTS.aggressive