from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from tennisAgents.utils.enumerations import *
from tennisAgents.agents.utils.prompt_anatomy import PromptBuilder, TennisAnalystAnatomies

def create_social_media_analyst(llm, toolkit):
    def social_media_analyst_node(state):
        match_date = state[STATE.match_date]
        player = state[STATE.player_of_interest]
        opponent = state[STATE.opponent]
        tournament = state[STATE.tournament]

        # Herramientas disponibles según configuración
        if toolkit.config["online_tools"]:
            tools = [toolkit.get_sentiment]
        else:
            tools = [
                toolkit.get_sentiment,
            ]

        # Obtener la anatomía del prompt para analista de redes sociales
        anatomy = TennisAnalystAnatomies.social_media_analyst()
        
        # Información de herramientas
        tools_info = (
            "• get_sentiment() - Obtiene análisis de sentimiento y percepción pública en redes sociales"
        )
        
        # Contexto adicional específico del análisis de redes sociales
        additional_context = (
            "FUENTES A ANALIZAR:\n"
            "• Tweets y conversaciones en Twitter/X\n"
            "• Comentarios en foros especializados de tenis\n"
            "• Publicaciones y discusiones en Reddit\n"
            "• Cualquier indicio sobre estado físico, moral, confianza o rumores\n\n"
            "TIPOS DE INFORMACIÓN A EXTRAER:\n"
            "• Sentimiento objetivo (positivo/negativo/neutral) con métricas cuantitativas\n"
            "• Percepción subjetiva y narrativa mediática\n"
            "• Rumores sobre lesiones, cambios de entrenador o problemas personales\n"
            "• Expectativas de los fans y expertos\n"
            "• Comparación de la popularidad y apoyo en redes sociales\n\n"
            "OBJETIVO: Proporcionar insights sobre el estado mental y la percepción pública que puedan influir en el rendimiento.\n\n"
            "IMPORTANTE: Proporciona análisis específico con métricas concretas, no generalidades. Incluye porcentajes de sentimiento, ejemplos de comentarios relevantes y contexto específico de cada plataforma."
        )

        # Crear prompt estructurado usando la anatomía
        prompt = PromptBuilder.create_structured_prompt(
            anatomy=anatomy,
            tools_info=tools_info,
            additional_context=additional_context
        )

        # Inyección de variables dinámicas
        prompt = prompt.partial(current_date=match_date)
        prompt = prompt.partial(player=player)
        prompt = prompt.partial(opponent=opponent)
        prompt = prompt.partial(tournament=tournament)

        # Construcción de la cadena LLM
        chain = prompt | llm.bind_tools(tools)

        # Crear el input correcto como diccionario
        input_data = {
            "messages": state[STATE.messages],
            "user_message": f"Analiza la percepción en redes sociales de {player} y {opponent} para el torneo {tournament}."
        }

        result = chain.invoke(input_data)

        report = ""
        if len(result.tool_calls) == 0:
            report = result.content

        return {
            STATE.messages: [result],
            REPORTS.sentiment_report: report,
        }

    return social_media_analyst_node
