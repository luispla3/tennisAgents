from enum import Enum
from typing import List, Optional, Dict
from pydantic import BaseModel

class AnalystType(str, Enum):
    news = "news"
    odds = "odds"
    players = "players"
    social = "social"
    tournament = "tournament"
    weather = "weather"
    aggressive = "aggressive"
    safe = "safe"
    neutral = "neutral"
    expected = "expected"
    judge = "judge"