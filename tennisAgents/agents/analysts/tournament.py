from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from tennisAgents.utils.enumerations import *

def create_tournament_analyst(llm, toolkit):
    def tournament_analyst_node(state):
        match_date = state[STATE.match_date]
        tournament = state[STATE.tournament]
        location = state.get(STATE.location, "Valencia")
        player = state[STATE.player_of_interest]
        opponent = state[STATE.opponent]

        # Herramientas específicas
        if toolkit.config["online_tools"]:
            tools = [toolkit.get_tournament_info]
        else:
            tools = [toolkit.get_mock_tournament_data]

        # Mensaje principal
        system_message = (
            f"Eres un experto analista de torneos de tenis. Debes realizar un informe detallado del torneo '{tournament}', "
            f"que se celebra en {location} el día {match_date}. Evalúa factores como el tipo de superficie, condiciones físicas del entorno "
            f"(altitud, clima habitual, velocidad de la pista), tipo de torneo, y el historial de {player} y {opponent} en este torneo o en condiciones similares.\n\n"
            "Tu objetivo es ayudar al equipo de predicción a entender el impacto del torneo sobre el rendimiento de los jugadores.\n"
            "Al final, incluye una tabla Markdown clara con los factores clave extraídos del análisis."
        )

        # Plantilla del prompt
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "Eres un asistente especializado en análisis de torneos de tenis. "
                    "Colaboras con otros agentes para tomar decisiones basadas en el torneo actual.\n\n"
                    "Usa las herramientas disponibles para obtener información detallada:\n\n"
                    "{tool_names}\n\n"
                    "{system_message}"
                ),
                ("user", "Analiza el torneo {tournament} en {location} y su impacto en {player} y {opponent}."),
                MessagesPlaceholder(variable_name=STATE.messages),
            ]
        )

        prompt = prompt.partial(system_message=system_message)
        prompt = prompt.partial(tool_names=", ".join([tool.name for tool in tools]))
        prompt = prompt.partial(tournament=tournament)
        prompt = prompt.partial(location=location)
        prompt = prompt.partial(player=player)
        prompt = prompt.partial(opponent=opponent)

        chain = prompt | llm.bind_tools(tools)

        result = chain.invoke(state[STATE.messages])

        report = ""
        if len(result.tool_calls) == 0:
            report = result.content

        return {
            STATE.messages: [result],
            REPORTS.news_report: report,
        }

    return tournament_analyst_node
