import os
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage
from tennisAgents.dataflows.config import get_config
from tennisAgents.dataflows.llm_utils import get_llm_client
from tennisAgents.dataflows.web_search_utils import perform_web_search

def get_sentiment_openai(player_name: str) -> str:
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
                SystemMessage(content="Eres un experto en análisis de sentimiento en redes sociales deportivas."),
                HumanMessage(content=f"Genera un análisis de sentimiento simulado basado en el conocimiento general sobre el jugador de tenis {player_name}. Menciona su popularidad, estilo de juego y percepción pública reciente (hasta tu fecha de corte de conocimiento).")
            ]
            
            response = llm.invoke(messages)
            return f"[ANÁLISIS VIA {source_label} - SIN BÚSQUEDA WEB EN TIEMPO REAL]\n{response.content}"
        except Exception as e:
            return f"Error usando modelo para sentimiento: {str(e)}"

    # Fallback to original online implementation
    client = get_llm_client()

    search_context = perform_web_search(
        f"{player_name} tennis social media sentiment news fan reaction"
    )

    response = client.chat.completions.create(
        model=config["quick_think_llm"],
        messages=[
            {
                "role": "system",
                "content": (
                    f"Resume el sentimiento en redes sociales y foros sobre "
                    f"el jugador de tenis {player_name}."
                ),
            },
            {"role": "user", "content": f"Resultados de búsqueda web:\n\n{search_context}"},
        ],
        temperature=1,
        max_tokens=4096,
    )

    return response.choices[0].message.content or ""