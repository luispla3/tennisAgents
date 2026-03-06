from tennisAgents.utils.enumerations import *
from tennisAgents.agents.utils.prompt_anatomy import PromptBuilder, TennisAnalystAnatomies

def create_news_analyst(llm, toolkit):
    def news_analyst_node(state):
        current_date = state[STATE.match_date]
        player = state[STATE.player_of_interest]
        opponent = state[STATE.opponent]
        tournament = state[STATE.tournament]

        # Herramientas según configuración
        if toolkit.config["online_tools"]:
            tools = [toolkit.get_news]
        else:
            tools = [
                toolkit.get_news,
            ]

        # Obtener la anatomía del prompt para analista de noticias
        anatomy = TennisAnalystAnatomies.news_analyst()
        
        # Información de herramientas
        tools_info = (
            "• get_news() - Obtiene noticias recientes sobre jugadores y torneos de tenis."
        )
        
        # Contexto adicional específico del análisis de noticias
        additional_context = (
            "OBJETIVO: Identificar información crítica que pueda influir en el rendimiento de los jugadores, incluyendo:\n"
            "• Lesiones recientes o problemas físicos, sobretodo en los partidos anteriores de ese toreno si los hay, para ello habra que investigar bien en las noticias\n"
            "• Cambios de entrenador o equipo técnico\n"
            "• Declaraciones polémicas o presión mediática\n"
            "• Estado mental o motivacional\n"
            "• Rendimiento en torneos recientes\n"
            "• Rivalidades o historial personal\n\n"
            "INSTRUCCIONES TÉCNICAS:\n"
            "• Para búsquedas con get_news: usa ÚNICAMENTE el nombre del jugador (ej: 'Christopher O'Connell', NO 'Christopher O'Connell 2025 Motorola razr Grandstand Court')\n"
            "• Incluye noticias generales del circuito ATP/WTA si son relevantes para el análisis del partido\n\n"
            "IMPORTANTE: Proporciona análisis granular y específico, no generalidades como 'las tendencias son mixtas'. Incluye fechas, citas relevantes y contexto específico.\n\n"
            "Fecha actual: {current_date}. Jugadores: {player} vs {opponent}, Torneo: {tournament}."
        )

        # Crear prompt estructurado usando la anatomía
        prompt = PromptBuilder.create_structured_prompt(
            anatomy=anatomy,
            tools_info=tools_info,
            additional_context=additional_context
        )

        # Rellenamos variables dinámicas
        prompt = prompt.partial(current_date=current_date)
        prompt = prompt.partial(player=player)
        prompt = prompt.partial(opponent=opponent)
        prompt = prompt.partial(tournament=tournament)

        #para crear un agente se necesita el modelo (llm), las herramientas (tools) y el prompt (prompt).
        chain = prompt | llm.bind_tools(tools)

        # Crear el input correcto como diccionario
        input_data = {
            "messages": state[STATE.messages],
            "user_message": f"Analiza las noticias más relevantes sobre {player} y {opponent} para el torneo {tournament}."
        }

        result = chain.invoke(input_data)     #Es un Message que puede ser de 2 tipos: AIMessage, ToolMessage.

        report = ""
        if len(result.tool_calls) == 0:  #len(result.tool_calls) == 0 significa: "En esta respuesta específica que acabo de generar, NO estoy pidiendo usar ninguna herramienta más".
            report = result.content      #result.content es el contenido de la respuesta del agente (es el texto del Message).

        return {
            STATE.messages: [result],       #AgentState hereda de MessagesState (de langgraph), lo que significa que el campo messages es una lista de mensajes de LangChain (BaseMessage). STATE['messages'] es una lista que crece (append-only por defecto en LangGraph).
            REPORTS.news_report: report,
        }

    return news_analyst_node
