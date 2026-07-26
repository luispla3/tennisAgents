from tennisAgents.utils.enumerations import *
from tennisAgents.agents.utils.prompt_anatomy import PromptBuilder, TennisAnalystAnatomies
from tennisAgents.dataflows.player_utils import fetch_injury_reports, fetch_surface_winrate
from tennisAgents.dataflows.tournament_utils import merge_analyst_tournament_context, normalize_tournament
from tennisAgents.agents.utils.report_utils import sanitize_analyst_report
from tennisAgents.agents.utils.agent_utils import _record_tool_output

def create_player_analyst(llm, toolkit):
    def player_analyst_node(state):
        match_date = state[STATE.match_date]
        player_name = state[STATE.player_of_interest]
        opponent_name = state[STATE.opponent]
        tournament = state[STATE.tournament]

        injury_report = fetch_injury_reports(player_name, opponent_name)
        _record_tool_output(
            "get_injury_reports",
            {"player1_name": player_name, "player2_name": opponent_name},
            injury_report,
        )

        tournament_surface = normalize_tournament(tournament).surface or "clay"
        surface_report_player = fetch_surface_winrate(player_name, tournament_surface)
        surface_report_opponent = fetch_surface_winrate(opponent_name, tournament_surface)
        _record_tool_output(
            "get_surface_winrate",
            {"player_name": player_name, "surface": tournament_surface, "tournament": tournament},
            surface_report_player,
        )
        _record_tool_output(
            "get_surface_winrate",
            {"player_name": opponent_name, "surface": tournament_surface, "tournament": tournament},
            surface_report_opponent,
        )
        # Selección dinámica de herramientas - usar todas las disponibles
        if toolkit.config["online_tools"]:
            tools = [
                toolkit.get_atp_rankings,
                toolkit.get_recent_matches,
                toolkit.get_head_to_head,
            ]
        else:
            tools = [
                toolkit.get_atp_rankings,
                toolkit.get_recent_matches,
                toolkit.get_head_to_head,
            ]

        # Obtener la anatomía del prompt para analista de jugadores
        anatomy = TennisAnalystAnatomies.player_analyst()
        
        # Información de herramientas
        tools_info = (
            "• get_atp_rankings('{player_name}', '{opponent_name}') - Perfiles ATP desde Tennis Abstract (ranking, Elo, país, mano)\n"
            "• get_injury_reports('{player_name}', '{opponent_name}') - Historial de lesiones desde Flashscore (ya precargado abajo; no repitas la llamada)\n"
            "• get_recent_matches('{player_name}', '{opponent_name}', num_matches) - Últimos partidos desde Tennis Abstract\n"
            f"• get_surface_winrate('{player_name}', '{tournament_surface}') - Estadísticas por superficie (ya precargado abajo; no repitas la llamada)\n"
            "• get_head_to_head('{player_name}', '{opponent_name}') - Historial H2H oficial desde ATP Tour (atptour.com)"
        )
        
        # Contexto adicional específico del partido
        additional_context = (
            "PROCESO RECOMENDADO:\n"
            "1. get_atp_rankings -> ranking, Elo, perfil básico\n"
            "2. Lesiones -> usa los datos Flashscore precargados (sección DATOS DE LESIONES)\n"
            "3. get_recent_matches -> forma reciente y stats de servicio por partido\n"
            "4. Superficie/servicio -> usa DATOS DE SUPERFICIE precargados (Tennis Abstract)\n"
            "5. get_head_to_head -> historial oficial ATP (incluye event breakdown)\n\n"
            f"Superficie del torneo resuelta: {tournament_surface} (torneo: {tournament})\n\n"
            "DATOS DE LESIONES (Flashscore, ya obtenidos — no llames get_injury_reports):\n"
            f"{injury_report}\n\n"
            f"DATOS DE SUPERFICIE Y SERVICIO — {player_name} (Tennis Abstract, ya obtenidos — no llames get_surface_winrate):\n"
            f"{surface_report_player}\n\n"
            f"DATOS DE SUPERFICIE Y SERVICIO — {opponent_name} (Tennis Abstract, ya obtenidos):\n"
            f"{surface_report_opponent}\n\n"
            "REGLAS DE FIDELIDAD A LOS DATOS:\n"
            "• Cada herramienta restante se invoca COMO MÁXIMO UNA VEZ; lesiones y superficie ya están precargadas\n"
            "• PROHIBIDO escribir frases de imposibilidad ('no es posible evaluar', "
            "'no puedo proporcionar'); sintetiza con los datos parciales disponibles\n"
            "• PROHIBIDO inventar rankings, porcentajes, récords, probabilidades numéricas o estadísticas\n"
            "• PROHIBIDO usar tablas markdown en el reporte final (las tools ya devuelven tablas crudas)\n"
            "• Redacta conclusiones en prosa y bullet points; cita la fuente: (Tennis Abstract), (ATP Tour), (Flashscore) o `No disponible`\n"
            "• Si un jugador tiene filas en DATOS DE LESIONES, cítalas con fechas en la sección 2 — no digas que faltan datos\n"
            "• Si Flashscore dice 'sin registros' para un jugador, escribe `Lesiones (Flashscore): sin registros` — no afirmes que está sano\n"
            "• PROHIBIDO afirmar 'no presenta lesiones' o 'está sano' sin evidencia explícita\n"
            "• En H2H: si hay filas en event breakdown, úsalas aunque el marcador global diga 0-0\n"
            "• Si DATOS DE SUPERFICIE incluyen 1stIn/1st%/2nd%/A%, cítalos en secciones 2 y 4 — no digas que faltan\n"
            "• Si solo hay split de últimas 52 semanas (sin carrera), úsalo igualmente como fuente válida\n"
            "• Si get_surface_winrate devuelve métricas derivadas de partidos recientes, indícalo como tal\n"
            "• Para get_recent_matches puedes usar num_matches=30\n\n"
            "QUÉ SINTETIZAR (no volcar tablas):\n"
            "• Ranking, Elo y mejor ranking de carrera\n"
            "• Forma reciente en la superficie: últimos resultados relevantes con fechas y torneos\n"
            "• Estado físico / lesiones: fechas y tipo según DATOS DE LESIONES (Flashscore)\n"
            "• Servicio en la superficie: 1stIn, 1st%, 2nd%, A% — solo si aparecen en las tools\n"
            "• Winrate en superficie (carrera o muestra reciente, según lo que devuelva la tool)\n"
            "• H2H: enfrentamientos concretos del event breakdown, no solo el marcador global\n"
            "• Factores que influyen en el partido, basados exclusivamente en los datos obtenidos\n\n"
            "ESTRUCTURA DEL REPORTE (solo texto y bullet points, sin tablas):\n"
            "## 1. Resumen ejecutivo\n"
            "4-6 líneas con los hallazgos más relevantes y verificables.\n\n"
            "## 2. Conclusiones por jugador\n"
            "Subsección por jugador. Bullets con ranking, forma, servicio en superficie y lesiones (Flashscore).\n\n"
            "## 3. Comparación directa\n"
            "Similitudes y diferencias clave entre ambos, solo con datos verificados.\n\n"
            "## 4. Servicio en la superficie del torneo\n"
            "Compara el servicio de ambos en la superficie usando DATOS DE SUPERFICIE precargados (1stIn, 1st%, 2nd%, A%). "
            "Si faltan datos para uno, dilo explícitamente.\n\n"
            "## 5. Head-to-head y contexto del enfrentamiento\n"
            "Resume enfrentamientos previos del event breakdown. Si no hay H2H, indícalo.\n\n"
            "## 6. Lectura del partido\n"
            "Ventajas/desventajas cualitativas. Puedes indicar favorito y confianza (Alta/Media/Baja) "
            "como etiqueta cualitativa, SIN porcentajes numéricos inventados.\n\n"
            "## 7. Limitaciones de datos\n"
            "Lista qué no se pudo verificar o qué tools devolvieron datos insuficientes.\n\n"
            "Fecha del partido: {match_date}, Torneo: {tournament}, Superficie: "
            f"{tournament_surface}, Jugadores: {{player_name}} vs {{opponent_name}}"
        )
        additional_context = merge_analyst_tournament_context(state, additional_context)

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
            "user_message": f"Analiza el rendimiento de {player_name} contra {opponent_name} en el torneo {tournament}. Sigue exactamente los pasos indicados y NO repitas llamadas."
        }

        result = chain.invoke(input_data)

        output = {STATE.messages: [result]}
        if len(result.tool_calls) == 0:
            output[REPORTS.players_report] = sanitize_analyst_report(result.content)
        return output

    return player_analyst_node
