import os
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage
from tennisAgents.dataflows.config import get_config
from tennisAgents.dataflows.llm_utils import get_llm_client
from tennisAgents.dataflows.web_search_utils import perform_web_search


def get_tournament_info_openai(tournament_name: str, category: str, date: str) -> str:
    config = get_config()
    
    # Check if we should use local (Ollama) or OpenRouter analyst model
    if config.get("use_local_analysts", False):
        try:
            local_base_url = config.get("local_base_url", "http://localhost:11434/v1")
            local_model = config.get("local_model_name", "qwen3.5:2b")
            is_local = "localhost" in local_base_url or "127.0.0.1" in local_base_url
            
            if is_local:
                # Ollama local
                base_url_cleaned = local_base_url.replace("/v1", "") if local_base_url.endswith("/v1") else local_base_url
                llm = ChatOllama(
                    model=local_model,
                    base_url=base_url_cleaned,
                    temperature=0.1,
                num_ctx=16384,
                num_predict=4096,
                reasoning=False
            )
                source_label = "OLLAMA LOCAL"
            else:
                # OpenRouter
                local_api_key = config.get("local_api_key") or os.getenv("OPENROUTER_API_KEY")
                if not local_api_key:
                    raise ValueError("OPENROUTER_API_KEY no configurada")
                llm = ChatOpenAI(
                    model=local_model,
                    base_url=local_base_url,
                    api_key=local_api_key,
                    default_headers={
                        "HTTP-Referer": "https://github.com/tennisAgents",
                        "X-Title": "Tennis Agents"
                    },
                    temperature=0.7
                )
                source_label = "OPENROUTER"
                
            messages = [
                SystemMessage(content="Eres un experto en torneos de tenis ATP y Grand Slam."),
                HumanMessage(content=f"Genera un informe simulado sobre el torneo {tournament_name} (Categoría: {category}). Describe las características típicas de este torneo: superficie, velocidad de pista, condiciones habituales y contexto histórico. Menciona que este análisis es basado en conocimiento general del modelo y no en datos en tiempo real.")
            ]
            
            response = llm.invoke(messages)
            return f"[ANÁLISIS VIA {source_label} - SIN BÚSQUEDA WEB EN TIEMPO REAL]\n{response.content}"
        except Exception as e:
            return f"Error usando modelo para torneo: {str(e)}"
            
    client = get_llm_client()

    search_context = perform_web_search(
        f"{tournament_name} tennis tournament {category} {date} draw schedule surface"
    )

    response = client.chat.completions.create(
        model=config["quick_think_llm"],
        messages=[
            {
                "role": "system",
                "content": (
                    f"Resume información actual sobre el torneo {tournament_name} "
                    f"el día {date} en la categoría {category}."
                ),
            },
            {"role": "user", "content": f"Resultados de búsqueda web:\n\n{search_context}"},
        ],
        temperature=1,
        max_tokens=4096,
    )

    return response.choices[0].message.content or ""