import os
from typing import Literal, Tuple

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from openai import OpenAI

from tennisAgents.dataflows.config import get_config

ModelKey = Literal["quick_think_llm", "deep_think_llm"]


def get_llm_client() -> OpenAI:
    """Cliente OpenAI-compatible para embeddings y APIs legacy."""
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


def get_chat_llm(model_key: ModelKey = "quick_think_llm", **overrides) -> BaseChatModel:
    """Devuelve un LLM LangChain según llm_provider en la configuración."""
    config = get_config()
    provider = config.get("llm_provider", "openai").lower()
    model = config[model_key]

    if provider in ("openai", "ollama", "openrouter"):
        kwargs = {"model": model, "base_url": config["backend_url"], **overrides}
        if provider == "openrouter":
            api_key = config.get("openrouter_api_key") or os.getenv("OPENROUTER_API_KEY")
            if api_key:
                kwargs["api_key"] = api_key
                kwargs["default_headers"] = {
                    "HTTP-Referer": "https://github.com/tennisAgents",
                    "X-Title": "Tennis Agents",
                }
        return ChatOpenAI(**kwargs)

    if provider == "anthropic":
        return ChatAnthropic(model=model, base_url=config["backend_url"], **overrides)

    if provider == "google":
        return ChatGoogleGenerativeAI(model=model, **overrides)

    raise ValueError(f"Proveedor LLM no soportado: {provider}")


def get_local_analyst_llm(**overrides) -> Tuple[BaseChatModel, str]:
    """Devuelve el LLM local/configurado para analistas y una etiqueta descriptiva."""
    config = get_config()
    local_base_url = config.get("local_base_url", "http://localhost:11434/v1")
    local_model = config.get("local_model_name", "qwen2.5:3b")
    is_local = "localhost" in local_base_url or "127.0.0.1" in local_base_url

    if is_local:
        base_url_cleaned = (
            local_base_url.replace("/v1", "")
            if local_base_url.endswith("/v1")
            else local_base_url
        )
        llm = ChatOllama(
            model=local_model,
            base_url=base_url_cleaned,
            temperature=0.1,
            num_ctx=16384,
            num_predict=4096,
            reasoning=False,
            **overrides,
        )
        return llm, "OLLAMA LOCAL"

    local_api_key = config.get("local_api_key") or os.getenv("OPENROUTER_API_KEY")
    if not local_api_key:
        raise ValueError("OPENROUTER_API_KEY no configurada")

    llm = ChatOpenAI(
        model=local_model,
        base_url=local_base_url,
        api_key=local_api_key,
        default_headers={
            "HTTP-Referer": "https://github.com/tennisAgents",
            "X-Title": "Tennis Agents",
        },
        temperature=0.7,
        **overrides,
    )
    return llm, "OPENROUTER"


def _message_content(message) -> str:
    """Extrae texto plano de la respuesta del LLM."""
    content = getattr(message, "content", message)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                parts.append(block.get("text", ""))
            else:
                parts.append(str(block))
        return "".join(parts)
    return str(content)


def invoke_chat_llm(
    system_prompt: str,
    user_content: str,
    *,
    model_key: ModelKey = "quick_think_llm",
    temperature: float = 1,
    max_tokens: int = 4096,
) -> str:
    """Invoca el LLM configurado con mensajes system/user y devuelve el texto."""
    llm = get_chat_llm(
        model_key=model_key,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    response = llm.invoke(
        [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_content),
        ]
    )
    return _message_content(response) or ""


def invoke_local_analyst_llm(system_prompt: str, user_content: str) -> Tuple[str, str]:
    """Invoca el LLM local de analistas. Devuelve (texto, etiqueta_fuente)."""
    llm, label = get_local_analyst_llm()
    response = llm.invoke(
        [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_content),
        ]
    )
    return _message_content(response) or "", label
