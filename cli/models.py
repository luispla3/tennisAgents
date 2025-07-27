from enum import Enum
from typing import List, Optional, Dict
from pydantic import BaseModel

class AnalystType(str, Enum):
    NEWS = "news"
    ODDS = "odds"
    PLAYERS = "players"
    SOCIAL = "social_media"
    TOURNAMENT = "tournament"
    WEATHER = "weather"
    AGGRESSIVE = "aggressive"
    SAFE = "safe"
    NEUTRAL = "neutral"
    EXPECTED = "expected"
    JUDGE = "judge"
