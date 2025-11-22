from typing import Annotated, Dict
from typing_extensions import TypedDict
from langgraph.graph import MessagesState
from typing import Optional, List, Any


# Estado del debate de gestión de riesgo
class RiskDebateState(TypedDict):
    aggressive_history: Annotated[
        str, "Aggressive Agent's Conversation history"
    ]  # Conversation history

    safe_history: Annotated[
        str, "Safe Agent's Conversation history"
    ]  # Conversation history

    neutral_history: Annotated[
        str, "Neutral Agent's Conversation history"
    ]  # Conversation history

    expected_history: Annotated[
        str, "Expected Value Agent's Conversation history"
    ]  # Conversation history

    history: Annotated[
        str, "Conversation history"
    ]  # Conversation history

    latest_speaker: Annotated[
        str, "Analyst that spoke last"
    ]

    current_risky_response: Annotated[
        str, "Latest response by the risky analyst"
    ]  # Last response

    current_safe_response: Annotated[
        str, "Latest response by the safe analyst"
    ]  # Last response

    current_neutral_response: Annotated[
        str, "Latest response by the neutral analyst"
    ]  # Last response

    judge_decision: Annotated[
        str, "Judge's decision"
    ]

    count: Annotated[
        int, "Length of the current conversation"
    ]  # Conversation length



class AgentState(MessagesState):
    match_date: Annotated[
        str, "Fecha del partido"
    ]

    player_of_interest: Annotated[
        str, "Nombre del jugador principal"
    ]

    opponent: Annotated[
        str, "Nombre del oponente"
    ]

    tournament: Annotated[
        str, "Nombre del torneo"
    ]

    wallet_balance: Annotated[
        float, "Saldo disponible de la cartera para apostar"
    ]

    # Todos los REPORTS
    news_report: Annotated[
        Optional[str], "Informe de noticias"
    ]

    odds_report: Annotated[
        Optional[str], "Informe de cuotas"
    ]

    players_report: Annotated[
        Optional[str], "Informe de jugadores"
    ]

    sentiment_report: Annotated[
        Optional[str], "Informe de redes sociales"
    ]

    weather_report: Annotated[
        Optional[str], "Informe de clima"
    ]

    tournament_report: Annotated[
        Optional[str], "Informe de torneo"
    ]

    match_live_report: Annotated[
        Optional[str], "Informe de partido en vivo"
    ]

    # Decisión final
    final_bet_decision: Annotated[
        Optional[str], "Decisión final de apuesta"
    ]

    # Decisiones individuales de cada risk manager (para medir rendimiento)
    individual_risk_manager_decisions: Annotated[
        Optional[Dict[str, str]], "Decisiones individuales de cada risk manager por modelo"
    ]

    # Estado del debate de riesgo
    risk_debate_state: Annotated[
        RiskDebateState, "Estado del debate de gestión de riesgo"
    ]


