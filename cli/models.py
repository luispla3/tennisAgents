from enum import Enum

class AnalystType(str, Enum):
    news = "news"
    odds = "odds"
    players = "players"
    social = "social"
    tournament = "tournament"
    weather = "weather"