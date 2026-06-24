from enum import Enum


class AnalystType(str, Enum):
    news = "news"
    odds = "odds"
    players = "players"
    social = "social"
    tournament = "tournament"
    weather = "weather"
    match_live = "match_live"


class REPORTS:
    weather_report = "weather_report"
    odds_report = "odds_report"
    sentiment_report = "sentiment_report"
    news_report = "news_report"
    players_report = "players_report"
    tournament_report = "tournament_report"
    match_live_report = "match_live_report"


class ANALYST_NODES:
    news = "news"
    odds = "odds"
    players = "players"
    social = "social_media"
    tournament = "tournament"
    weather = "weather"
    match_live = "match_live"


class STATE:
    match_date = "match_date"
    player_of_interest = "player_of_interest"
    opponent = "opponent"
    tournament = "tournament"
    wallet_balance = "wallet_balance"
    messages = "messages"
    final_bet_decision = "final_bet_decision"
