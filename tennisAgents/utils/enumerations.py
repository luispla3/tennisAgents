from enum import Enum


class AnalystType(str, Enum):
    news = "news"
    players = "players"
    tournament = "tournament"
    weather = "weather"


class REPORTS:
    weather_report = "weather_report"
    sentiment_report = "sentiment_report"
    news_report = "news_report"
    players_report = "players_report"
    tournament_report = "tournament_report"


class ANALYST_NODES:
    news = "news"
    players = "players"
    tournament = "tournament"
    weather = "weather"


class STATE:
    match_date = "match_date"
    player_of_interest = "player_of_interest"
    opponent = "opponent"
    tournament = "tournament"
    tournament_context = "tournament_context"
    wallet_balance = "wallet_balance"
    messages = "messages"
    final_bet_decision = "final_bet_decision"
