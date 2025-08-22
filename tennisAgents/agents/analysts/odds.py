from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tennisAgents.utils.enumerations import *
from tennisAgents.agents.utils.prompt_anatomy import PromptBuilder, TennisAnalystAnatomies

def create_odds_analyst(llm, toolkit):
    def odds_analyst_node(state):
        match_date = state[STATE.match_date]
        player = state[STATE.player_of_interest]
        opponent = state[STATE.opponent]
        tournament = state[STATE.tournament]

        tools = [toolkit.mock_tennis_odds]
        # Obtener la anatomía del prompt para analista de cuotas
        anatomy = TennisAnalystAnatomies.odds_analyst()
        
        # Información de herramientas
        tools_info = (
            "• mock_tennis_odds(player_a, player_b, tournament) - Genera cuotas ficticias realistas para un partido específico"
        )
        
        # Información sobre la herramienta de odds
        odds_info = """
        HERRAMIENTA DE CUOTAS DISPONIBLE:

        mock_tennis_odds(player_a, player_b, tournament)
        - player_a: Nombre del primer jugador
        - player_b: Nombre del segundo jugador
        - tournament: Nombre del torneo

        Esta herramienta genera cuotas ficticias realistas para el partido especificado, incluyendo los mismos mercados que la herramienta real pero con datos simulados basados en el ranking de los jugadores.
        """
        
        # Contexto adicional específico del análisis de cuotas
        additional_context = (
            f"{odds_info}\n\n"
            "PROCESO OBLIGATORIO:\n"
            f"1. DEBES usar UNA UNICA VEZ la herramienta 'mock_tennis_odds' con estos parámetros EXACTOS:\n"
            f"   - player_a: '{player}'\n"
            f"   - player_b: '{opponent}'\n"
            f"   - tournament: '{tournament}'\n"
            "2. NO procedas sin llamar a la herramienta primero\n"
            "3. Una vez que obtengas los datos, analiza cada mercado disponible\n\n"
            "ANÁLISIS REQUERIDO:\n"
            "• Identificación del favorito según las cuotas de Match Winner\n"
            "• Análisis de las cuotas de Set Betting para diferentes resultados\n"
            "• Evaluación de las cuotas de Set Score para marcadores específicos\n"
            "• Análisis de la cuota Both Win Set y su implicación\n"
            "• Comparación de las cuotas Player Set Win entre ambos jugadores\n"
            "• Evaluación de las cuotas Combined Bet para combinaciones específicas\n"
            "• Identificación de mercados no disponibles y su impacto\n\n"
            "IMPORTANTE: Proporciona análisis específico con números concretos, no generalidades. Incluye cuotas exactas y contexto específico del mercado.\n\n"
            "OBLIGATORIO: Llama mock_tennis_odds antes de hacer cualquier análisis."
        )

        # Crear prompt estructurado usando la anatomía
        prompt = PromptBuilder.create_structured_prompt(
            anatomy=anatomy,
            tools_info=tools_info,
            additional_context=additional_context
        )

        # Inyección de variables al prompt
        prompt = prompt.partial(player=player)
        prompt = prompt.partial(opponent=opponent)
        prompt = prompt.partial(match_date=match_date)

        chain = prompt | llm.bind_tools(tools)
        
        # Crear el input correcto como diccionario
        input_data = {
            "messages": state[STATE.messages],
            "user_message": f"Analiza las cuotas de apuestas para el partido entre {player} y {opponent}."
        }
        
        result = chain.invoke(input_data)

        # Debug: imprimir información sobre el resultado
        print(f"DEBUG - Result tool_calls: {len(result.tool_calls)}")
        print(f"DEBUG - Result content: {result.content[:200]}...")
        
        report = ""
        report = result.content

        return {
            STATE.messages: [result],
            REPORTS.odds_report: report,
        }

    return odds_analyst_node
