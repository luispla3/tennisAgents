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
            "• get_sentiment() - Obtiene análisis de sentimiento y percepción pública en redes sociales."
        )
        
        # Contexto adicional específico del análisis de redes sociales
        additional_context = (
            "FUENTES A ANALIZAR:\n"
            "• Tweets y conversaciones en Twitter/X\n"
            "• Comentarios en foros especializados de tenis\n"
            "• Publicaciones y discusiones en Reddit\n"
            "• Conversación pública reciente relacionada con los jugadores o el torneo\n\n"
            "TIPOS DE INFORMACIÓN A EXTRAER:\n"
            "• Sentimiento objetivo (positivo/negativo/neutral) con métricas cuantitativas\n"
            "• Narrativas públicas o temas recurrentes claramente observables\n"
            "• Volumen relativo de conversación si la herramienta lo proporciona\n"
            "• Ejemplos representativos de comentarios o temas, cuando estén disponibles\n"
            "• Comparación del nivel de atención pública entre ambos jugadores, si puede verificarse\n\n"
            "OBJETIVO: Documentar la percepción pública y el sentimiento observable en redes sociales de forma descriptiva y verificable.\n\n"
            "IMPORTANTE:\n"
            "• Proporciona análisis específico con métricas concretas, no generalidades\n"
            "• Incluye porcentajes de sentimiento, ejemplos de comentarios relevantes y contexto específico de cada plataforma cuando estén disponibles\n"
            "• No presentes rumores no verificados como hechos\n"
            "• No infieras estado mental, confianza o rendimiento futuro a partir de la conversación social\n"
            "• No hagas predicciones ni recomendaciones"
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
            "user_message": f"Recopila y resume la percepción pública en redes sociales sobre {player} y {opponent} para el torneo {tournament}."
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
