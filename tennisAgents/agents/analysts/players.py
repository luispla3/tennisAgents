from tennisAgents.utils.enumerations import *
from tennisAgents.agents.utils.prompt_anatomy import PromptBuilder, TennisAnalystAnatomies

def create_player_analyst(llm, toolkit):
    def player_analyst_node(state):
        match_date = state[STATE.match_date]
        player_name = state[STATE.player_of_interest]
        opponent_name = state[STATE.opponent]
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

        # Obtener la anatomía del prompt para analista de jugadores
        anatomy = TennisAnalystAnatomies.player_analyst()
        
        # Información de herramientas
        tools_info = (
            "• get_atp_rankings('{player_name}', '{opponent_name}') - Busca en la pagina web de la ATP el ranking ATP actual y el mejor ranking de su carrera para ambos jugadores\n"
            "• get_injury_reports() - Obtiene reportes de lesiones y jugadores que regresan\n"
            "• get_recent_matches('{player_name}', '{opponent_name}', num_matches) - Últimos partidos de ambos jugadores\n"
            "• get_surface_winrate('{player_name}', 'superficie') - Winrate del jugador en una superficie específica\n"
            "• get_head_to_head('{player_name}', '{opponent_name}') - Historial de enfrentamientos entre ambos"
        )
        
        # Contexto adicional específico del partido
        additional_context = (
            "PROCESO RECOMENDADO:\n"
            "1. Comienza obteniendo el ranking ATP para contextualizar la posición de ambos jugadores\n"
            "2. Consulta reportes de lesiones para documentar el estado físico actual\n"
            "3. Reúne partidos recientes de ambos jugadores (últimos 20-30 partidos)\n"
            "4. Revisa el rendimiento específico en la superficie del torneo\n"
            "5. Consulta el historial head-to-head entre ambos\n\n"
            "REGLAS IMPORTANTES:\n"
            "• Las herramientas usan OpenAI con búsqueda web, proporcionando información actualizada\n"
            "• No hay un orden estricto - usa las herramientas según la información que necesites\n"
            "• Para get_recent_matches, puedes especificar el número de partidos (por defecto 30)\n"
            "• Para get_surface_winrate, usa la superficie exacta del torneo (clay, hard, grass)\n"
            "• Si una herramienta no devuelve un dato concreto, indícalo como no disponible\n\n"
            "INFORMACIÓN BASE REQUERIDA:\n"
            "• Ranking actual y mejor ranking histórico de ambos jugadores\n"
            "• Estado físico y reportes de lesiones recientes, si los hay\n"
            "• Rendimiento en partidos recientes (últimos 20-30 partidos)\n"
            "• Rendimiento específico sobre la superficie del torneo\n"
            "• Comparación de winrates entre ambos jugadores en la superficie\n"
            "• Historial head-to-head y resultados relevantes\n\n"
            "ESTRUCTURA OBLIGATORIA DEL REPORTE FINAL:\n"
            "1. Encabeza el documento con `## 1. Resumen Ejecutivo` y resume en 4-6 líneas los hallazgos más relevantes.\n"
            "2. Añade `## 2. Análisis por Jugador` con sub-secciones claras para cada jugador y su contexto reciente.\n"
            "3. Continúa con `## 3. Comparación directa` destacando similitudes y diferencias clave.\n"
            "4. Presenta `## 4. Tabla de métricas clave` con una tabla markdown (| col1 | col2 | ...) que muestre estadísticas comparables.\n"
            "5. Cierra con `## 5. Observaciones objetivas` para resumir diferencias relevantes sin hacer predicciones.\n\n"
            "IMPORTANTE:\n"
            "• No hagas predicciones del partido, del set ni estimaciones de probabilidad\n"
            "• No asignes puntuaciones subjetivas al servicio ni a otras cualidades del juego\n"
            "• No des recomendaciones de apuestas ni estrategia\n"
            "• Proporciona información específica y cuantitativa, no generalidades\n"
            "• Incluye estadísticas concretas, fechas relevantes y contexto verificable\n"
            "• Si un dato no puede comprobarse con las herramientas, indícalo explícitamente como no disponible\n\n"
            "Fecha del partido: {match_date}, Torneo: {tournament}, Superficie: la superficie del torneo, Jugadores: {player_name} vs {opponent_name}"
        )

        # Crear prompt estructurado usando la anatomía
        prompt = PromptBuilder.create_structured_prompt(
            anatomy=anatomy,
            tools_info=tools_info,
            additional_context=additional_context
        )

        # Inyección de variables al prompt
        prompt = prompt.partial(match_date=match_date)
        prompt = prompt.partial(tournament=tournament)
        prompt = prompt.partial(player_name=player_name)
        prompt = prompt.partial(opponent_name=opponent_name)

        # Construcción de la cadena LLM con herramientas
        chain = prompt | llm.bind_tools(tools)

        # Crear el input correcto como diccionario
        input_data = {
            "messages": state[STATE.messages],
            "user_message": f"Recopila y compara información objetiva de {player_name} y {opponent_name} para el torneo {tournament}. Sigue exactamente los pasos indicados y no repitas llamadas."
        }

        result = chain.invoke(input_data)

        report = ""
        if len(result.tool_calls) == 0:  #len(result.tool_calls) == 0 significa: "En esta respuesta específica que acabo de generar, NO estoy pidiendo usar ninguna herramienta más".
            report = result.content

        return {
            STATE.messages: [result],
            REPORTS.players_report: report,
        }

    return player_analyst_node
