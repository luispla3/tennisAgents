from langchain_core.messages import AIMessage

from tennisAgents.dataflows.config import get_config
from tennisAgents.utils.enumerations import REPORTS, STATE

GENERALIST_NODE = "generalist_llm"


def _emit_progress(event: dict) -> None:
    """Emite eventos de progreso al callback configurado."""
    callback = get_config().get("progress_callback")
    if callback:
        try:
            callback(event)
        except Exception:
            pass


def _collect_analyst_reports(state: dict) -> str:
    """Recopila los informes de analistas disponibles en el estado."""
    sections = []
    for key in (
        REPORTS.news_report,
        REPORTS.odds_report,
        REPORTS.players_report,
        REPORTS.sentiment_report,
        REPORTS.tournament_report,
        REPORTS.weather_report,
        REPORTS.match_live_report,
    ):
        content = state.get(key)
        if content:
            title = key.replace("_report", "").replace("_", " ").upper()
            sections.append(f"## {title}\n\n{content}")
    return "\n\n---\n\n".join(sections) if sections else "Sin informes de analistas disponibles."


def create_generalist_llm(deep_thinking_llm):
    """Nodo generalista: genera final_bet_decision a partir de los informes de analistas."""

    def generalist_llm_node(state):
        """Genera la decisión final de apuesta a partir de los informes de analistas."""
        print(f"\n{'=' * 80}", flush=True)
        print("GENERALIST LLM - Generando decisión final", flush=True)
        print(f"{'=' * 80}", flush=True)

        _emit_progress({"type": "generalist_start"})

        player = state.get(STATE.player_of_interest, "")
        opponent = state.get(STATE.opponent, "")
        tournament = state.get(STATE.tournament, "")
        match_date = state.get(STATE.match_date, "")
        wallet_balance = state.get(STATE.wallet_balance, 0)
        analyst_reports = _collect_analyst_reports(state)

        # TODO: definir prompt final, tools y formato estructurado de la decisión.
        prompt = (
            "Eres el agente generalista del sistema de apuestas de tenis.\n"
            "Tu tarea es leer los informes de los analistas y generar la decisión final de apuesta.\n"
            "Responde en markdown. El contenido se guardará en final_bet_decision.md.\n\n"
            f"Partido: {player} vs {opponent}\n"
            f"Torneo: {tournament}\n"
            f"Fecha: {match_date}\n"
            f"Saldo disponible: {wallet_balance}\n\n"
            f"INFORMES DE ANALISTAS:\n\n{analyst_reports}"
        )

        try:
            response = deep_thinking_llm.invoke(prompt)
            decision = response.content if hasattr(response, "content") else str(response)
        except Exception as exc:
            decision = f"Error al generar la decisión final: {exc}"
            print(f"✗ Error en generalist_llm: {exc}", flush=True)

        print("✅ Decisión final generada por generalist_llm", flush=True)
        _emit_progress({"type": "generalist_complete", "decision": decision})

        return {
            STATE.messages: [AIMessage(content=decision)],
            STATE.final_bet_decision: decision,
        }

    return generalist_llm_node
