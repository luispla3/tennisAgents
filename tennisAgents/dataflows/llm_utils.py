import os

from openai import OpenAI

from tennisAgents.dataflows.config import get_config


def get_llm_client() -> OpenAI:
    """Cliente OpenAI compatible con OpenAI, OpenRouter y Ollama."""
    config = get_config()
    kwargs = {"base_url": config["backend_url"]}
    provider = config.get("llm_provider", "openai").lower()

    if provider == "openrouter":
        api_key = config.get("openrouter_api_key") or os.getenv("OPENROUTER_API_KEY")
        if api_key:
            kwargs["api_key"] = api_key
            kwargs["default_headers"] = {
                "HTTP-Referer": "https://github.com/tennisAgents",
                "X-Title": "Tennis Agents",
            }

    return OpenAI(**kwargs)
