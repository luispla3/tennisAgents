from tennisAgents.dataflows.config import get_config
from tennisAgents.dataflows.llm_utils import invoke_chat_llm, invoke_local_analyst_llm
from tennisAgents.dataflows.web_search_utils import perform_web_search


def get_sentiment_openai(player_name: str) -> str:
    config = get_config()

    if config.get("use_local_analysts", False):
        try:
            text, label = invoke_local_analyst_llm(
                "Eres un experto en análisis de sentimiento en redes sociales deportivas.",
                (
                    f"Genera un análisis de sentimiento simulado basado en el conocimiento general "
                    f"sobre el jugador de tenis {player_name}. Menciona su popularidad, estilo de juego "
                    f"y percepción pública reciente (hasta tu fecha de corte de conocimiento)."
                ),
            )
            return f"[ANÁLISIS VIA {label} - SIN BÚSQUEDA WEB EN TIEMPO REAL]\n{text}"
        except Exception as e:
            return f"Error usando modelo para sentimiento: {str(e)}"

    search_context = perform_web_search(
        f"{player_name} tennis social media sentiment news fan reaction"
    )
    return invoke_chat_llm(
        (
            f"Resume el sentimiento en redes sociales y foros sobre "
            f"el jugador de tenis {player_name}."
        ),
        f"Resultados de búsqueda web:\n\n{search_context}",
    )

