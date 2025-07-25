from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import MessagesState


# Estado del debate de gestión de riesgo
class RiskDebateState(TypedDict):
    risky_history: Annotated[str, "Risky Analyst's Conversation history"]
    safe_history: Annotated[str, "Safe Analyst's Conversation history"]
    neutral_history: Annotated[str, "Neutral Analyst's Conversation history"]
    expected_history: Annotated[str, "Expected Value Analyst's Conversation history"]
    history: Annotated[str, "Conversation history"]
    latest_speaker: Annotated[str, "Analyst that spoke last"]
    current_risky_response: Annotated[str, "Latest response by the risky analyst"]
    current_safe_response: Annotated[str, "Latest response by the safe analyst"]
    current_neutral_response: Annotated[str, "Latest response by the neutral analyst"]
    current_expected_response: Annotated[str, "Latest response by the expected value analyst"]
    judge_decision: Annotated[str, "Judge's decision"]
    count: Annotated[int, "Length of the current conversation"]


class AgentState(MessagesState):
    match_of_interest: Annotated[str, "Match we are analyzing for betting"]
    match_date: Annotated[str, "Date of the match"]

    sender: Annotated[str, "Agent that sent this message"]

    # Informes de los analistas
    news_report: Annotated[str, "Report from the News Analyst"]
    odds_report: Annotated[str, "Report from the Odds Analyst"]
    player_report: Annotated[str, "Report from the Player Analyst"]
    sentiment_report: Annotated[str, "Report from the Social Media Analyst"]
    tournament_report: Annotated[str, "Report from the Tournament Analyst"]
    weather_report: Annotated[str, "Report from the Weather Analyst"]
    
    # Estado del debate de gestión de riesgos
    risk_debate_state: Annotated[RiskDebateState, "Current state of the risk debate"]

    final_trade_decision: Annotated[str, "Final betting decision after the risk debate"]
