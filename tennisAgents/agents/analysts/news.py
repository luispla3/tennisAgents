from langchain_core.messages import AIMessage

from tennisAgents.agents.utils.prompt_anatomy import PromptBuilder, TennisAnalystAnatomies
from tennisAgents.dataflows.config import get_config
from tennisAgents.dataflows.news_utils import fetch_news_for_match
from tennisAgents.dataflows.tournament_utils import merge_analyst_tournament_context
from tennisAgents.agents.utils.report_utils import sanitize_analyst_report
from tennisAgents.utils.enumerations import *


def _emit_activity(analyst: str, message: str) -> None:
    callback = get_config().get("progress_callback")
    if callback:
        try:
            callback({"type": "analyst_activity", "analyst": analyst, "message": message})
        except Exception:
            pass


def create_news_analyst(llm, toolkit):
    def news_analyst_node(state):
        current_date = state[STATE.match_date]
        player = state[STATE.player_of_interest]
        opponent = state[STATE.opponent]
        tournament = state[STATE.tournament]

        print(f"\n{'=' * 80}", flush=True)
        print("NEWS ANALYST - Recopilando noticias", flush=True)
        print(f"{'=' * 80}", flush=True)
        print(f"Jugadores: {player} vs {opponent}", flush=True)
        print(f"Torneo: {tournament}", flush=True)

        _emit_activity("news", "Buscando noticias (Google News RSS + web)...")

        raw_news = fetch_news_for_match(player, opponent, tournament, current_date)
        print(f"[SUCCESS] Noticias recopiladas ({len(raw_news)} caracteres)", flush=True)

        _emit_activity("news", "Sintetizando informe con LLM...")

        anatomy = TennisAnalystAnatomies.news_analyst()
        additional_context = merge_analyst_tournament_context(
            state,
            (
            "OBJETIVO: Identificar información crítica que pueda influir en el rendimiento de los jugadores.\n"
            "Usa EXCLUSIVAMENTE las noticias proporcionadas en el mensaje del usuario.\n"
            "No inventes noticias ni pidas más búsquedas.\n"
            "PROHIBIDO usar tablas markdown en el informe final.\n\n"
            f"Fecha del partido: {current_date}. Jugadores: {player} vs {opponent}. Torneo: {tournament}."
            ),
        )

        prompt = PromptBuilder.create_structured_prompt(
            anatomy=anatomy,
            tools_info="",
            additional_context=additional_context,
        )

        chain = prompt | llm
        result = chain.invoke(
            {
                "messages": state[STATE.messages],
                "user_message": (
                    f"Analiza las noticias más relevantes sobre {player} y {opponent} "
                    f"para el torneo {tournament}.\n\n"
                    f"NOTICIAS RECOPILADAS:\n\n{raw_news}"
                ),
            }
        )

        report = sanitize_analyst_report(
            result.content if hasattr(result, "content") else str(result)
        )
        print("[OK] Reporte de noticias generado", flush=True)

        return {
            STATE.messages: [AIMessage(content=report)],
            REPORTS.news_report: report,
        }

    return news_analyst_node
