import json
from typing import Annotated

from langchain_core.messages import AIMessage
from langchain_core.tools import tool

from tennisAgents.dataflows.config import get_config
from tennisAgents.utils.enumerations import REPORTS, STATE

GENERALIST_NODE = "generalist_llm"


def _tool_log(action: str, **data) -> str:
    return json.dumps({"status": "logged", "action": action, **data}, ensure_ascii=False)


@tool
def Bet(
    match_id: Annotated[str, "Identificador del partido"],
    market: Annotated[str, "Mercado de la apuesta, por ejemplo match_winner"],
    selection: Annotated[str, "Selección apostada"],
    stake: Annotated[float, "Importe de la apuesta"],
    rationale: Annotated[str, "Motivo breve de la apuesta"],
    confidence: Annotated[float, "Confianza entre 0 y 1"],
) -> str:
    """Registra una apuesta."""
    return _tool_log("Bet", match_id=match_id, market=market, selection=selection, stake=stake, rationale=rationale, confidence=confidence)


@tool
def Wait(
    match_id: Annotated[str, "Identificador del partido"],
    rationale: Annotated[str, "Motivo breve para no actuar"],
    confidence: Annotated[float, "Confianza entre 0 y 1"],
    next_trigger: Annotated[str, "Condición que haría reconsiderar la decisión"] = "",
) -> str:
    """Registra que se decide esperar sin hacer nada."""
    return _tool_log("Wait", match_id=match_id, rationale=rationale, confidence=confidence, next_trigger=next_trigger)


@tool
def Close(
    match_id: Annotated[str, "Identificador del partido"],
    close_percentage: Annotated[float, "Porcentaje de cierre, de 0 a 1"],
    rationale: Annotated[str, "Motivo breve del cierre"],
    confidence: Annotated[float, "Confianza entre 0 y 1"],
) -> str:
    """Registra el cierre de una apuesta."""
    return _tool_log("Close", match_id=match_id, close_percentage=close_percentage, rationale=rationale, confidence=confidence)


GENERALIST_TOOLS = [Bet, Wait, Close]
GENERALIST_TOOL_MAP = {t.name: t for t in GENERALIST_TOOLS}


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


def _call_data(tool_call):
    return tool_call if isinstance(tool_call, dict) else {"name": tool_call.name, "args": tool_call.args, "id": getattr(tool_call, "id", None)}


def _fallback_wait(match_id: str) -> AIMessage:
    return AIMessage(content="", tool_calls=[{"name": "Wait", "args": {"match_id": match_id, "rationale": "El modelo no ejecutó una tool call válida; se espera por seguridad.", "confidence": 0, "next_trigger": "Nueva señal clara de valor."}, "id": "fallback_wait"}])


def _execute_tool_call(tool_call) -> str:
    call = _call_data(tool_call)
    name, args = call["name"], call.get("args", {})
    result = GENERALIST_TOOL_MAP[name].invoke(args)
    return json.dumps({"tool": name, "args": args, "result": json.loads(result)}, ensure_ascii=False, indent=2)


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
        match_id = f"{player} vs {opponent} | {tournament} | {match_date}"
        
        # TODO: definir prompt final, tools y formato estructurado de la decisión.
        prompt = (
            "Eres el agente generalista del sistema de apuestas de tenis.\n"
            "Lee los informes y termina ejecutando exactamente una tool call: Bet, Wait o Close.\n"
            "No escribas informe final, markdown ni texto adicional. Si no hay valor claro o faltan cuotas fiables, usa Wait.\n\n"
            f"match_id: {match_id}\n"
            f"Partido: {player} vs {opponent}\n"
            f"Torneo: {tournament}\n"
            f"Fecha: {match_date}\n"
            f"Saldo disponible: {wallet_balance}\n\n"
        )

        try:
            try:
                response = deep_thinking_llm.bind_tools(GENERALIST_TOOLS, tool_choice="any").invoke(prompt)
            except Exception:
                response = deep_thinking_llm.bind_tools(GENERALIST_TOOLS).invoke(prompt)
            if not getattr(response, "tool_calls", None):
                response = _fallback_wait(match_id)
            tool_call = response.tool_calls[0]
            response = AIMessage(content="", tool_calls=[tool_call])
            decision = _execute_tool_call(tool_call)
        except Exception as exc:
            response = _fallback_wait(match_id)
            decision = _execute_tool_call(response.tool_calls[0])
            decision = json.dumps({"tool": "Wait", "args": response.tool_calls[0]["args"], "error": str(exc), "result": json.loads(decision)["result"]}, ensure_ascii=False, indent=2)
            print(f"✗ Error en generalist_llm: {exc}", flush=True)

        print("✅ Decisión final generada por generalist_llm", flush=True)
        _emit_progress({"type": "generalist_complete", "decision": decision})

        return {
            STATE.messages: [response],
            STATE.final_bet_decision: decision,
        }

    return generalist_llm_node
