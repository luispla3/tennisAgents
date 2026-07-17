import os

from dotenv import load_dotenv

load_dotenv()


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


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
    "automated_wallet_balance": _env_float("TENNISAGENTS_AUTOMATED_WALLET_BALANCE", 100.0),
    "llm_timeout_sec": _env_int("TENNISAGENTS_LLM_TIMEOUT_SEC", 180),
    "llm_max_retries": _env_int("TENNISAGENTS_LLM_MAX_RETRIES", 1),
    "automated_analysis_workers": max(
        1,
        _env_int("TENNISAGENTS_AUTOMATED_ANALYSIS_WORKERS", 2),
    ),
    "audit_log_max_bytes": max(
        1024 * 1024,
        _env_int("TENNISAGENTS_AUDIT_LOG_MAX_BYTES", 100 * 1024 * 1024),
    ),
}
