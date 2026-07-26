from langchain_core.messages import AIMessage

from tennisAgents.utils.enumerations import *
from tennisAgents.agents.utils.prompt_anatomy import PromptBuilder, TennisAnalystAnatomies
from tennisAgents.agents.utils.agent_utils import _record_tool_output
from tennisAgents.dataflows.config import get_config
from tennisAgents.dataflows.interface import get_tournament_data
from tennisAgents.dataflows.tournament_utils import merge_analyst_tournament_context, normalize_tournament
from tennisAgents.agents.utils.report_utils import sanitize_analyst_report


def _emit_activity(message: str) -> None:
    callback = get_config().get("progress_callback")
    if callback:
        try:
            callback({"type": "analyst_activity", "analyst": "tournament", "message": message})
        except Exception:
            pass


def create_tournament_analyst(llm, toolkit):
    def tournament_analyst_node(state):
        match_date = state[STATE.match_date]
        tournament = state[STATE.tournament]
        player = state[STATE.player_of_interest]
        opponent = state[STATE.opponent]
        tournament_identity = normalize_tournament(tournament)
        category = tournament_identity.category if tournament_identity.category != "unknown" else "atp"

        _emit_activity("Obteniendo datos del torneo...")
        tournament_data = get_tournament_data(tournament, category, match_date)
        _record_tool_output(
            "get_tournament_info",
            {
                "tournament": tournament,
                "tournament_normalized": tournament_identity.display_name,
                "category": category,
                "date": match_date,
            },
            tournament_data,
        )

        anatomy = TennisAnalystAnatomies.tournament_analyst()

        additional_context = merge_analyst_tournament_context(
            state,
            (
            "FACTORES A EVALUAR:\n"
            "• Tipo de superficie y condiciones físicas del entorno (altitud, clima habitual, velocidad de la pista)\n"
            "• Categoría del torneo y su importancia en el calendario\n"
            f"• Historial de {player} y {opponent} en este torneo o en condiciones similares\n"
            "• Impacto del formato del torneo en el rendimiento de los jugadores\n\n"
            "CONOCIMIENTO ESPECÍFICO DEL TENIS:\n"
            "• Categorías de torneos: atpgs (ATP + Grand Slams), atp (circuito ATP), gs (Grand Slams), 1000 (Masters 1000), ch (Challenger Circuit)\n"
            "• En Grand Slams: los jugadores juegan en días alternos, afectando la fatiga y recuperación\n"
            "• En Grand Slams avanzados: el jugador con mejor ranking/trayectoria suele ganar por mayor confianza y menos nervios (mejor de 5 sets)\n"
            "• En torneos menores: los jugadores buenos pueden no rendir al máximo si se reservan para torneos importantes\n"
            "• Jugadores mayores de 30 años: menor disposición para remontar partidos/sets, especialmente en formato a 5 sets\n\n"
            "OBJETIVO: Ayudar al equipo de predicción a entender el impacto del torneo sobre el rendimiento de los jugadores.\n\n"
            "Usa EXCLUSIVAMENTE los datos del torneo proporcionados en el mensaje del usuario.\n"
            "No inventes datos históricos ni condiciones concretas que no aparezcan en esos datos.\n"
            "PROHIBIDO usar tablas markdown en el informe final.\n"
            "No pidas más búsquedas ni repitas get_tournament_info."
            ),
        )

        prompt = PromptBuilder.create_structured_prompt(
            anatomy=anatomy,
            tools_info="",
            additional_context=additional_context,
        )

        prompt = prompt.partial(tournament=tournament)
        prompt = prompt.partial(player=player)
        prompt = prompt.partial(opponent=opponent)
        prompt = prompt.partial(match_date=match_date)

        _emit_activity("Sintetizando informe con LLM...")
        chain = prompt | llm
        result = chain.invoke(
            {
                "messages": state[STATE.messages],
                "user_message": (
                    f"Analiza el torneo {tournament} y su impacto en {player} y {opponent} "
                    f"para el partido del {match_date}.\n\n"
                    f"DATOS DEL TORNEO (ya obtenidos — no repitas la herramienta):\n\n{tournament_data}"
                ),
            }
        )

        report = sanitize_analyst_report(
            result.content if hasattr(result, "content") else str(result)
        )

        return {
            STATE.messages: [AIMessage(content=report)],
            REPORTS.tournament_report: report,
        }

    return tournament_analyst_node
