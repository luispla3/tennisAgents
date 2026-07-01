from typing import Annotated, Optional

from langgraph.graph import MessagesState


class AgentState(MessagesState):
    match_date: Annotated[str, "Fecha del partido"]
    player_of_interest: Annotated[str, "Nombre del jugador principal"]
    opponent: Annotated[str, "Nombre del oponente"]
    tournament: Annotated[str, "Nombre del torneo"]
    wallet_balance: Annotated[float, "Saldo disponible de la cartera para apostar"]

    news_report: Annotated[Optional[str], "Informe de noticias"]
    players_report: Annotated[Optional[str], "Informe de jugadores"]
    sentiment_report: Annotated[Optional[str], "Informe de redes sociales"]
    weather_report: Annotated[Optional[str], "Informe de clima"]
    tournament_report: Annotated[Optional[str], "Informe de torneo"]

    final_bet_decision: Annotated[Optional[str], "Decisión final de apuesta"]
