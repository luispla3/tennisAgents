from tennisAgents.agents.utils.agent_states import AgentState
from tennisAgents.utils.enumerations import STATE


class ConditionalLogic:
    """Gestiona la lógica condicional para determinar el flujo del grafo de agentes."""

    def should_continue_news(self, state: AgentState):
        """Determina si el análisis de noticias debe continuar."""
        messages = state[STATE.messages]
        last_message = messages[-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools_news"
        return "Msg Clear News"

    def should_continue_odds(self, state: AgentState):
        """Determina si el análisis de cuotas debe continuar."""
        messages = state[STATE.messages]
        last_message = messages[-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools_odds"
        return "Msg Clear Odds"

    def should_continue_players(self, state: AgentState):
        """Determina si el análisis de jugadores debe continuar."""
        messages = state[STATE.messages]
        last_message = messages[-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools_players"
        return "Msg Clear Players"

    def should_continue_social(self, state: AgentState):
        """Determina si el análisis de redes sociales debe continuar."""
        messages = state[STATE.messages]
        last_message = messages[-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools_social"
        return "Msg Clear Social"

    def should_continue_tournament(self, state: AgentState):
        """Determina si el análisis de torneo debe continuar."""
        messages = state[STATE.messages]
        last_message = messages[-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools_tournament"
        return "Msg Clear Tournament"

    def should_continue_weather(self, state: AgentState):
        """Determina si el análisis de clima debe continuar."""
        messages = state[STATE.messages]
        last_message = messages[-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools_weather"
        return "Msg Clear Weather"

    def should_continue_match_live(self, state: AgentState):
        """Determina si el análisis de partido en vivo debe continuar."""
        messages = state[STATE.messages]
        last_message = messages[-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools_match_live"
        return "Msg Clear Match_live"
