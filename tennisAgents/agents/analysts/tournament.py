from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from tennisAgents.utils.enumerations import *
from tennisAgents.agents.utils.prompt_anatomy import PromptBuilder, TennisAnalystAnatomies

def create_tournament_analyst(llm, toolkit):
    def tournament_analyst_node(state):
        match_date = state[STATE.match_date]
        tournament = state[STATE.tournament]
        location = state.get(STATE.location, "Ubicación no especificada")
        player = state[STATE.player_of_interest]
        opponent = state[STATE.opponent]

        # Herramientas específicas
        if toolkit.config["online_tools"]:
            tools = [toolkit.get_tournament_info]
        else:
            tools = [toolkit.get_tournament_info]

        # Obtener la anatomía del prompt para analista de torneos
        anatomy = TennisAnalystAnatomies.tournament_analyst()
        
        # Información de herramientas
        tools_info = (
            "• get_tournament_info() - Obtiene información detallada sobre torneos de tenis"
        )
        
        # Contexto adicional específico del análisis de torneos
        additional_context = (
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
            "IMPORTANTE: Solo puedes hacer UNA SOLA LLAMADA a get_tournament_info. Usa esa información de manera eficiente y completa.\n\n"
            "IMPORTANTE: Cuando uses get_tournament_info, debes incluir la fecha del partido {match_date} como parámetro 'date'."
        )

        # Crear prompt estructurado usando la anatomía
        prompt = PromptBuilder.create_structured_prompt(
            anatomy=anatomy,
            tools_info=tools_info,
            additional_context=additional_context
        )

        # Inyección de variables al prompt
        prompt = prompt.partial(tournament=tournament)
        prompt = prompt.partial(location=location)
        prompt = prompt.partial(player=player)
        prompt = prompt.partial(opponent=opponent)
        prompt = prompt.partial(match_date=match_date)

        chain = prompt | llm.bind_tools(tools)

        # Crear el input correcto como diccionario
        input_data = {
            "messages": state[STATE.messages],
            "user_message": f"Analiza el torneo {tournament} en {location} y su impacto en {player} y {opponent}."
        }

        result = chain.invoke(input_data)

        report = ""
        if len(result.tool_calls) == 0:
            report = result.content

        return {
            STATE.messages: [result],
            REPORTS.tournament_report: report,
        }

    return tournament_analyst_node
