import os
from openai import OpenAI
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from tennisAgents.dataflows.config import get_config

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
                llm = ChatOpenAI(
                    model=local_model,
                    base_url=local_base_url,
                    api_key=config.get("local_api_key", "ollama"),
                    temperature=0.7
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
    client = OpenAI(base_url=config["backend_url"])

    response = client.responses.create(
        model=config["quick_think_llm"],
        input=[
            {
                "role": "system",
                "content": [
                    {
                        "type": "input_text",
                        "text": f"Puedes buscar en Redes Sociales y Foros sobre {player_name} y resumir el sentimiento de las publicaciones?",
                    }
                ],
            }
        ],
        text={"format": {"type": "text"}},
        reasoning={},
        tools=[
            {
                "type": "web_search_preview",
                "user_location": {"type": "approximate"},
                "search_context_size": "low",
            }
        ],
        temperature=1,
        max_output_tokens=4096,
        top_p=1,
        store=True,
    )

    return response.output[1].content[0].text