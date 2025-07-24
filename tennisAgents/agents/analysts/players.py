from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

def create_player_analyst(llm, toolkit):
    def player_analyst_node(state):
        match_date = state["match_date"]
        player_name = state["player_of_interest"]
        opponent_name = state["opponent"]
        surface = state["surface"]
        tournament = state["tournament"]

        # Selección dinámica de herramientas
        if toolkit.config["online_tools"]:
            tools = [toolkit.get_player_profile_openai]
        else:
            tools = [
                toolkit.get_atp_rankings,
                toolkit.get_recent_matches,
                toolkit.get_surface_winrate,
                toolkit.get_head_to_head,
                toolkit.get_injury_reports,
            ]

        # Instrucciones del rol del agente (system_message)
        system_message = (
            f"Eres un analista deportivo experto en tenis. Tu tarea es analizar en profundidad el rendimiento de {player_name} en el contexto del partido contra {opponent_name}. "
            "Debes utilizar todas las fuentes de datos disponibles para crear un informe completo que ayude al sistema de predicción a decidir con base en evidencia sólida. "
            "Analiza los siguientes puntos:\n"
            "- Ranking actual y su evolución reciente\n"
            "- Resultados recientes (últimos 5 partidos)\n"
            "- Eficiencia sobre superficie actual ({surface})\n"
            "- Historial de enfrentamientos directos contra {opponent_name}\n"
            "- Posibles lesiones o signos de fatiga\n\n"
            "Asegúrate de incluir una tabla Markdown al final con los datos clave, organizada y fácil de leer."
        )

        # Plantilla de prompt con placeholders y mensajes anteriores
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "Eres un asistente experto en tenis que colabora con otros analistas en una cadena de razonamiento. "
                    "Usa las herramientas disponibles para progresar en la elaboración del análisis. "
                    "Si no puedes completar todo el análisis, deja tu aportación parcial. "
                    "Tienes acceso a: {tool_names}.\n{system_message}\n\n"
                    "Fecha del partido: {match_date}, Torneo: {tournament}, Superficie: {surface}, Jugadores: {player_name} vs {opponent_name}",
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        # Inyección de variables al prompt
        prompt = prompt.partial(system_message=system_message)
        prompt = prompt.partial(tool_names=", ".join([tool.name for tool in tools]))
        prompt = prompt.partial(match_date=match_date)
        prompt = prompt.partial(tournament=tournament)
        prompt = prompt.partial(surface=surface)
        prompt = prompt.partial(player_name=player_name)
        prompt = prompt.partial(opponent_name=opponent_name)

        # Construcción de la cadena LLM con herramientas
        chain = prompt | llm.bind_tools(tools)

        # Ejecución del modelo con el historial de mensajes
        result = chain.invoke(state["messages"])

        report = ""
        if len(result.tool_calls) == 0:
            report = result.content

        return {
            "messages": [result],
            "player_report": report,
        }

    return player_analyst_node
