from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from tennisAgents.utils.enumerations import *
from tennisAgents.agents.utils.prompt_anatomy import PromptBuilder, TennisAnalystAnatomies

def create_match_live_analyst(llm, toolkit):
    def match_live_analyst_node(state):
        match_date = state[STATE.match_date]
        player_a = state[STATE.player_of_interest]
        player_b = state[STATE.opponent]
        tournament = state[STATE.tournament]
        surface = state.get(STATE.surface, "")
        # Herramienta para obtener datos reales del partido en vivo
        tools = [toolkit.get_match_live_data]

        # Obtener la anatomía del prompt para analista de partidos en vivo
        anatomy = TennisAnalystAnatomies.match_live_analyst()

        # Información de herramientas
        tools_info = (
            "• get_match_live_data(player_a, player_b, tournament) - Accede a URLs específicas de Flashcore y SofaScore para obtener datos del partido Jannik Sinner vs Carlos Alcaraz del 07/09/2025"
        )

        # Contexto adicional específico para el análisis del partido
        additional_context = (
            "ANÁLISIS DE PARTIDO DE TENIS - FLASHCORE Y SOFASCORE:\n"
            f"1. DEBES usar UNA UNICA VEZ la herramienta 'get_match_live_data' con estos parámetros EXACTOS:\n"
            f"   - player_a: '{player_a}'\n"
            f"   - player_b: '{player_b}'\n"
            f"   - tournament: '{tournament}'\n"
            "2. Esta herramienta intentará acceder a Flashcore, SofaScore y otras fuentes deportivas para el partido Jannik Sinner vs Carlos Alcaraz del 07/09/2025\n"
            "3. NO procedas sin llamar a la herramienta primero\n"
            "4. Una vez que obtengas los datos, analiza la información del partido\n\n"
            "ESTRUCTURA DE DATOS A EXTRAER (BASADO EN EL FORMATO DE FLASHCORE):\n\n"
            "**SECCIÓN SERVICIO (SERVICIO):**\n"
            "- Aces: [número para cada jugador]\n"
            "- Dobles faltas: [número para cada jugador]\n"
            "- Porcentaje 1er servicio: [% para cada jugador]\n"
            "- Pts. ganados 1er serv.: [% (X/Y) para cada jugador]\n"
            "- Pts. ganados 2º serv.: [% (X/Y) para cada jugador]\n"
            "- Puntos break salvados: [% (X/Y) para cada jugador]\n"
            "- Velocidad media del primer servicio: [km/h para cada jugador]\n"
            "- Velocidad media del segundo servicio: [km/h para cada jugador]\n\n"
            "**SECCIÓN RESTO (RETURN):**\n"
            "- Pts. ganados 1ª devoluc.: [% (X/Y) para cada jugador]\n"
            "- Pts. ganados 2ª devoluc.: [% (X/Y) para cada jugador]\n"
            "- Puntos break convertidos: [% (X/Y) para cada jugador]\n\n"
            "**SECCIÓN PUNTOS (PUNTOS):**\n"
            "- Golpes Ganadores: [número para cada jugador]\n"
            "- Errores No Forzados: [número para cada jugador]\n"
            "- Puntos ganados en red: [% (X/Y) para cada jugador]\n"
            "- Puntos ganados servicio: [% (X/Y) para cada jugador]\n"
            "- Puntos ganados resto: [% (X/Y) para cada jugador]\n"
            "- Total puntos ganados: [% (X/Y) para cada jugador]\n"
            "- Últimos diez puntos: [número para cada jugador]\n"
            "- Puntos de partido salvados: [número para cada jugador]\n\n"
            "**SECCIÓN JUEGOS (JUEGOS):**\n"
            "- Juegos ganados servicio: [% (X/Y) para cada jugador]\n"
            "- Juegos ganados resto: [% (X/Y) para cada jugador]\n"
            "- Total juegos ganados: [% (X/Y) para cada jugador]\n\n"
            "INFORMACIÓN OBLIGATORIA EN LA SALIDA:\n"
            "1. Confirmación de acceso:\n"
            "   - ¿Acceso exitoso a Flashcore? (SÍ/NO)\n"
            "   - URL consultada\n"
            "   - Estado del partido encontrado\n\n"
            "2. Información COMPLETA del partido (OBLIGATORIO - NO OMITIR NADA):\n"
            "   - Resultado final por sets \n"
            "   - Fecha del partido exacta\n"
            "   - Torneo\n"
            "   - TODAS las estadísticas disponibles organizadas por secciones:\n\n"
            "   **SERVICIO:**\n"
            "   - Aces: Carlos Alcaraz: [X], Jannik Sinner: [Y]\n"
            "   - Dobles faltas: Carlos Alcaraz: [X], Jannik Sinner: [Y]\n"
            "   - Porcentaje 1er servicio: Carlos Alcaraz: [X%], Jannik Sinner: [Y%]\n"
            "   - Pts. ganados 1er serv.: Carlos Alcaraz: [X% (A/B)], Jannik Sinner: [Y% (C/D)]\n"
            "   - Pts. ganados 2º serv.: Carlos Alcaraz: [X% (A/B)], Jannik Sinner: [Y% (C/D)]\n"
            "   - Puntos break salvados: Carlos Alcaraz: [X% (A/B)], Jannik Sinner: [Y% (C/D)]\n"
            "   - Velocidad media 1er serv.: Carlos Alcaraz: [X km/h], Jannik Sinner: [Y km/h]\n"
            "   - Velocidad media 2º serv.: Carlos Alcaraz: [X km/h], Jannik Sinner: [Y km/h]\n\n"
            "   **RESTO:**\n"
            "   - Pts. ganados 1ª devoluc.: Carlos Alcaraz: [X% (A/B)], Jannik Sinner: [Y% (C/D)]\n"
            "   - Pts. ganados 2ª devoluc.: Carlos Alcaraz: [X% (A/B)], Jannik Sinner: [Y% (C/D)]\n"
            "   - Puntos break convertidos: Carlos Alcaraz: [X% (A/B)], Jannik Sinner: [Y% (C/D)]\n\n"
            "   **PUNTOS:**\n"
            "   - Golpes Ganadores: Carlos Alcaraz: [X], Jannik Sinner: [Y]\n"
            "   - Errores No Forzados: Carlos Alcaraz: [X], Jannik Sinner: [Y]\n"
            "   - Puntos ganados en red: Carlos Alcaraz: [X% (A/B)], Jannik Sinner: [Y% (C/D)]\n"
            "   - Puntos ganados servicio: Carlos Alcaraz: [X% (A/B)], Jannik Sinner: [Y% (C/D)]\n"
            "   - Puntos ganados resto: Carlos Alcaraz: [X% (A/B)], Jannik Sinner: [Y% (C/D)]\n"
            "   - Total puntos ganados: Carlos Alcaraz: [X% (A/B)], Jannik Sinner: [Y% (C/D)]\n"
            "   - Últimos diez puntos: Carlos Alcaraz: [X], Jannik Sinner: [Y]\n"
            "   - Puntos de partido salvados: Carlos Alcaraz: [X], Jannik Sinner: [Y]\n\n"
            "   **JUEGOS:**\n"
            "   - Juegos ganados servicio: Carlos Alcaraz: [X% (A/B)], Jannik Sinner: [Y% (C/D)]\n"
            "   - Juegos ganados resto: Carlos Alcaraz: [X% (A/B)], Jannik Sinner: [Y% (C/D)]\n"
            "   - Total juegos ganados: Carlos Alcaraz: [X% (A/B)], Jannik Sinner: [Y% (C/D)]\n\n"
            "3. Análisis del partido:\n"
            "   - Resumen del desarrollo del partido\n"
            "   - Puntos clave y momentos importantes\n"
            "   - Rendimiento de cada jugador\n"
            "   - Estadísticas comparativas\n\n"
            "INSTRUCCIONES CRÍTICAS - SOLO DATOS REALES:\n"
            "• NUNCA inventes o generes estadísticas ficticias\n"
            "• SOLO reporta datos que veas REALMENTE en las fuentes consultadas\n"
            "• Si no puedes acceder a Flashcore o SofaScore, la herramienta buscará en otras fuentes deportivas\n"
            "• Si no puedes acceder a ninguna fuente o no ves datos, escribe 'NO DISPONIBLE' o 'ERROR DE ACCESO'\n"
            "• En Flashcore, busca específicamente las secciones 'SERVICIO', 'RESTO', 'PUNTOS' y 'JUEGOS'\n"
            "• En SofaScore, busca la pestaña 'Statistics' y las estadísticas detalladas del partido\n"
            "• En otras fuentes, busca estadísticas similares (aces, dobles faltas, porcentajes, etc.)\n"
            "• Extrae ÚNICAMENTE los valores numéricos que aparezcan REALMENTE en las fuentes\n"
            "• Los valores aparecen como números enteros o porcentajes con fracciones (X/Y)\n"
            "• Si no encuentras un dato específico, escribe 'NO DISPONIBLE' - NO lo inventes\n"
            "• Confirma qué fuentes pudiste consultar y cuáles no\n"
            "• Los datos deben ser reales y actualizados del partido\n"
            "• Si ves estadísticas en las fuentes, extrae esos números exactos\n"
            "• Si no puedes acceder a las fuentes o hay errores, reporta el problema específico\n"
            "• NO generes números aleatorios o estimaciones\n"
            "• NO uses datos de partidos anteriores o de tu conocimiento\n"
            "• SOLO datos extraídos directamente de las fuentes web consultadas\n"
            "• SIEMPRE indica claramente qué información NO pudiste encontrar\n"
            "• OBLIGATORIO: Extrae y muestra TODA la información disponible, NO omitas nada\n"
            "• Incluye el resultado exacto por sets\n"
            "• Muestra TODAS las estadísticas numéricas disponibles\n"
            "• NO uses frases como 'no incluida en detalle aquí por limitación de resumen'\n"
            "• SIEMPRE incluye los detalles completos del partido\n"
            "• Reporta cualquier problema de acceso o limitación encontrada\n"
            "• Confirma que la información obtenida es real y actualizada\n"
            "• Incluye evidencia detallada de lo encontrado en la página\n\n"
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
        prompt = prompt.partial(surface=surface)
        prompt = prompt.partial(player_a=player_a)
        prompt = prompt.partial(player_b=player_b)

        # Construcción de la cadena LLM con herramientas
        chain = prompt | llm.bind_tools(tools)

        # Crear el input correcto como diccionario
        input_data = {
            "messages": state[STATE.messages],
            "user_message": f"Analiza el partido Jannik Sinner vs Carlos Alcaraz del 07/09/2025. Accede a la URL específica de Flashcore y obtén todos los datos disponibles del partido: resultado, estadísticas y información completa."
        }

        result = chain.invoke(input_data)

        # Generar reporte basado en el resultado
        report = result.content
        if hasattr(result, 'tool_calls') and result.tool_calls:
            # Si hay tool calls, el contenido puede estar en el resultado final
            report = result.content

        return {
            STATE.messages: [result],
            REPORTS.match_live_report: report,
        }

    return match_live_analyst_node
