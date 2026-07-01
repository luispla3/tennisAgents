from enum import Enum

class AnalystType(str, Enum):
    news = "news"
    players = "players"
    social = "social"
    tournament = "tournament"
    weather = "weather"
