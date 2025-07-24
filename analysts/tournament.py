from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

def create_tournament_analyst(llm, toolkit):
    def tournament_analyst_node(state):
        current_date = state["match_date"]
        tournament = state["tournament"]
        location = state["location"]
        player = state["player_of_interest"]
        opponent = state["opponent"]

        # Herramientas específicas
        if toolkit.config["online_tools"]:
            tools = [toolkit.get_tournament_info]
        else:
            tools = [toolkit.get_mock_tournament_data]

        # Mensaje principal
        system_message = (
            f"Eres un experto analista de torneos de tenis. Debes realizar un informe detallado del torneo '{tournament}', "
            f"que se celebra en {location} el día {current_date}. Evalúa factores como el tipo de superficie, condiciones físicas del entorno "
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
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        prompt = prompt.partial(system_message=system_message)
        prompt = prompt.partial(tool_names=", ".join([tool.name for tool in tools]))

        chain = prompt | llm.bind_tools(tools)
        result = chain.invoke(state["messages"])

        report = ""
        if len(getattr(result, "tool_calls", [])) == 0:
            report = result.content

        return {
            "messages": [result],
            "tournament_report": report,
        }

    return tournament_analyst_node
