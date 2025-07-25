from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from tennisAgents.utils.enumerations import REPORTS

def create_odds_analyst(llm, toolkit):
    def odds_analyst_node(state):
        match_date = state["match_date"]
        player = state["player_of_interest"]
        opponent = state["opponent"]

        if toolkit.config["online_tools"]:
            tools = [toolkit.get_odds_data]
        else:
            tools = [toolkit.get_mock_odds_data]

        system_message = (
            f"Eres un analista de apuestas deportivas. Tu tarea es examinar las cuotas ofrecidas por las casas de apuestas "
            f"para el partido entre {player} y {opponent} que se disputa el {match_date}.\n\n"
            "Debes identificar:\n"
            "- Qué jugador parte como favorito según las cuotas.\n"
            "- Qué casas ofrecen cuotas significativamente distintas.\n"
            "- Si las cuotas han variado en las últimas horas y qué puede significar eso.\n"
            "- Cualquier patrón que indique que el mercado apuesta fuertemente a una dirección.\n\n"
            "Al final del informe, añade una tabla Markdown con las cuotas por casa y cualquier observación clave."
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "Actúas como parte de un sistema de IA que asiste en la predicción de partidos de tenis. "
                    "Tu enfoque es el análisis de mercados de apuestas. Colabora con otros agentes y proporciona observaciones valiosas usando las herramientas disponibles:\n\n"
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
        if len(result.tool_calls) == 0:
            report = result.content

        return {
            "messages": [result],
            REPORTS.odds_report: report,
        }

    return odds_analyst_node
