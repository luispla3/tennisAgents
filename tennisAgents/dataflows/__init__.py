# tennis_agents/dataflows/__init__.py

from .tennisdata_utils import get_data_in_range
from .googlenews_utils import getNewsData
from .yfin_utils import YFinanceUtils
from .reddit_utils import fetch_top_from_category
from .matchstats_utils import MatchStatsUtils

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
