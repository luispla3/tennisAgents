from typing import Annotated, Any, Optional

from langgraph.graph import MessagesState


class AgentState(MessagesState):
    match_date: Annotated[str, "Fecha del partido"]
    player_of_interest: Annotated[str, "Nombre del jugador principal"]
    opponent: Annotated[str, "Nombre del oponente"]
    tournament: Annotated[str, "Nombre del torneo"]
    wallet_balance: Annotated[float, "Saldo disponible de la cartera para apostar"]
    scraper_snapshot: Annotated[Optional[dict[str, Any]], "Snapshot actual de BetfairEnv"]
    context_path: Annotated[Optional[str], "Ruta al context.md persistente del partido"]
    step_index: Annotated[int, "Índice del timestep automatizado"]
    phase: Annotated[Optional[str], "Fase del partido"]
    score: Annotated[Optional[str], "Marcador actual"]
    current_set: Annotated[Optional[dict[str, Any]], "Set actual"]
    server: Annotated[Optional[str], "Jugador que saca"]
    game_score: Annotated[Optional[str], "Puntuación del juego actual"]
    elapsed_minutes: Annotated[Optional[float], "Minutos transcurridos"]
    previous_actions: Annotated[list[dict[str, Any]], "Decisiones anteriores"]
    open_positions: Annotated[list[dict[str, Any]], "Posiciones abiertas"]
    available_balance: Annotated[float, "Saldo disponible tras posiciones"]
    generalist_turns_log: Annotated[Optional[str], "Archivo de historial de decisiones del partido"]

    news_report: Annotated[Optional[str], "Informe de noticias"]
    players_report: Annotated[Optional[str], "Informe de jugadores"]
    sentiment_report: Annotated[Optional[str], "Informe de redes sociales"]
    weather_report: Annotated[Optional[str], "Informe de clima"]
    tournament_report: Annotated[Optional[str], "Informe de torneo"]

    final_bet_decision: Annotated[Optional[str], "Decisión final de apuesta"]
