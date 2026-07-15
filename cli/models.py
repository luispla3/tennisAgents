from enum import Enum

class AnalystType(str, Enum):
    news = "news"
    players = "players"
    tournament = "tournament"
    weather = "weather"
