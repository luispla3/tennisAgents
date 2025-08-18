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

        tournament_keys = """
        "australian_open"
        "french_open"
        "wimbledon"
        "us_open"

        "indian_wells"
        "miami_open"
        "monte_carlo"
        "madrid_open"
        "italian_open"
        "canadian_open"
        "cincinnati_open"
        "shanghai_masters"
        "paris_masters"
        "National Bank Open Presented by Rogers"

        "dubai"
        "qatar_open"
        "china_open"

        "wta_australian_open"
        "wta_french_open"
        "wta_wimbledon"
        "wta_us_open"
        "wta_indian_wells"
        "wta_miami_open"
        "wta_madrid_open"
        "wta_italian_open"
        "wta_canadian_open"
        "wta_cincinnati_open"
        "wta_dubai"
        "wta_qatar_open"
        "wta_china_open"
        "wta_wuhan_open"""

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
                    "PROCESO OBLIGATORIO (SEGUIR EXACTAMENTE ESTE ORDEN):\n"
                    f"KEYS DE TORNEOS DISPONIBLES:\n{tournament_keys}\n\n"
                    "1. get_tournament_surface('tournament_key_correcta') - UNA SOLA VEZ\n"
                    f"   IMPORTANTE: Para el torneo '{tournament}', identifica la tournament_key correcta de la lista anterior\n"
                    "2. get_injury_reports() - UNA SOLA VEZ\n"
                    "3. get_atp_rankings() - UNA SOLA VEZ\n"
                    "4. Extraer IDs del ranking para ambos jugadores\n"
                    "5. get_recent_matches(ID_jugador1, ID_jugador2) - UNA SOLA VEZ\n"
                    "6. get_surface_winrate(ID_jugador1, 'superficie_obtenida') - UNA SOLA VEZ\n"
                    "7. get_surface_winrate(ID_jugador2, 'superficie_obtenida') - UNA SOLA VEZ\n"
                    "8. get_head_to_head(ID_jugador1, ID_jugador2) - UNA SOLA VEZ\n\n"
                    "REGLAS ESTRICTAS:\n"
                    "• NUNCA repitas llamadas a las mismas herramientas\n"
                    "• Una vez obtenidos los datos, procede directamente al análisis\n"
                    "• Para get_tournament_surface(), usa la tournament_key exacta, NO el nombre del torneo\n\n"
                    "ANÁLISIS REQUERIDO:\n"
                    "• Superficie del torneo y su impacto en ambos jugadores\n"
                    "• Estado físico y reportes de lesiones recientes\n"
                    "• Ranking actual y evolución reciente de posiciones\n"
                    "• Rendimiento en partidos recientes (últimos 5-10 partidos)\n"
                    "• Eficiencia específica sobre la superficie del torneo\n"
                    "• Comparación de winrates entre ambos jugadores\n"
                    "• Estadísticas head-to-head y su relevancia histórica\n"
                    "• Factores que puedan influir en el resultado del partido\n\n"
                    "FORMATO DEL INFORME:\n"
                    "1. Resumen ejecutivo de los hallazgos clave\n"
                    "2. Análisis detallado por jugador\n"
                    "3. Comparación directa de fortalezas y debilidades\n"
                    "4. Predicción basada en datos objetivos\n"
                    "5. Tabla Markdown con métricas clave organizadas por categoría\n\n"
                    "IMPORTANTE: Proporciona análisis específico y cuantitativo, no generalidades. Incluye estadísticas concretas, fechas relevantes y contexto específico.\n\n"
                    "Fecha del partido: {match_date}, Torneo: {tournament}, Superficie: {surface}, Jugadores: {player_name} vs {opponent_name}"
                ),
                ("user", "Analiza el rendimiento de {player_name} contra {opponent_name} en el torneo {tournament}. Sigue exactamente los pasos indicados y NO repitas llamadas."),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        # Inyección de variables al prompt
        prompt = prompt.partial(system_message=system_message)
        prompt = prompt.partial(tool_names=", ".join([tool.name for tool in tools]))
        prompt = prompt.partial(tournament_keys=tournament_keys)
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
