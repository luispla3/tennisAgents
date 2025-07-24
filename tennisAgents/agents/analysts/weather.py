from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

def create_weather_analyst(llm, toolkit):
    def weather_analyst_node(state):
        current_date = state["match_date"]
        location = state["location"]
        player = state["player_of_interest"]
        opponent = state["opponent"]
        tournament = state["tournament"]

        # Herramientas de consulta meteorológica
        if toolkit.config["online_tools"]:
            tools = [toolkit.get_weather_forecast]
        else:
            tools = [toolkit.get_mock_weather_data]  # Para testing o entorno offline

        # Mensaje al sistema para enfocar el análisis
        system_message = (
            f"Eres un analista meteorológico especializado en tenis. Tu tarea es evaluar las condiciones climáticas "
            f"esperadas para el día {current_date} en {location}, sede del torneo {tournament}, donde jugarán {player} contra {opponent}.\n\n"
            "Analiza cómo la temperatura, el viento, la humedad o la posibilidad de lluvia pueden afectar el juego. "
            "Considera el estilo de ambos jugadores y si alguno tiene un historial de mal rendimiento o lesiones bajo ciertas condiciones.\n\n"
            "Finaliza con un resumen en formato tabla Markdown de los factores clave."
        )

        # Definición del prompt con historial y herramientas
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "Eres un asistente experto en meteorología deportiva colaborando con otros analistas. "
                    "Usa las siguientes herramientas para recopilar y analizar datos climáticos:\n\n"
                    "{tool_names}\n\n"
                    "{system_message}"
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        # Rellenar con valores reales del estado
        prompt = prompt.partial(system_message=system_message)
        prompt = prompt.partial(tool_names=", ".join([tool.name for tool in tools]))

        chain = prompt | llm.bind_tools(tools)

        result = chain.invoke(state["messages"])

        report = ""
        if len(result.tool_calls) == 0:
            report = result.content

        return {
            "messages": [result],
            "weather_report": report,
        }

    return weather_analyst_node
