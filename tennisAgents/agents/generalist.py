import json
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Annotated

from langchain_core.messages import AIMessage
from langchain_core.tools import tool

from tennisAgents.dataflows import interface
from tennisAgents.dataflows.config import get_config
from tennisAgents.dataflows.market_resolve import resolve_market_selection
from tennisAgents.utils.enumerations import REPORTS, STATE

GENERALIST_NODE = "generalist_llm"


def _tool_log(action: str, **data) -> str:
    return json.dumps({"status": "logged", "action": action, **data}, ensure_ascii=False)


@tool
def Bet(
    match_id: Annotated[str, "Identificador del partido"],
    market: Annotated[
        str,
        "market_type exacto del snapshot (p.ej. MATCH_ODDS) o name visible del mercado",
    ],
    selection: Annotated[str, "Selección apostada"],
    stake: Annotated[
        float,
        "Importe de la apuesta; debe ser > 0 y no superar el saldo disponible",
    ],
    rationale: Annotated[str, "Motivo breve de la apuesta"],
    confidence: Annotated[float, "Confianza entre 0 y 1"],
    estimated_probability: Annotated[
        float,
        "Probabilidad estimada de la selección, entre 0 y 1",
    ],
    notes: Annotated[
        str,
        "Notas para el siguiente timestep; incluye edge, % del wallet y por qué "
        "esta línea supera a las alternativas",
    ] = "",
) -> str:
    """Registra una apuesta."""
    return _tool_log(
        "Bet",
        match_id=match_id,
        market=market,
        selection=selection,
        stake=stake,
        rationale=rationale,
        confidence=confidence,
        estimated_probability=estimated_probability,
        notes=notes,
    )


@tool
def Wait(
    match_id: Annotated[str, "Identificador del partido"],
    rationale: Annotated[str, "Motivo breve para no actuar"],
    confidence: Annotated[float, "Confianza entre 0 y 1"],
    next_trigger: Annotated[str, "Condición que haría reconsiderar la decisión"] = "",
    notes: Annotated[str, "Notas para revisar en el siguiente timestep"] = "",
) -> str:
    """Registra que se decide esperar sin hacer nada."""
    return _tool_log(
        "Wait",
        match_id=match_id,
        rationale=rationale,
        confidence=confidence,
        next_trigger=next_trigger,
        notes=notes,
    )


@tool
def Close(
    match_id: Annotated[str, "Identificador del partido"],
    close_percentage: Annotated[float, "Porcentaje de cierre, de 0 a 1"],
    rationale: Annotated[str, "Motivo breve del cierre"],
    confidence: Annotated[float, "Confianza entre 0 y 1"],
    notes: Annotated[str, "Notas para revisar en el siguiente timestep"] = "",
    position_id: Annotated[str, "ID exacto de la posición abierta que se cerrará"] = "",
) -> str:
    """Registra el cierre de una apuesta."""
    return _tool_log(
        "Close",
        match_id=match_id,
        close_percentage=close_percentage,
        rationale=rationale,
        confidence=confidence,
        notes=notes,
        position_id=position_id,
    )


GENERALIST_TOOLS = [Bet, Wait, Close]
GENERALIST_TOOL_MAP = {t.name: t for t in GENERALIST_TOOLS}
GENERALIST_TOOL_MAP.update({t.name.lower(): t for t in GENERALIST_TOOLS})
REPORT_ORDER = (REPORTS.players_report, REPORTS.news_report, REPORTS.tournament_report, REPORTS.weather_report)


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
    """Extrae el mercado del snapshot producido por BetfairEnv."""
    scraper_snapshot = state.get("scraper_snapshot") or {}
    betfair = scraper_snapshot.get("betfair") or {}
    return {
        "source": "BetfairEnv",
        "captured_at": scraper_snapshot.get("timestamp") or captured_at,
        "event_id": scraper_snapshot.get("betfair_event_id"),
        "status": betfair.get("status"),
        "primary_market": betfair.get("primary_market") or {},
        "markets": betfair.get("markets") or [],
    }


def _market_selection(
    snapshot: dict,
    market_type: str,
    option: str,
) -> tuple[dict, dict] | tuple[None, None]:
    """Resuelve una selección contra el snapshot real, sin confiar en el LLM."""
    return resolve_market_selection(
        list(snapshot.get("markets") or []),
        market_type,
        option,
        primary_market=snapshot.get("primary_market") or {},
    )


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


def _target_call(tool_call, snapshot: dict, *, state: dict | None = None) -> dict:
    call = _call_data(tool_call)
    args = call.get("args", {})
    name = call["name"].lower()
    reason = args.get("reason") or args.get("rationale") or ""
    state = state or {}
    wallet = _num(state.get(STATE.wallet_balance), 0.0)
    available = _num(state.get("available_balance"), wallet)
    if name == "bet":
        option, market = args.get("option") or args.get("selection", ""), args.get("market", "")
        matched_market, runner = _market_selection(snapshot, market, option)
        stake = _num(args.get("stake"), 0.0)
        odds = _num((runner or {}).get("odds_decimal"))
        estimated_probability = _num(args.get("estimated_probability"))
        calibration = _bet_calibration_fields(
            stake=stake,
            odds=odds,
            estimated_probability=estimated_probability,
            wallet_balance=wallet,
            available_balance=available,
            market=str(
                (matched_market or {}).get("market_type")
                or market
                or ""
            ),
        )
        return {
            "name": "bet",
            "technical_fallback": False,
            "arguments": {
                "market": market,
                "option": option,
                "stake": stake,
                "odds": calibration.get("odds"),
                "market_id": (matched_market or {}).get("market_id"),
                "selection_id": (runner or {}).get("selection_id"),
                "reason": reason,
                "confidence": _num(args.get("confidence")),
                "estimated_probability": calibration.get("estimated_probability"),
                "implied_probability": calibration.get("implied_probability"),
                "edge": calibration.get("edge"),
                "stake_pct_wallet": calibration.get("stake_pct_wallet"),
                "stake_pct_available": calibration.get("stake_pct_available"),
                "market_family": calibration.get("market_family"),
                "notes": args.get("notes") or "",
            },
        }
    if name == "close":
        return {
            "name": "close",
            "technical_fallback": False,
            "arguments": {
                "position_id": args.get("position_id") or "",
                "match_id": args.get("match_id") or "",
                "close_percentage": _num(args.get("close_percentage"), 1.0),
                "reason": reason,
                "confidence": _num(args.get("confidence")),
                "notes": args.get("notes") or "",
            },
        }
    return {
        "name": "wait",
        "technical_fallback": call.get("id") == "fallback_wait",
        "arguments": {
            "reason": reason,
            "confidence": _num(args.get("confidence")),
            "next_trigger": args.get("next_trigger") or "",
            "notes": args.get("notes") or "",
        },
    }


def _turn_log(state: dict, tool_call) -> dict:
    ts = datetime.now().astimezone().isoformat(timespec="seconds")
    player, opponent, date = state.get(STATE.player_of_interest, ""), state.get(STATE.opponent, ""), state.get(STATE.match_date, "")
    previous, positions = state.get("previous_actions") or [], state.get("open_positions") or []
    step = int(state.get("step_index", len(previous)))
    trajectory_id = f"match_{date}_{_slug(player)}_vs_{_slug(opponent)}"
    wallet = _num(state.get(STATE.wallet_balance), 0.0)
    snapshot = _market_snapshot(state, ts)
    target_call = _target_call(tool_call, snapshot, state=state)
    technical_fallback = bool(target_call.get("technical_fallback"))
    return {
        "schema_version": "tennis_generalist_turn_v1",
        "trajectory_id": trajectory_id,
        "turn_id": f"{trajectory_id}_tick_{step:04d}",
        "step_index": step,
        "timestamp": ts,
        "match": {"player_a": player, "player_b": opponent, "tournament": state.get(STATE.tournament, ""), "match_date": date},
        "state": {**_match_live_state(state), "wallet_balance": wallet, "available_balance": _num(state.get("available_balance"), wallet), "previous_actions": previous, "open_positions": positions},
        "input": {"reports": {key: state.get(key, "") for key in REPORT_ORDER}, "market_snapshot": snapshot},
        "target": {"tool_call": target_call},
        "outcome": {
            "accepted_for_training": False,
            "label_source": "technical_fallback" if technical_fallback else "pending_validation",
            "eventual_match_winner": state.get("eventual_match_winner"),
            "pnl_after_match": state.get("pnl_after_match"),
        },
    }


def _save_turn_log(record: dict, path: str | None = None) -> None:
    path = path or get_config().get("generalist_turns_log")
    if not path:
        return

    log_path = Path(path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    max_bytes = int(
        get_config().get("audit_log_max_bytes", 100 * 1024 * 1024)
    )
    if log_path.exists() and log_path.stat().st_size >= max_bytes:
        rotated = Path(f"{path}.1")
        rotated.unlink(missing_ok=True)
        os.replace(log_path, rotated)

    # Un retry del mismo snapshot no debe duplicar el último turno.
    if log_path.exists() and log_path.stat().st_size:
        with log_path.open("rb") as existing:
            existing.seek(0, os.SEEK_END)
            position = existing.tell()
            buffer = b""
            last_line_bytes = b""
            while position > 0:
                block_size = min(64 * 1024, position)
                position -= block_size
                existing.seek(position)
                buffer = existing.read(block_size) + buffer
                stripped = buffer.rstrip(b"\r\n\t ")
                if b"\n" in stripped:
                    last_line_bytes = stripped.rsplit(b"\n", 1)[-1]
                    break
                if position == 0:
                    last_line_bytes = stripped
            last_line = last_line_bytes.decode("utf-8")
        try:
            last_record = json.loads(last_line)
        except json.JSONDecodeError:
            last_record = {}
        if last_record.get("turn_id") == record.get("turn_id"):
            return

    with log_path.open("a", encoding="utf-8") as output:
        output.write(json.dumps(record, ensure_ascii=False) + "\n")
        output.flush()
        os.fsync(output.fileno())


def _read_context_file(state: dict) -> tuple[str, str | None]:
    """Lee el contexto persistente del partido antes de cada invocación."""
    path = state.get("context_path") or get_config().get("context_path")
    if not path:
        return "No existe context.md para este análisis.", None

    context_path = Path(path)
    try:
        if not context_path.exists():
            return "context.md todavía no existe; este es el primer timestep.", str(context_path)
        content = context_path.read_text(encoding="utf-8").strip()
        return content or "context.md está vacío; no hay notas previas.", str(context_path)
    except OSError as exc:
        return f"No se pudo leer context.md: {exc}", str(context_path)


def _scraper_context(state: dict) -> str:
    """Serializa el snapshot actual para que el generalista razone sobre datos frescos."""
    snapshot = state.get("scraper_snapshot")
    if not snapshot:
        return "No hay snapshot de BetfairEnv; se usarán los fallbacks configurados."
    return json.dumps(snapshot, ensure_ascii=False, indent=2)


def _market_family(market_key: str) -> str:
    """Clasifica un mercado para diversificación y calibración."""
    token = str(market_key or "").casefold().replace(" ", "_")
    if not token:
        return "unknown"
    if "match_odds" in token or token in {"match_winner", "winner", "moneyline"}:
        return "match_odds"
    if "correct_score" in token or "set_betting" in token:
        return "set"
    if "set_" in token and "game" not in token:
        return "set"
    if "game" in token or "juego" in token:
        return "game"
    if "total" in token or "over" in token or "under" in token:
        return "totals"
    if "both" in token or "to_win_a_set" in token:
        return "props"
    return "other"


def _bet_calibration_fields(
    *,
    stake: float,
    odds: float | None,
    estimated_probability: float | None,
    wallet_balance: float,
    available_balance: float,
    market: str,
) -> dict:
    """Campos homogéneos de calibración para training y auditoría."""
    implied = None
    edge = None
    if odds is not None and odds > 1.0:
        implied = 1.0 / odds
        if estimated_probability is not None and 0.0 < estimated_probability < 1.0:
            edge = estimated_probability - implied
    wallet_safe = wallet_balance if wallet_balance > 0 else 0.0
    available_safe = available_balance if available_balance > 0 else 0.0
    return {
        "implied_probability": (
            round(implied, 6) if implied is not None else None
        ),
        "edge": round(edge, 6) if edge is not None else None,
        "stake_pct_wallet": (
            round(stake / wallet_safe, 6) if wallet_safe else None
        ),
        "stake_pct_available": (
            round(stake / available_safe, 6) if available_safe else None
        ),
        "market_family": _market_family(market),
        "odds": round(odds, 6) if odds is not None and odds > 0 else odds,
        "estimated_probability": (
            round(estimated_probability, 6)
            if estimated_probability is not None
            else None
        ),
        "stake": round(stake, 6) if stake is not None else stake,
    }


def _portfolio_capital_brief(state: dict) -> dict:
    """Resumen de exposición para razonar diversificación de capital."""
    wallet = _num(
        state.get(STATE.wallet_balance),
        _num(state.get("available_balance"), 0.0),
    )
    available = _num(state.get("available_balance"), wallet)
    positions = [
        position
        for position in (state.get("open_positions") or [])
        if isinstance(position, dict)
    ]
    exposure = sum(_num(position.get("remaining_stake"), 0.0) for position in positions)
    by_market: dict[str, float] = {}
    for position in positions:
        market = str(position.get("market") or position.get("market_type") or "unknown")
        by_market[market] = by_market.get(market, 0.0) + _num(
            position.get("remaining_stake"),
            0.0,
        )
    wallet_safe = wallet if wallet > 0 else 0.0
    return {
        "wallet_balance": round(wallet_safe, 4),
        "available_balance": round(available, 4),
        "total_exposure": round(exposure, 4),
        "exposure_fraction": (
            round(exposure / wallet_safe, 4) if wallet_safe else None
        ),
        "available_fraction": (
            round(available / wallet_safe, 4) if wallet_safe else None
        ),
        "open_positions_count": len(positions),
        "exposure_by_market": {
            key: round(value, 4) for key, value in sorted(by_market.items())
        },
        "suggested_max_single_stake": (
            round(wallet_safe * 0.10, 4) if wallet_safe else 0.0
        ),
        "suggested_max_total_exposure": (
            round(wallet_safe * 0.35, 4) if wallet_safe else 0.0
        ),
        "sizing_hint": (
            "Quarter-Kelly aproximado: stake ≈ available * 0.25 * "
            "edge / (odds - 1), con edge = p_estimada - 1/odds. "
            "Si edge <= 0 o odds <= 1, no apostar."
        ),
    }


def _open_market_lines(snapshot: dict | None, *, limit: int = 40) -> list[dict]:
    """Líneas abiertas con probabilidad implícita para comparar valor relativo."""
    if not isinstance(snapshot, dict):
        return []
    betfair = snapshot.get("betfair") or {}
    markets = list(betfair.get("markets") or [])
    if not markets and snapshot.get("markets"):
        markets = list(snapshot.get("markets") or [])
    lines: list[dict] = []
    for market in markets:
        if not isinstance(market, dict):
            continue
        if str(market.get("status") or "").upper() not in {"", "OPEN"}:
            continue
        market_key = str(
            market.get("market_type") or market.get("name") or market.get("market_id") or ""
        )
        family = _market_family(market_key)
        for runner in market.get("runners") or []:
            if not isinstance(runner, dict):
                continue
            if str(runner.get("status") or "").upper() not in {"", "ACTIVE"}:
                continue
            odds = _num(runner.get("odds_decimal"), 0.0)
            if odds <= 1.0:
                continue
            lines.append(
                {
                    "market": market_key,
                    "market_family": family,
                    "selection": str(runner.get("name") or ""),
                    "odds": round(odds, 4),
                    "implied_probability": round(1.0 / odds, 4),
                }
            )
    # Orden neutro: por familia y luego implícita (sin penalizar MATCH_ODDS).
    lines.sort(
        key=lambda item: (
            str(item.get("market_family") or "unknown"),
            str(item.get("market") or ""),
            _num(item.get("implied_probability"), 1.0),
        )
    )
    return lines[:limit]


def _diversification_prompt_hint(market_lines: list[dict]) -> str:
    families = sorted(
        {
            str(line.get("market_family") or "unknown")
            for line in market_lines
            if str(line.get("market_family") or "unknown") != "unknown"
        }
    )
    if not families:
        return (
            "Compara todas las líneas abiertas por edge (p_estimada - 1/cuota) "
            "y elige la de mejor EV ajustado a riesgo; Wait si ninguna es clara."
        )
    return (
        "Familias disponibles: "
        + ", ".join(families)
        + ". Trátalas como candidatas iguales: elige la línea con mejor EV "
        "(edge × stake admisible), sea MATCH_ODDS, set, juego u otra. "
        "No descartes MATCH_ODDS por principio ni apuestes fuera de MATCH_ODDS "
        "solo por diversificar."
    )


def _write_context_file(
    path: str | None,
    *,
    record: dict,
    scraper_snapshot: dict | None,
) -> None:
    """Reescribe context.md con la justificación y las notas del timestep actual."""
    if not path:
        return

    match = record.get("match") or {}
    state = record.get("state") or {}
    target = record.get("target", {}).get("tool_call") or {}
    arguments = target.get("arguments") or {}
    action = target.get("name", "wait").capitalize()
    snapshot = scraper_snapshot or {}
    betfair = snapshot.get("betfair") or {}
    flashscore = snapshot.get("flashscore") or {}

    lines = [
        "# Contexto persistente del partido",
        "",
        f"- **Actualizado:** {record.get('timestamp', 'N/D')}",
        f"- **Partido:** {match.get('player_a', 'N/D')} vs {match.get('player_b', 'N/D')}",
        f"- **Torneo:** {match.get('tournament', 'N/D')}",
        f"- **Fecha:** {match.get('match_date', 'N/D')}",
        f"- **Timestep:** {record.get('step_index', 'N/D')}",
        "",
        "## Decisión anterior",
        "",
        f"- **Tool:** `{action}`",
        f"- **Confianza:** {arguments.get('confidence', 'N/D')}",
        f"- **Justificación:** {arguments.get('reason') or 'N/D'}",
        "",
        "## Notas para el siguiente timestep",
        "",
        arguments.get("notes")
        or arguments.get("next_trigger")
        or "Reevaluar cuando llegue el siguiente snapshot.",
        "",
        "## Estado observado por los scrapers",
        "",
        f"- **Snapshot:** {snapshot.get('timestamp', 'N/D')}",
        f"- **Estado Betfair:** {betfair.get('status', 'N/D')}",
        f"- **Marcador Flashscore:** {flashscore.get('score', 'N/D')}",
        f"- **Puntos actuales:** {flashscore.get('current_points') or flashscore.get('current_game') or 'N/D'}",
        f"- **Servidor:** {flashscore.get('serving', 'N/D')}",
        "",
        "El archivo se reescribe en cada timestep; el historial completo permanece en generalist_turns.jsonl.",
        "",
    ]

    context_path = Path(path)
    temporary_path: Path | None = None
    try:
        context_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=context_path.parent,
            prefix=f".{context_path.name}-",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary.write("\n".join(str(line) for line in lines))
            temporary.flush()
            os.fsync(temporary.fileno())
            temporary_path = Path(temporary.name)
        os.replace(temporary_path, context_path)
    except OSError:
        raise
    finally:
        if temporary_path and temporary_path.exists():
            temporary_path.unlink(missing_ok=True)


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
                f"- **Stake % wallet:** {args.get('stake_pct_wallet') if args.get('stake_pct_wallet') is not None else 'N/A'}",
                f"- **Cuota:** {args.get('odds') if args.get('odds') is not None else 'N/A'}",
                f"- **Familia de mercado:** {args.get('market_family') or 'N/A'}",
                f"- **Probabilidad estimada:** {args.get('estimated_probability') if args.get('estimated_probability') is not None else 'N/A'}",
                f"- **Probabilidad implícita:** {args.get('implied_probability') if args.get('implied_probability') is not None else 'N/A'}",
                f"- **Edge:** {args.get('edge') if args.get('edge') is not None else 'N/A'}",
                f"- **Motivo:** {args.get('reason') or 'N/A'}",
                f"- **Confianza:** {args.get('confidence') if args.get('confidence') is not None else 'N/A'}",
                f"- **Notas:** {args.get('notes') or 'N/A'}",
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
                f"- **Confianza:** {args.get('confidence') if args.get('confidence') is not None else 'N/A'}",
                f"- **Notas:** {args.get('notes') or 'N/A'}",
            ]
        )
    else:
        lines.append(f"- **Motivo:** {args.get('reason') or 'N/A'}")
        lines.append(f"- **Confianza:** {args.get('confidence') if args.get('confidence') is not None else 'N/A'}")
        lines.append(f"- **Siguiente condición:** {args.get('next_trigger') or 'N/A'}")
        lines.append(f"- **Notas:** {args.get('notes') or 'N/A'}")

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
        wallet_balance = state.get(
            "available_balance",
            state.get(STATE.wallet_balance, 0),
        )
        analyst_reports = _collect_analyst_reports(state)
        match_id = f"{player} vs {opponent} | {tournament} | {match_date}"
        context_text, context_path = _read_context_file(state)
        scraper_snapshot = state.get("scraper_snapshot") or {}
        capital_brief = _portfolio_capital_brief(state)
        market_lines = _open_market_lines(scraper_snapshot)
        diversification_hint = _diversification_prompt_hint(market_lines)

        if scraper_snapshot:
            odds_report = json.dumps(
                scraper_snapshot.get("betfair") or {},
                ensure_ascii=False,
                indent=2,
            )
            live_report = json.dumps(
                scraper_snapshot.get("flashscore") or {},
                ensure_ascii=False,
                indent=2,
            )
        else:
            try:
                odds_report = interface.get_betfair_odds_scraper(player)
            except Exception as exc:
                odds_report = f"Cuotas de Betfair no disponibles: {exc}"
            try:
                live_report = interface.get_match_live_data(player, opponent, tournament)
            except Exception as exc:
                live_report = f"Datos en vivo no disponibles: {exc}"

        prompt = (
            "Eres el agente generalista del sistema de apuestas de tenis.\n"
            "Debes leer los informes, el snapshot actual de los scrapers y context.md.\n"
            "Termina ejecutando exactamente una tool call: Bet, Wait o Close.\n"
            "La tool call debe contener una justificación factual en 'rationale' y notas accionables "
            "para el siguiente timestep en 'notes' (Wait también puede usar 'next_trigger').\n"
            "No escribas texto fuera de la tool call. Si no hay valor claro o faltan cuotas fiables, usa Wait.\n"
            "No inventes marcador, cuotas, estadísticas ni eventos que no aparezcan en los datos.\n"
            "Nunca uses Bet con stake <= 0 ni con stake superior al saldo disponible. "
            "Si no puedes fijar un stake positivo concreto, usa Wait (no Bet con 0).\n"
            "Bet debe incluir estimated_probability entre 0 y 1; comprueba que sea "
            "mayor que 1/cuota y explica el edge sin errores aritméticos.\n"
            "En Bet.market usa el market_type exacto del snapshot (p.ej. MATCH_ODDS, "
            "SET_2_GAME_3_WINNER) o el name visible del mercado; en selection/option "
            "usa el name exacto del runner.\n"
            "Para Close usa el position_id exacto mostrado en Posiciones abiertas.\n"
            "Si marcador, set, servidor o mercado no son coherentes entre fuentes, usa Wait.\n\n"
            "Estrategia de capital (objetivo: EV y supervivencia a largo plazo, no "
            "recuperar pérdidas del partido):\n"
            "- Considera TODOS los mercados abiertos (MATCH_ODDS, set, juegos, "
            "totales, props, etc.) como candidatas a la misma estrategia. "
            "No prohíbas ni penalices MATCH_ODDS; tampoco apuestes otro mercado "
            "solo por 'diversificar'.\n"
            "- Compara líneas por edge real (p_estimada - 1/cuota) y liquidez/"
            "fiabilidad de la señal; elige la de mejor EV ajustado a riesgo "
            "(o Wait si ninguna supera el umbral).\n"
            f"- Hint de mercado: {diversification_hint}\n"
            "- Diversifica exposición de capital: evita concentrar todo el "
            "bankroll en una sola selección; si ya hay posiciones correlacionadas "
            "(p.ej. mismo jugador en MATCH_ODDS + set/juegos), exige más edge "
            "conjunto o usa Wait/Close.\n"
            "- Dimensiona el stake con el hint de Quarter-Kelly del resumen de "
            "cartera; por defecto no superes ~10% del wallet en una sola apuesta ni "
            "~35% de exposición total, salvo edge excepcional muy bien justificado.\n"
            "- No aumentes stake por tilt ni para 'compensar' un Wait/Close previo; "
            "cada timestep se evalúa solo con el edge actual.\n"
            "- Preferible Wait a forzar Bet con edge marginal (<~3-5%). En cuotas "
            "muy cortas (<~1.25) de cualquier mercado, el edge del LLM es frágil: "
            "exige más convicción o Wait.\n"
            "- En rationale/notes deja explícito: p_estimada, implícita (1/cuota), "
            "edge, stake, stake% del wallet, market_family y por qué esa línea "
            "bate a las alternativas consideradas (incluidas MATCH_ODDS y el resto).\n\n"
            f"match_id: {match_id}\n"
            f"Partido: {player} vs {opponent}\n"
            f"Torneo: {tournament}\n"
            f"Fecha: {match_date}\n"
            f"Saldo disponible: {wallet_balance}\n\n"
            f"Resumen de cartera / capital:\n"
            f"{json.dumps(capital_brief, ensure_ascii=False, indent=2)}\n\n"
            f"Líneas abiertas (cuota e implícita; todas las familias):\n"
            f"{json.dumps(market_lines, ensure_ascii=False, indent=2)}\n\n"
            f"Acciones anteriores:\n{json.dumps(state.get('previous_actions') or [], ensure_ascii=False, indent=2)}\n\n"
            f"Posiciones abiertas:\n{json.dumps(state.get('open_positions') or [], ensure_ascii=False, indent=2)}\n\n"
            f"Cuotas Betfair:\n{odds_report}\n\n"
            f"Datos en vivo del partido:\n{live_report}\n\n"
            f"Snapshot completo de los scrapers:\n{_scraper_context(state)}\n\n"
            f"Informes de analistas:\n{analyst_reports}\n\n"
            f"context.md de timesteps anteriores ({context_path or 'sin archivo'}):\n"
            f"{context_text}\n"
        )

        generalist_error = None
        technical_fallback = False
        try:
            try:
                response = deep_thinking_llm.bind_tools(GENERALIST_TOOLS, tool_choice="any").invoke(prompt)
            except Exception:
                response = deep_thinking_llm.bind_tools(GENERALIST_TOOLS).invoke(prompt)
            if not getattr(response, "tool_calls", None):
                response = _fallback_wait(match_id)
                generalist_error = "El modelo no devolvió una tool call."
                technical_fallback = True
            elif len(response.tool_calls) != 1:
                response = _fallback_wait(match_id)
                generalist_error = (
                    f"El modelo devolvió {len(response.tool_calls)} tool calls; "
                    "se requiere exactamente una."
                )
                technical_fallback = True
            tool_call = response.tool_calls[0]
            call_data = _call_data(tool_call)
            if str(call_data.get("name") or "").lower() == "bet":
                stake_value = _num((call_data.get("args") or {}).get("stake"), 0.0)
                if stake_value is None or stake_value <= 0:
                    tool_call = {
                        "name": "Wait",
                        "args": {
                            "match_id": match_id,
                            "rationale": (
                                "Bet inválido: stake debe ser > 0. Se espera "
                                "en lugar de apostar con stake nulo o negativo."
                            ),
                            "confidence": _num(
                                (call_data.get("args") or {}).get("confidence"),
                                0.5,
                            )
                            or 0.5,
                            "next_trigger": (
                                "Reformular Bet con stake positivo acotado "
                                "al saldo y al sizing de cartera."
                            ),
                            "notes": (
                                "Corrección automática: stake<=0 no está permitido."
                            ),
                        },
                        "id": call_data.get("id") or "stake_guard_wait",
                    }
                    generalist_error = (
                        (generalist_error + " | " if generalist_error else "")
                        + "Bet con stake<=0 convertido a Wait."
                    )
            response = AIMessage(content="", tool_calls=[tool_call])
            _execute_tool_call(tool_call)
        except Exception as exc:
            response = _fallback_wait(match_id)
            tool_call = response.tool_calls[0]
            _execute_tool_call(tool_call)
            generalist_error = f"{type(exc).__name__}: {exc}"
            technical_fallback = True
            print(f"ERROR en generalist_llm: {exc}", flush=True)

        print("Decision final generada por generalist_llm", flush=True)
        record = _turn_log(state, tool_call)
        if not state.get("defer_generalist_persistence", False):
            _save_turn_log(record, state.get("generalist_turns_log"))
            _write_context_file(
                context_path,
                record=record,
                scraper_snapshot=scraper_snapshot,
            )
        decision = format_decision_display(record)
        _emit_progress({"type": "generalist_complete", "decision": decision})

        return {
            STATE.messages: [response],
            STATE.final_bet_decision: decision,
            "generalist_record": record,
            "generalist_error": generalist_error,
            "technical_fallback": technical_fallback,
        }

    return generalist_llm_node
