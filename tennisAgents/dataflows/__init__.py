# tennisAgents/dataflows/__init__.py

# TODO: Import necessary modules and functions for dataflows

from .interface import (
    # News and sentiment functions
    get_google_news,
    get_reddit_global_news,
    get_reddit_player_news,
    
    # Match statistics functions
    get_player_match_history,
    get_head_to_head_stats,
    
    # Technical/Statistical indicators
    get_player_performance_indicators,
    get_form_trend_indicator,
    
    # Market data functions (odds)
    get_betting_odds_window,
    get_betting_odds_data,
)

__all__ = [
    # News and sentiment functions
    "get_google_news",
    "get_reddit_global_news",
    "get_reddit_player_news",
    
    # Match statistics functions
    "get_player_match_history",
    "get_head_to_head_stats",
    
    # Technical/Statistical indicators
    "get_player_performance_indicators",
    "get_form_trend_indicator",
    
    # Market data functions (odds)
    "get_betting_odds_window",
    "get_betting_odds_data",
]
