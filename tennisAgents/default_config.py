import os

DEFAULT_CONFIG = {
    "project_dir": os.path.abspath(os.path.join(os.path.dirname(__file__), ".")),
    "results_dir": os.getenv("TENNISAGENTS_RESULTS_DIR", "./results"),
    "data_dir": "./tennisAgents/data", 
    "data_cache_dir": os.path.join(
        os.path.abspath(os.path.join(os.path.dirname(__file__), ".")),
        "dataflows/data_cache",
    ),
    # LLM settings
    "llm_provider": "openai",
    "deep_think_llm": "o4-mini",
    "quick_think_llm": "gpt-4o-mini",
    "backend_url": "https://api.openai.com/v1",
    # OpenRouter settings for additional risk managers
    "openrouter_api_key": os.getenv("OPENROUTER_API_KEY", None),
    "openrouter_base_url": "https://openrouter.ai/api/v1",
    # Fixed models for additional risk managers (via OpenRouter)
    "additional_risk_managers": [
        {"name": "GPT-5.1", "model": "openai/gpt-5.1"},
        {"name": "Gemini-3-Pro", "model": "google/gemini-3-pro"},
        {"name": "Grok-4", "model": "x-ai/grok-4"},
    ],
    # Debate and discussion settings
    "max_debate_rounds": 1,
    "max_risk_discuss_rounds": 1,
    "max_recur_limit": 100,
    # Tool settings
    "online_tools": True,
    
    # RAG settings
    "enable_rag": False,  # Set to True to enable RAG functionality
    
    # Sportradar API settings
    "sportradar_base_url": "https://api.sportradar.com/tennis/trial/v3/en",
    "sportradar_api_timeout": 30,  # segundos
    "sportradar_access_level": "trial",  # nivel de acceso (trial, production)
    "sportradar_language": "en",  # idioma por defecto
    "sportradar_request_delay": 1.0,  # delay entre solicitudes (segundos) - TTL de 1 segundo
    "sportradar_max_retries": 3,  # número máximo de reintentos en caso de error
    "sportradar_retry_delay": 5  # delay inicial para reintentos (segundos)
}