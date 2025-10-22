from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from tennisAgents.utils.enumerations import *
from tennisAgents.agents.utils.prompt_anatomy import PromptBuilder, TennisAnalystAnatomies

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

        # Obtener la anatomía del prompt para analista de jugadores
        anatomy = TennisAnalystAnatomies.player_analyst()
        
        # Información de herramientas
        tools_info = (
            "• get_atp_rankings() - Obtiene el ranking ATP actual con top 400 jugadores\n"
            "• get_injury_reports() - Obtiene reportes de lesiones y jugadores que regresan\n"
            "• get_recent_matches('{player_name}', '{opponent_name}', num_matches) - Últimos partidos de ambos jugadores\n"
            "• get_surface_winrate('{player_name}', 'superficie') - Winrate del jugador en una superficie específica\n"
            "• get_head_to_head('{player_name}', '{opponent_name}') - Historial de enfrentamientos entre ambos"
        )
        
        # Contexto adicional específico del partido
        additional_context = (
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
            "ANÁLISIS BASE REQUERIDO:\n"
            "• Ranking actual y evolución reciente de posiciones\n"
            "• Estado físico y reportes de lesiones recientes\n"
            "• Rendimiento en partidos recientes (últimos 20-30 partidos)\n"
            "• Eficiencia específica sobre la superficie del torneo\n"
            "• Comparación de winrates entre ambos jugadores en la superficie\n"
            "• Estadísticas head-to-head y su relevancia histórica\n"
            "• Factores que puedan influir en el resultado del partido\n\n"
            "ANÁLISIS DE CONSISTENCIA DEL FAVORITO:\n"
            "Si hay una diferencia significativa de ranking (>50 posiciones):\n"
            "• Identifica quién es el jugador favorito según ranking y forma actual\n"
            "• Evalúa la CONSISTENCIA del favorito contra jugadores de menor nivel:\n"
            "  - Tasa de victoria del favorito contra jugadores en el rango de ranking del rival\n"
            "  - Rendimiento histórico en torneos de este nivel vs torneos superiores\n"
            "  - ¿Viene de jugar torneos de categoría superior? (Grand Slams, Masters 1000, etc.)\n"
            "    Si es así, analiza su adaptación al nivel del torneo actual\n"
            "  - Contexto de la temporada: ¿Es inicio, mitad o final de temporada?\n"
            "  - ¿El favorito suele tener bajadas de rendimiento contra rivales teóricamente inferiores?\n\n"
            "• Evalúa si el jugador 'peor' está realmente en peor forma:\n"
            "  - ¿El ranking refleja su nivel actual o está en un valle temporal?\n"
            "  - ¿Ha tenido lesiones o bajón de forma reciente que expliquen su posición?\n"
            "  - ¿Su forma reciente sugiere que es mejor jugador de lo que indica su ranking, por ejemplo, si es un jugador next gen y esta empezando a hacer buenos resultados\n"
            "  - ¿Tiene historial de ser más fuerte de lo que su ranking sugiere?\n\n"
            "• PROBABILIDAD ESTIMADA: Basándote en estos factores, estima la probabilidad real\n"
            "  de que el favorito gane considerando:\n"
            "  - Su consistencia histórica contra jugadores de este perfil\n"
            "  - El nivel del torneo actual y su adaptación a él\n"
            "  - La verdadera forma actual del rival (más allá del ranking)\n"
            "  - Factores contextuales (etapa temporada, torneos previos, etc.)\n\n"
            "IMPORTANTE: Proporciona análisis específico y cuantitativo, no generalidades. Incluye estadísticas concretas, fechas relevantes y contexto específico. Las herramientas te darán información detallada y actualizada.\n\n"
            "Fecha del partido: {match_date}, Torneo: {tournament}, Superficie: {surface}, Jugadores: {player_name} vs {opponent_name}"
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

        report = ""
        if len(result.tool_calls) == 0:
            report = result.content

        return {
            STATE.messages: [result],
            REPORTS.players_report: report,
        }

    return player_analyst_node
