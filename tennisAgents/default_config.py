import os

from dotenv import load_dotenv

load_dotenv()

DEFAULT_LLM_PROVIDER = (
    os.getenv("TENNISAGENTS_LLM_PROVIDER", "openrouter").strip().lower()
    or "openrouter"
)
DEFAULT_BACKEND_URLS = {
    "openai": "https://api.openai.com/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "ollama": "http://localhost:11434/v1",
    "anthropic": "https://api.anthropic.com/",
    "google": "https://generativelanguage.googleapis.com/v1",
}
DEFAULT_DEEP_THINK_LLM = os.getenv(
    "TENNISAGENTS_DEEP_THINK_LLM",
    "deepseek/deepseek-v4-flash",
)
DEFAULT_QUICK_THINK_LLM = os.getenv(
    "TENNISAGENTS_QUICK_THINK_LLM",
    "deepseek/deepseek-v4-flash",
)


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


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


_DEFAULT_BACKEND_URL = DEFAULT_BACKEND_URLS.get(
    DEFAULT_LLM_PROVIDER,
    DEFAULT_BACKEND_URLS["openrouter"],
)
# Si el proveedor es OpenRouter, nunca se permite caer en api.openai.com
# aunque exista un TENNISAGENTS_LLM_BASE_URL residual.
_CONFIGURED_BACKEND_URL = os.getenv("TENNISAGENTS_LLM_BASE_URL", _DEFAULT_BACKEND_URL)
if DEFAULT_LLM_PROVIDER == "openrouter" and "openrouter.ai" not in (
    _CONFIGURED_BACKEND_URL or ""
):
    _CONFIGURED_BACKEND_URL = DEFAULT_BACKEND_URLS["openrouter"]

DEFAULT_CONFIG = {
    "project_dir": os.path.abspath(os.path.join(os.path.dirname(__file__), ".")),
    "results_dir": os.getenv("TENNISAGENTS_RESULTS_DIR", "./results"),
    "data_dir": "./tennisAgents/data",
    "data_cache_dir": os.path.join(
        os.path.abspath(os.path.join(os.path.dirname(__file__), ".")),
        "dataflows/data_cache",
    ),
    "llm_provider": DEFAULT_LLM_PROVIDER,
    "deep_think_llm": DEFAULT_DEEP_THINK_LLM,
    "quick_think_llm": DEFAULT_QUICK_THINK_LLM,
    "backend_url": _CONFIGURED_BACKEND_URL,
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
    "analysis_retry_delay_sec": max(
        5,
        _env_int("TENNISAGENTS_ANALYSIS_RETRY_DELAY_SEC", 60),
    ),
    "analysis_snapshot_max_age_sec": max(
        60,
        _env_int("TENNISAGENTS_ANALYSIS_SNAPSHOT_MAX_AGE_SEC", 300),
    ),
    "provider_circuit_breaker_sec": max(
        60,
        _env_int("TENNISAGENTS_PROVIDER_CIRCUIT_BREAKER_SEC", 900),
    ),
    "analysis_max_failures_per_snapshot": max(
        1,
        _env_int("TENNISAGENTS_ANALYSIS_MAX_FAILURES_PER_SNAPSHOT", 12),
    ),
    "analyst_report_min_chars": max(
        200,
        _env_int("TENNISAGENTS_ANALYST_REPORT_MIN_CHARS", 1000),
    ),
    "analysts_max_runtime_sec": max(
        60,
        _env_int("TENNISAGENTS_ANALYSTS_MAX_RUNTIME_SEC", 600),
    ),
    "analysts_in_process_retries": max(
        1,
        _env_int("TENNISAGENTS_ANALYSTS_IN_PROCESS_RETRIES", 3),
    ),
    "analysts_retry_sleep_sec": max(
        1,
        _env_int("TENNISAGENTS_ANALYSTS_RETRY_SLEEP_SEC", 5),
    ),
    "minimum_bet_edge": max(
        0.0,
        _env_float("TENNISAGENTS_MINIMUM_BET_EDGE", 0.02),
    ),
    # Tope suave de diversificación (no anti-pérdida agresivo). 1.0 lo desactiva.
    "max_stake_fraction": min(
        1.0,
        max(0.01, _env_float("TENNISAGENTS_MAX_STAKE_FRACTION", 0.20)),
    ),
    "max_total_exposure_fraction": min(
        1.0,
        max(0.05, _env_float("TENNISAGENTS_MAX_TOTAL_EXPOSURE_FRACTION", 0.50)),
    ),
    "minimum_bet_stake": max(
        0.01,
        _env_float("TENNISAGENTS_MINIMUM_BET_STAKE", 1.0),
    ),
    # MATCH_ODDS con cuota corta exige más edge (calibración frágil del LLM).
    "match_odds_short_odds_max": max(
        1.01,
        _env_float("TENNISAGENTS_MATCH_ODDS_SHORT_ODDS_MAX", 1.25),
    ),
    "match_odds_short_min_edge": max(
        0.0,
        _env_float("TENNISAGENTS_MATCH_ODDS_SHORT_MIN_EDGE", 0.05),
    ),
    "void_unresolved_markets_on_finish": _env_bool(
        "TENNISAGENTS_VOID_UNRESOLVED_MARKETS_ON_FINISH",
        True,
    ),
    "void_unresolved_on_indecisive_finish": _env_bool(
        "TENNISAGENTS_VOID_UNRESOLVED_ON_INDECISIVE_FINISH",
        True,
    ),
    "void_open_positions_on_shutdown": _env_bool(
        "TENNISAGENTS_VOID_OPEN_POSITIONS_ON_SHUTDOWN",
        True,
    ),
    "settle_open_positions_on_shutdown": _env_bool(
        "TENNISAGENTS_SETTLE_OPEN_POSITIONS_ON_SHUTDOWN",
        True,
    ),
    "shutdown_drain_sec": max(
        0,
        _env_int("TENNISAGENTS_SHUTDOWN_DRAIN_SEC", 5),
    ),
    "default_match_start_time": os.getenv("TENNISAGENTS_DEFAULT_MATCH_START_TIME", "14:00").strip() or "14:00",
    "audit_log_max_bytes": max(
        1024 * 1024,
        _env_int("TENNISAGENTS_AUDIT_LOG_MAX_BYTES", 100 * 1024 * 1024),
    ),
}
