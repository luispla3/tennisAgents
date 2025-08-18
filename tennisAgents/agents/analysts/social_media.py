from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from tennisAgents.utils.enumerations import *

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
                toolkit.get_twitter_sentiment,
                toolkit.get_tennis_forum_sentiment,
                toolkit.get_reddit_sentiment,
            ]

        # Instrucciones específicas del analista
        system_message = (
            f"Eres un analista especializado en recopilar y analizar la opinión pública sobre jugadores de tenis. "
            f"Tu tarea es elaborar un informe detallado sobre la percepción actual de {player} y {opponent} en redes sociales y foros de tenis, "
            f"de cara al partido que se jugará en el torneo {tournament}."
        )

        # Prompt que incluye los mensajes anteriores y la plantilla base
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "Eres un asistente de IA experto en analizar redes sociales de jugadores de tenis, colaborando con otros agentes.\n"
                    "Tu objetivo es extraer información valiosa sobre la percepción pública que pueda influir en el rendimiento.\n\n"
                    "Herramientas: {tool_names}\n\n"
                    "{system_message}\n\n"
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
                    "FORMATO DEL INFORME:\n"
                    "1. Resumen ejecutivo del sentimiento general hacia ambos jugadores\n"
                    "2. Análisis detallado por plataforma (Twitter, foros, Reddit)\n"
                    "3. Comparación de la percepción entre ambos jugadores\n"
                    "4. Identificación de temas recurrentes y preocupaciones\n"
                    "5. Impacto potencial en la confianza y motivación\n"
                    "6. Tabla Markdown con métricas clave organizadas por plataforma y jugador\n\n"
                    "IMPORTANTE: Proporciona análisis específico con métricas concretas, no generalidades. Incluye porcentajes de sentimiento, ejemplos de comentarios relevantes y contexto específico de cada plataforma.\n\n"
                    "Fecha: {current_date}. Jugadores: {player} vs {opponent}, Torneo: {tournament}."
                ),
                ("user", "Analiza la percepción en redes sociales de {player} y {opponent} para el torneo {tournament}."),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        # Inyección de variables dinámicas
        prompt = prompt.partial(system_message=system_message)
        prompt = prompt.partial(tool_names=", ".join([tool.name for tool in tools]))
        prompt = prompt.partial(current_date=match_date)
        prompt = prompt.partial(player=player)
        prompt = prompt.partial(opponent=opponent)
        prompt = prompt.partial(tournament=tournament)

        # Construcción de la cadena LLM
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
            REPORTS.sentiment_report: report,
        }

    return social_media_analyst_node
