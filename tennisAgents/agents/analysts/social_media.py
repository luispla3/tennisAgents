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
            tools = [toolkit.get_twitter_sentiment]
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
            "de cara al partido que se jugará en el torneo {tournament}. "
            "Debes analizar tweets, comentarios, publicaciones en Reddit o foros, y cualquier indicio sobre estado físico, moral, confianza o rumores.\n\n"
            "Incluye tanto información objetiva (sentimiento positivo/negativo) como subjetiva (percepción, rumores, narrativa mediática).\n\n"
            "Finaliza tu informe con una tabla Markdown con los puntos clave para que sea fácil de leer."
        )

        # Prompt que incluye los mensajes anteriores y la plantilla base
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "Eres un asistente de IA experto en analizar redes sociales de jugadores de tenis, colaborando con otros agentes.\n"
                    "Usa las herramientas disponibles para extraer información útil. Si no puedes completar el análisis, aporta lo que puedas.\n"
                    "Herramientas disponibles: {tool_names}\n{system_message}\n\n"
                    "Fecha: {current_date}. Jugadores: {player} vs {opponent}, Torneo: {tournament}."
                ),
                ("user", "Analiza la percepción en redes sociales de {player} y {opponent} para el torneo {tournament}."),
                MessagesPlaceholder(variable_name=STATE.messages),
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

        result = chain.invoke(state[STATE.messages])

        report = ""
        if len(result.tool_calls) == 0:
            report = result.content

        return 
        {
            STATE.messages: [result],
            REPORTS.news_report: report,
        }

    return social_media_analyst_node
