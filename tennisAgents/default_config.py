import os

from dotenv import load_dotenv

load_dotenv()

DEFAULT_CONFIG = {
    "project_dir": os.path.abspath(os.path.join(os.path.dirname(__file__), ".")),
    "results_dir": os.getenv("TENNISAGENTS_RESULTS_DIR", "./results"),
    "data_dir": "./tennisAgents/data",
    "data_cache_dir": os.path.join(
        os.path.abspath(os.path.join(os.path.dirname(__file__), ".")),
        "dataflows/data_cache",
    ),
    "llm_provider": "openai",
    "deep_think_llm": "o4-mini",
    "quick_think_llm": "gpt-4o-mini",
    "backend_url": "https://api.openai.com/v1",
    "openrouter_api_key": os.getenv("OPENROUTER_API_KEY", None),
    "openrouter_base_url": "https://openrouter.ai/api/v1",
    "max_recur_limit": 100,
    "online_tools": True,
    "use_local_analysts": False,
    "local_model_name": "qwen3.5:2b",
    "local_base_url": "http://localhost:11434/v1",
    "local_api_key": "ollama",
    "enable_rag": False,
    "flashscore_locale": "es",
    "betfair_sport": "tennis",
}
