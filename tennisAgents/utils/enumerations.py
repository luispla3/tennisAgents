class RESPONSES:
    aggressive = "current_aggressive_response"
    neutral = "current_neutral_response"
    safe = "current_safe_response"
    expected = "current_expected_response"

class SPEAKERS:
    aggressive = "aggressive"
    neutral = "neutral"
    safe = "safe"
    expected = "expected"
    judge = "judge"

class HISTORYS:
    history = "history"
    aggressive_history = "aggressive_history"
    neutral_history = "neutral_history"
    expected_history = "expected_history"
    safe_history = "safe_history"

class REPORTS:
    weather_report = "weather_report"
    odds_report = "odds_report"
    sentiment_report = "sentiment_report"
    news_report = "news_report"
    players_report = "players_report"
    tournament_report = "tournament_report"
    risk_analysis_report = "risk_analysis_report"
    match_live_report = "match_live_report"

class ANALYSTS:
    aggressive = "Aggressive Analyst"
    neutral = "Neutral Analyst"
    safe = "Safe Analyst"
    expected = "Expected Analyst"
    judge = "Risk Judge"

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
    surface = "surface"
    location = "location"
    wallet_balance = "wallet_balance"

    messages = "messages"

    risk_debate_state = "risk_debate_state"

    final_bet_decision = "final_bet_decision"
    
    count = "count"
    latest_speaker = "latest_speaker"
    judge_decision = "judge_decision"