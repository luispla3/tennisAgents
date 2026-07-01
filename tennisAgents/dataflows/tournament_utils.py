from tennisAgents.dataflows.config import get_config
from tennisAgents.dataflows.llm_utils import invoke_chat_llm, invoke_local_analyst_llm
from tennisAgents.dataflows.web_search_utils import perform_web_search


def get_tournament_info_openai(tournament_name: str, category: str, date: str) -> str:
    config = get_config()

    if config.get("use_local_analysts", False):
        try:
            text, label = invoke_local_analyst_llm(
                "Eres un experto en torneos de tenis ATP y Grand Slam.",
                (
                    f"Genera un informe simulado sobre el torneo {tournament_name} "
                    f"(Categoría: {category}). Describe las características típicas de este torneo: "
                    f"superficie, velocidad de pista, condiciones habituales y contexto histórico. "
                    f"Menciona que este análisis es basado en conocimiento general del modelo y no "
                    f"en datos en tiempo real."
                ),
            )
            return f"[ANÁLISIS VIA {label} - SIN BÚSQUEDA WEB EN TIEMPO REAL]\n{text}"
        except Exception as e:
            return f"Error usando modelo para torneo: {str(e)}"

    search_context = perform_web_search(
        f"{tournament_name} tennis tournament {category} {date} draw schedule surface"
    )
    return invoke_chat_llm(
        (
            f"Resume información actual sobre el torneo {tournament_name} "
            f"el día {date} en la categoría {category}."
        ),
        f"Resultados de búsqueda web:\n\n{search_context}",
    )

