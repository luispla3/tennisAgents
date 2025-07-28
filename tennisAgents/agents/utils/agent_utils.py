from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage, AIMessage
from typing import List
from typing import Annotated
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import RemoveMessage
from langchain_core.tools import tool
from datetime import date, timedelta, datetime
import functools
import pandas as pd
import os
from dateutil.relativedelta import relativedelta
from langchain_openai import ChatOpenAI
import tradingagents.dataflows.interface as interface
from tradingagents.default_config import DEFAULT_CONFIG
from langchain_core.messages import HumanMessage


def create_msg_delete():
    def delete_messages(state):
        """Clear messages and add placeholder for Anthropic compatibility"""
        messages = state["messages"]
        
        # Remove all messages
        removal_operations = [RemoveMessage(id=m.id) for m in messages]
        
        # Add a minimal placeholder message
        placeholder = HumanMessage(content="Continue")
        
        return {"messages": removal_operations + [placeholder]}
    
    return delete_messages

class Toolkit:
    _config = DEFAULT_CONFIG.copy()

    @classmethod
    def update_config(cls, config):
        """Update the class-level configuration."""
        cls._config.update(config)

    @property
    def config(self):
        """Access the configuration."""
        return self._config

    def __init__(self, config=None):
        if config:
            self.update_config(config)
            
    # NEWS ANALYST TOOLS
    @tool
    def get_tennis_news_openai(
        query: Annotated[str, "Consulta de noticias de tenis"],
        curr_date: Annotated[str, "Fecha en formato yyyy-mm-dd"],
    ) -> str:
        """Obtiene las últimas noticias de tenis usando OpenAI."""
        return interface.get_news_articles(query, curr_date)

    @tool
    def get_google_news(
        query: Annotated[str, "Consulta para buscar en Google News"],
        curr_date: Annotated[str, "Fecha en formato yyyy-mm-dd"],
    ) -> str:
        """Obtiene noticias de Google News sobre tenis."""
        return interface.get_google_news(query, curr_date)

    @tool
    def get_atp_news(
        curr_date: Annotated[str, "Fecha en formato yyyy-mm-dd"],
    ) -> str:
        """Obtiene noticias recientes de la web oficial ATP."""
        return interface.get_atp_news(curr_date)

    @tool
    def get_tennisworld_news(
        curr_date: Annotated[str, "Fecha en formato yyyy-mm-dd"],
    ) -> str:
        """Obtiene noticias recientes de TennisWorld."""
        return interface.get_tennisworld_news(curr_date)

    # ODDS ANALYST TOOLS
    @tool
    def get_odds_data(
        player1: Annotated[str, "Nombre del jugador 1"],
        player2: Annotated[str, "Nombre del jugador 2"],
        match_date: Annotated[str, "Fecha del partido yyyy-mm-dd"],
    ) -> str:
        """Obtiene cuotas reales para el partido."""
        return interface.get_tennis_odds(player1, player2, match_date)

    @tool
    def get_mock_odds_data(
        player1: Annotated[str, "Nombre del jugador 1"],
        player2: Annotated[str, "Nombre del jugador 2"],
    ) -> str:
        """Devuelve cuotas simuladas para pruebas."""
        return interface.get_mock_odds_data(player1, player2)

    # PLAYERS ANALYST TOOLS
    @tool
    def get_player_profile_openai(
        player_name: Annotated[str, "Nombre del jugador"],
    ) -> str:
        """Obtiene el perfil del jugador usando OpenAI."""
        return interface.get_player_stats_tennisabstract(player_name)

    @tool
    def get_atp_rankings() -> str:
        """Obtiene el ranking ATP actual."""
        return interface.get_atp_rankings()

    @tool
    def get_recent_matches(
        player_name: Annotated[str, "Nombre del jugador"],
        num_matches: Annotated[int, "Número de partidos recientes"] = 5,
    ) -> str:
        """Obtiene los últimos partidos jugados por el jugador."""
        return interface.get_recent_matches(player_name, num_matches)

    @tool
    def get_surface_winrate(
        player_name: Annotated[str, "Nombre del jugador"],
        surface: Annotated[str, "Superficie (clay, hard, grass)"],
    ) -> str:
        """Obtiene el winrate del jugador en una superficie dada."""
        return interface.get_surface_winrate(player_name, surface)

    @tool
    def get_head_to_head(
        player1: Annotated[str, "Nombre del jugador 1"],
        player2: Annotated[str, "Nombre del jugador 2"],
    ) -> str:
        """Obtiene el historial H2H entre dos jugadores."""
        return interface.get_head_to_head(player1, player2)

    @tool
    def get_injury_reports(
        player_name: Annotated[str, "Nombre del jugador"],
    ) -> str:
        """Obtiene reportes de lesiones del jugador."""
        return interface.get_injury_reports(player_name)

    # SOCIAL MEDIA ANALYST TOOLS
    @tool
    def get_social_sentiment_openai(
        player_name: Annotated[str, "Nombre del jugador"],
    ) -> str:
        """Analiza sentimiento social usando OpenAI."""
        return interface.get_social_sentiment_openai(player_name)

    @tool
    def get_twitter_sentiment(
        player_name: Annotated[str, "Nombre del jugador"],
    ) -> str:
        """Analiza sentimiento en Twitter sobre el jugador."""
        return interface.get_twitter_posts(player_name)

    @tool
    def get_tennis_forum_sentiment(
        player_name: Annotated[str, "Nombre del jugador"],
    ) -> str:
        """Analiza sentimiento en foros de tenis."""
        return interface.get_tennis_forum_sentiment(player_name)

    @tool
    def get_reddit_sentiment(
        player_name: Annotated[str, "Nombre del jugador"],
    ) -> str:
        """Analiza sentimiento en Reddit sobre el jugador."""
        return interface.get_reddit_posts("tennis", player_name)

    # TOURNAMENT ANALYST TOOLS
    @tool
    def get_tournament_info(
        tournament: Annotated[str, "Nombre del torneo"],
        year: Annotated[int, "Año del torneo"],
    ) -> str:
        """Obtiene información y estadísticas del torneo."""
        return interface.get_tournaments(year)

    @tool
    def get_mock_tournament_data(
        tournament: Annotated[str, "Nombre del torneo"],
    ) -> str:
        """Devuelve datos simulados de torneo para pruebas."""
        return interface.get_mock_tournament_data(tournament)

    # WEATHER ANALYST TOOLS
    @tool
    def get_weather_forecast(
        latitude: Annotated[float, "Latitud"],
        longitude: Annotated[float, "Longitud"],
        match_date: Annotated[str, "Fecha del partido yyyy-mm-dd"],
    ) -> str:
        """Obtiene la previsión meteorológica para el partido."""
        return interface.get_weather_forecast(latitude, longitude, start_date=match_date, end_date=match_date)

    @tool
    def get_mock_weather_data(
        location: Annotated[str, "Ubicación textual o ciudad"],
    ) -> str:
        """Devuelve datos meteorológicos simulados para pruebas."""
        return interface.get_mock_weather_data(location)