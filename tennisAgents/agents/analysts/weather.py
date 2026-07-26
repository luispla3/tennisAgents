from langchain_core.messages import AIMessage

from tennisAgents.utils.enumerations import *
from tennisAgents.agents.utils.prompt_anatomy import PromptBuilder, TennisAnalystAnatomies
from tennisAgents.agents.utils.agent_utils import _record_tool_output
from tennisAgents.dataflows.config import get_config
from tennisAgents.dataflows.interface import get_weather_forecast
from tennisAgents.dataflows.match_utils import resolve_match_datetime
from tennisAgents.dataflows.tennis_abstract_utils import format_player_identity_block
from tennisAgents.dataflows.tournament_utils import merge_analyst_tournament_context, normalize_tournament, resolve_weather_location
from tennisAgents.agents.utils.report_utils import sanitize_analyst_report


def _emit_activity(message: str) -> None:
    callback = get_config().get("progress_callback")
    if callback:
        try:
            callback({"type": "analyst_activity", "analyst": "weather", "message": message})
        except Exception:
            pass


def create_weather_analyst(llm, toolkit):
    def weather_analyst_node(state):
        match_date = state[STATE.match_date]
        player = state[STATE.player_of_interest]
        opponent = state[STATE.opponent]
        tournament = state[STATE.tournament]
        tournament_identity = normalize_tournament(tournament)
        resolved_location, _, location_note = resolve_weather_location(
            tournament,
            tournament_identity.location,
        )
        location = (
            resolved_location
            or tournament_identity.location
            or tournament_identity.search_name
        )
        fecha_hora = resolve_match_datetime(
            match_date,
            snapshot=state.get("scraper_snapshot"),
            default_hour=str(get_config().get("default_match_start_time", "14:00")),
        )
        player_identity = format_player_identity_block(player, opponent)

        _emit_activity("Obteniendo pronóstico meteorológico...")
        weather_report = get_weather_forecast(tournament, fecha_hora, location)
        _record_tool_output(
            "get_weather_forecast",
            {
                "tournament": tournament,
                "tournament_normalized": tournament_identity.display_name,
                "fecha_hora": fecha_hora,
                "location": location,
            },
            weather_report,
        )

        anatomy = TennisAnalystAnatomies.weather_analyst()

        additional_context = merge_analyst_tournament_context(
            state,
            (
            "FACTORES CLIMÁTICOS A ANALIZAR:\n"
            "• Temperatura y su impacto en la velocidad de la pelota y resistencia de los jugadores\n"
            "• Viento y su efecto en la precisión de los saques y golpes\n"
            "• Humedad y su influencia en la velocidad de la superficie y deslizamiento\n"
            "• Posibilidad de lluvia y su impacto en la continuidad del juego\n"
            "• Presión atmosférica y su efecto en la altitud (si aplica)\n\n"
            "ANÁLISIS REQUERIDO:\n"
            "• Cómo las condiciones climáticas pueden afectar el estilo de juego de ambos jugadores\n"
            "• Impacto en la estrategia del partido y adaptaciones necesarias\n"
            "• Comparación de ventajas/desventajas para cada jugador según el clima\n\n"
            f"Fecha/hora del partido resuelta: {fecha_hora}. Torneo: {tournament}. Ubicación resuelta: {location}.\n"
            + (f"Nota de ubicación: {location_note}\n" if location_note else "")
            + "Usa EXCLUSIVAMENTE el pronóstico proporcionado en el mensaje del usuario.\n"
            "PROHIBIDO inventar temperatura, viento, humedad o lluvia si no aparecen en esos datos.\n"
            "PROHIBIDO escribir 'no hay datos meteorológicos disponibles'; sintetiza con lo disponible.\n"
            "PROHIBIDO inferir nacionalidad de los jugadores; usa solo el bloque de identidad verificada.\n"
            "PROHIBIDO usar tablas markdown en el informe final.\n"
            "No pidas más búsquedas ni repitas get_weather_forecast."
            ),
        )

        prompt = PromptBuilder.create_structured_prompt(
            anatomy=anatomy,
            tools_info="",
            additional_context=additional_context,
        )

        prompt = prompt.partial(player=player)
        prompt = prompt.partial(opponent=opponent)
        prompt = prompt.partial(match_date=match_date)
        prompt = prompt.partial(tournament=tournament)

        _emit_activity("Sintetizando informe con LLM...")
        chain = prompt | llm
        identity_section = (
            f"IDENTIDAD VERIFICADA DE JUGADORES:\n\n{player_identity}\n\n"
            if player_identity
            else ""
        )
        result = chain.invoke(
            {
                "messages": state[STATE.messages],
                "user_message": (
                    f"Analiza las condiciones meteorológicas para el partido entre {player} y {opponent} "
                    f"el {fecha_hora} en {tournament}.\n\n"
                    f"{identity_section}"
                    f"PRONÓSTICO (ya obtenido — no repitas la herramienta):\n\n{weather_report}"
                ),
            }
        )

        report = sanitize_analyst_report(
            result.content if hasattr(result, "content") else str(result)
        )

        return {
            STATE.messages: [AIMessage(content=report)],
            REPORTS.weather_report: report,
        }

    return weather_analyst_node
