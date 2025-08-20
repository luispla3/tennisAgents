from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from tennisAgents.utils.enumerations import *

def create_player_analyst(llm, toolkit):
    def player_analyst_node(state):
        match_date = state[STATE.match_date]
        player_name = state[STATE.player_of_interest]
        opponent_name = state[STATE.opponent]
        surface = state.get(STATE.surface, "")
        tournament = state[STATE.tournament]

        # Selección dinámica de herramientas - usar todas las disponibles
        if toolkit.config["online_tools"]:
            tools = [
                toolkit.get_atp_rankings,
                toolkit.get_recent_matches,
                toolkit.get_surface_winrate,
                toolkit.get_head_to_head,
                toolkit.get_injury_reports,
            ]
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
            f"Eres un analista deportivo experto en tenis. Tu tarea es analizar en profundidad el rendimiento de {player_name} en el contexto del partido contra {opponent_name}."
        )

        # Plantilla de prompt con placeholders y mensajes anteriores
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "Eres un asistente experto en tenis que colabora con otros analistas en una cadena de razonamiento. "
                    "Tu objetivo es analizar el rendimiento de los jugadores usando las herramientas disponibles.\n\n"
                    "Herramientas: {tool_names}\n\n"
                    "{system_message}\n\n"
                    "HERRAMIENTAS DISPONIBLES:\n"
                    "• get_atp_rankings() - Obtiene el ranking ATP actual con top 400 jugadores\n"
                    "• get_injury_reports() - Obtiene reportes de lesiones y jugadores que regresan\n"
                    "• get_recent_matches('{player_name}', '{opponent_name}', num_matches) - Últimos partidos de ambos jugadores\n"
                    "• get_surface_winrate('{player_name}', 'superficie') - Winrate del jugador en una superficie específica\n"
                    "• get_head_to_head('{player_name}', '{opponent_name}') - Historial de enfrentamientos entre ambos\n\n"
                    "PROCESO RECOMENDADO:\n"
                    "1. Comienza obteniendo el ranking ATP para contextualizar la posición de ambos jugadores\n"
                    "2. Consulta reportes de lesiones para evaluar el estado físico actual\n"
                    "3. Analiza partidos recientes de ambos jugadores (últimos 20-30 partidos)\n"
                    "4. Evalúa el rendimiento específico en la superficie del torneo\n"
                    "5. Revisa el historial head-to-head para patrones históricos\n\n"
                    "REGLAS IMPORTANTES:\n"
                    "• Las herramientas usan OpenAI con búsqueda web, proporcionando información actualizada\n"
                    "• No hay un orden estricto - usa las herramientas según la información que necesites\n"
                    "• Para get_recent_matches, puedes especificar el número de partidos (por defecto 30)\n"
                    "• Para get_surface_winrate, usa la superficie exacta del torneo (clay, hard, grass)\n"
                    "• Todas las herramientas devuelven análisis detallados, no solo datos crudos\n\n"
                    "ANÁLISIS REQUERIDO:\n"
                    "• Ranking actual y evolución reciente de posiciones\n"
                    "• Estado físico y reportes de lesiones recientes\n"
                    "• Rendimiento en partidos recientes (últimos 20-30 partidos)\n"
                    "• Eficiencia específica sobre la superficie del torneo\n"
                    "• Comparación de winrates entre ambos jugadores en la superficie\n"
                    "• Estadísticas head-to-head y su relevancia histórica\n"
                    "• Factores que puedan influir en el resultado del partido\n\n"
                    "FORMATO DEL INFORME:\n"
                    "1. Resumen ejecutivo de los hallazgos clave\n"
                    "2. Análisis detallado por jugador\n"
                    "3. Comparación directa de fortalezas y debilidades\n"
                    "4. Predicción basada en datos objetivos\n"
                    "5. Tabla Markdown con métricas clave organizadas por categoría\n\n"
                    "IMPORTANTE: Proporciona análisis específico y cuantitativo, no generalidades. Incluye estadísticas concretas, fechas relevantes y contexto específico. Las herramientas te darán información detallada y actualizada.\n\n"
                    "Fecha del partido: {match_date}, Torneo: {tournament}, Superficie: {surface}, Jugadores: {player_name} vs {opponent_name}"
                ),
                ("user", "Analiza el rendimiento de {player_name} contra {opponent_name} en el torneo {tournament}. Sigue exactamente los pasos indicados y NO repitas llamadas."),
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

        # Crear el input correcto como diccionario
        input_data = {
            "messages": state[STATE.messages]
        }

        result = chain.invoke(input_data)

        report = ""
        if len(result.tool_calls) == 0:
            report = result.content

        return {
            STATE.messages: [result],
            REPORTS.players_report: report,
        }

    return player_analyst_node
