from langchain_core.messages import AIMessage

from tennisAgents.utils.enumerations import *
from tennisAgents.agents.utils.prompt_anatomy import PromptBuilder, TennisAnalystAnatomies
from tennisAgents.agents.utils.agent_utils import _record_tool_output
from tennisAgents.dataflows.config import get_config
from tennisAgents.dataflows.interface import get_weather_forecast
from tennisAgents.dataflows.tournament_utils import normalize_tournament


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
        location = tournament_identity.location or tournament_identity.search_name
        fecha_hora = f"{match_date} 14:00"

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

        additional_context = (
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
            f"Fecha del partido: {match_date}. Torneo: {tournament}. Ubicación resuelta: {location}.\n"
            "Usa EXCLUSIVAMENTE el pronóstico proporcionado en el mensaje del usuario.\n"
            "PROHIBIDO inventar temperatura, viento, humedad o lluvia si no aparecen en esos datos.\n"
            "No pidas más búsquedas ni repitas get_weather_forecast."
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
        result = chain.invoke(
            {
                "messages": state[STATE.messages],
                "user_message": (
                    f"Analiza las condiciones meteorológicas para el partido entre {player} y {opponent} "
                    f"el día {match_date} en {tournament}.\n\n"
                    f"PRONÓSTICO (ya obtenido — no repitas la herramienta):\n\n{weather_report}"
                ),
            }
        )

        report = result.content if hasattr(result, "content") else str(result)

        return {
            STATE.messages: [AIMessage(content=report)],
            REPORTS.weather_report: report,
        }

    return weather_analyst_node
