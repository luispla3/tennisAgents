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
                toolkit.get_tournament_surface,
                toolkit.get_atp_rankings,
                toolkit.get_recent_matches,
                toolkit.get_surface_winrate,
                toolkit.get_head_to_head,
                toolkit.get_injury_reports,
            ]
        else:
            tools = [
                toolkit.get_tournament_surface,
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
            f"Eres un analista deportivo experto en tenis. Tu tarea es analizar en profundidad el rendimiento de {player_name} en el contexto del partido contra {opponent_name}. "
            "DEBES SEGUIR EXACTAMENTE ESTE ORDEN Y NO REPETIR LLAMADAS:\n\n"
            f"KEYS DE TORNEOS DISPONIBLES:\n{tournament_keys}\n\n"
            "PASO 1: get_tournament_surface('tournament_key_correcta') - SOLO UNA VEZ para obtener la superficie\n"
            f"        IMPORTANTE: Para el torneo '{tournament}', debes identificar la tournament_key correcta de la lista anterior\n"
            f"        y usar esa key exacta (no el nombre '{tournament}') en la llamada get_tournament_surface()\n"
            "PASO 2: get_injury_reports() - SOLO UNA VEZ \n"
            "PASO 3: get_atp_rankings() - SOLO UNA VEZ\n"
            "PASO 4: Extraer IDs del ranking para {player_name} y {opponent_name}\n"
            "PASO 5: get_recent_matches(ID_jugador1, ID_jugador2) - SOLO UNA VEZ\n"
            "PASO 6: get_surface_winrate(ID_jugador1, 'superficie_obtenida') - SOLO UNA VEZ\n"
            "PASO 7: get_surface_winrate(ID_jugador2, 'superficie_obtenida') - SOLO UNA VEZ\n"
            "PASO 8: get_head_to_head(ID_jugador1, ID_jugador2) - SOLO UNA VEZ\n"
            "PASO 9: Analizar y crear informe\n\n"
            "REGLAS ESTRICTAS:\n"
            "- NUNCA llames a get_tournament_surface más de una vez\n"
            "- NUNCA llames a get_injury_reports más de una vez\n"
            "- NUNCA llames a get_atp_rankings más de una vez\n"
            "- NUNCA llames a get_recent_matches más de una vez\n"
            "- NUNCA llames a get_surface_winrate más de dos veces\n"
            "- NUNCA llames a get_head_to_head más de una vez\n"
            "- NUNCA repitas las mismas llamadas\n"
            "- Una vez que tengas los datos, procede directamente al análisis\n"
            "- Si ya obtuviste datos de un jugador, NO vuelvas a llamar para el mismo jugador\n"
            "- Para get_tournament_surface(), usa la tournament_key correcta, NO el nombre del torneo\n\n"
            "Análisis requerido:\n"
            "- Superficie del torneo (usar get_tournament_surface primero)\n"
            "- Reportes de lesiones recientes (verificar si los jugadores están lesionados)\n"
            "- Ranking actual y evolución reciente\n"
            "- Partidos recientes de ambos jugadores\n"
            "- Eficiencia sobre superficie obtenida\n"
            "- Comparación de winrates entre ambos jugadores\n"
            "- Estadísticas head-to-head entre ambos jugadores\n"
            "- Incluir tabla Markdown con datos clave"
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
                    "Fecha del partido: {match_date}, Torneo: {tournament}, Superficie: {surface}, Jugadores: {player_name} vs {opponent_name}\n\n"
                    "TOURNAMENT KEYS DISPONIBLES:\n{tournament_keys}\n\n"
                    "INSTRUCCIONES ESTRICTAS:\n"
                    "1. get_tournament_surface('tournament_key_correcta') - UNA SOLA VEZ PRIMERO\n"
                    "   IMPORTANTE: Para el torneo '{tournament}', identifica y usa la tournament_key correcta de la lista\n"
                    "2. get_injury_reports() - UNA SOLA VEZ\n"
                    "3. get_atp_rankings() - UNA SOLA VEZ\n"
                    "4. get_recent_matches(ID_jugador1, ID_jugador2) - UNA SOLA VEZ\n"
                    "5. get_surface_winrate(ID_jugador1, superficie_obtenida) - UNA SOLA VEZ\n"
                    "6. get_surface_winrate(ID_jugador2, superficie_obtenida) - UNA SOLA VEZ\n"
                    "7. get_head_to_head(ID_jugador1, ID_jugador2) - UNA SOLA VEZ\n"
                    "8. Analizar y crear informe\n\n"
                    "NO REPETIR LLAMADAS - NO VOLVER A CONSULTAR DATOS YA OBTENIDOS\n"
                    "PARA get_tournament_surface(): USA LA TOURNAMENT_KEY EXACTA, NO EL NOMBRE DEL TORNEO",
                ),
                ("user", "Analiza el rendimiento de {player_name} contra {opponent_name} en el torneo {tournament}. IMPORTANTE: Sigue exactamente los pasos indicados y NO repitas llamadas. Para get_tournament_surface(), identifica la tournament_key correcta de la lista proporcionada."),
                MessagesPlaceholder(variable_name=STATE.messages),
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

        result = chain.invoke(state[STATE.messages])

        report = ""
        if len(result.tool_calls) == 0:
            report = result.content

        return {
            STATE.messages: [result],
            REPORTS.players_report: report,
        }

    return player_analyst_node
