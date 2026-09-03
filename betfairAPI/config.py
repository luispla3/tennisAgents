import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

APP_KEY = "owXqg8AXJZSI6Z4R"
LOGIN_URL = "https://identitysso.betfair.es/api/login"
KEEP_ALIVE_URL = "https://identitysso.betfair.es/api/keepAlive"
BETTING_URL = "https://api.betfair.com/exchange/betting/rest/v1.0"
ACCOUNT_URL = "https://api.betfair.com/exchange/account/rest/v1.0"

SESSION_FILE = BASE_DIR / ".session_token"
ENV_FILE = BASE_DIR / ".env"

TENNIS_EVENT_TYPE_ID = "2"
MAX_MARKET_BOOK_BATCH = 40


def load_env_file():
    if not ENV_FILE.exists():
        return
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())
