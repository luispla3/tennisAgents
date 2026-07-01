import json
import re
from datetime import datetime
from pathlib import Path
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
GENERALIST_TOOL_MAP.update({t.name.lower(): t for t in GENERALIST_TOOLS})
REPORT_ORDER = (REPORTS.players_report, REPORTS.news_report, REPORTS.sentiment_report, REPORTS.tournament_report, REPORTS.weather_report)


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
        REPORTS.players_report,
        REPORTS.sentiment_report,
        REPORTS.tournament_report,
        REPORTS.weather_report,
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


def _execute_tool_call(tool_call) -> dict:
    call = _call_data(tool_call)
    name, args = call["name"], call.get("args", {})
    result = GENERALIST_TOOL_MAP[name].invoke(args)
    return json.loads(result)


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(value).lower()).strip("-") or "unknown"


def _num(value, default=None):
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return default


def _market_snapshot(state: dict, captured_at: str) -> dict:
    """Construye snapshot de mercado vacío; las cuotas ya no vienen de un analista dedicado."""
    return {"source": "none", "captured_at": captured_at, "markets": []}


def _match_live_state(state: dict) -> dict:
    """Extrae el estado en vivo disponible directamente en el state del grafo."""
    return {
        "phase": state.get("phase") or "pre_match",
        "score": state.get("score") or "",
        "current_set": state.get("current_set"),
        "server": state.get("server", ""),
        "game_score": state.get("game_score", ""),
        "elapsed_minutes": state.get("elapsed_minutes"),
    }


def _target_call(tool_call, snapshot: dict) -> dict:
    call = _call_data(tool_call)
    args = call.get("args", {})
    name = call["name"].lower()
    reason = args.get("reason") or args.get("rationale") or ""
    if name == "bet":
        option, market = args.get("option") or args.get("selection", ""), args.get("market", "")
        return {"name": "bet", "arguments": {"market": market, "option": option, "stake": _num(args.get("stake"), 0.0), "odds": _num(args.get("odds")), "reason": reason}}
    if name == "close":
        return {"name": "close", "arguments": {"position_id": args.get("position_id", ""), "close_percentage": _num(args.get("close_percentage"), 1.0), "reason": reason}}
    return {"name": "wait", "arguments": {"reason": reason}}


def _turn_log(state: dict, tool_call) -> dict:
    ts = datetime.now().astimezone().isoformat(timespec="seconds")
    player, opponent, date = state.get(STATE.player_of_interest, ""), state.get(STATE.opponent, ""), state.get(STATE.match_date, "")
    previous, positions = state.get("previous_actions") or [], state.get("open_positions") or []
    step = int(state.get("step_index", len(previous)))
    trajectory_id = f"match_{date}_{_slug(player)}_vs_{_slug(opponent)}"
    wallet = _num(state.get(STATE.wallet_balance), 0.0)
    snapshot = _market_snapshot(state, ts)
    return {
        "schema_version": "tennis_generalist_turn_v1",
        "trajectory_id": trajectory_id,
        "turn_id": f"{trajectory_id}_tick_{step:04d}",
        "step_index": step,
        "timestamp": ts,
        "match": {"player_a": player, "player_b": opponent, "tournament": state.get(STATE.tournament, ""), "match_date": date},
        "state": {**_match_live_state(state), "wallet_balance": wallet, "available_balance": _num(state.get("available_balance"), wallet), "previous_actions": previous, "open_positions": positions},
        "input": {"reports": {key: state.get(key, "") for key in REPORT_ORDER}, "market_snapshot": snapshot},
        "target": {"tool_call": _target_call(tool_call, snapshot)},
        "outcome": {"accepted_for_training": True, "label_source": "teacher_model", "eventual_match_winner": state.get("eventual_match_winner"), "pnl_after_match": state.get("pnl_after_match")},
    }


def _save_turn_log(record: dict) -> None:
    path = get_config().get("generalist_turns_log")
    if path:
        try:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception:
            pass


_ACTION_LABELS = {
    "wait": "Esperar",
    "bet": "Apostar",
    "close": "Cerrar posición",
}


def format_decision_display(record: dict) -> str:
    """Convierte el registro interno del turno en un resumen legible para la UI."""
    match = record.get("match", {})
    state = record.get("state", {})
    target = record.get("target", {}).get("tool_call", {})
    name = (target.get("name") or "wait").lower()
    args = target.get("arguments", {})
    action_label = _ACTION_LABELS.get(name, name.capitalize())

    player_a = match.get("player_a", "")
    player_b = match.get("player_b", "")
    lines = [
        f"# Decisión Final — {player_a} vs {player_b}",
        "",
        f"**Torneo:** {match.get('tournament', 'N/A')}",
        f"**Fecha:** {match.get('match_date', 'N/A')}",
        f"**Fase:** {state.get('phase', 'N/A')}",
    ]

    score = state.get("score")
    if score:
        lines.append(f"**Marcador:** {score}")

    balance = state.get("available_balance", state.get("wallet_balance"))
    if balance is not None:
        lines.append(f"**Saldo disponible:** {balance}")

    lines.extend(["", f"## Acción: {action_label}", ""])

    if name == "bet":
        lines.extend(
            [
                f"- **Mercado:** {args.get('market') or 'N/A'}",
                f"- **Selección:** {args.get('option') or 'N/A'}",
                f"- **Stake:** {args.get('stake') if args.get('stake') is not None else 'N/A'}",
                f"- **Cuota:** {args.get('odds') if args.get('odds') is not None else 'N/A'}",
                f"- **Motivo:** {args.get('reason') or 'N/A'}",
            ]
        )
    elif name == "close":
        close_pct = args.get("close_percentage")
        close_label = f"{float(close_pct) * 100:.0f}%" if close_pct is not None else "N/A"
        lines.extend(
            [
                f"- **Posición:** {args.get('position_id') or 'N/A'}",
                f"- **Cierre:** {close_label}",
                f"- **Motivo:** {args.get('reason') or 'N/A'}",
            ]
        )
    else:
        lines.append(f"- **Motivo:** {args.get('reason') or 'N/A'}")

    timestamp = record.get("timestamp")
    if timestamp:
        lines.extend(["", "---", f"*Generado: {timestamp}*"])

    return "\n".join(lines)


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
            f"Informes de analistas:\n{analyst_reports}\n"
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
            _execute_tool_call(tool_call)
        except Exception as exc:
            response = _fallback_wait(match_id)
            tool_call = response.tool_calls[0]
            _execute_tool_call(tool_call)
            print(f"ERROR en generalist_llm: {exc}", flush=True)

        print("Decision final generada por generalist_llm", flush=True)
        record = _turn_log(state, tool_call)
        _save_turn_log(record)
        decision = format_decision_display(record)
        _emit_progress({"type": "generalist_complete", "decision": decision})

        return {
            STATE.messages: [response],
            STATE.final_bet_decision: decision,
        }

    return generalist_llm_node
