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
from tennisAgents.dataflows import interface
from tennisAgents.default_config import DEFAULT_CONFIG
from tennisAgents.utils.enumerations import STATE

from langchain_core.messages import HumanMessage


def create_msg_delete():
    def delete_messages(state):
        """Clear messages and add placeholder for Anthropic compatibility"""
        messages = state[STATE.messages]
        
        # Remove all messages
        removal_operations = [RemoveMessage(id=m.id) for m in messages]
        
        # Add a minimal placeholder message
        placeholder = HumanMessage(content="Continue")

        return {STATE.messages: removal_operations + [placeholder]}

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
    def get_news(
        query: Annotated[str, "Consulta para buscar en Google News noticias relevantes de tenis"],
        curr_date: Annotated[str, "Fecha en formato yyyy-mm-dd"],
    ) -> str:
        """Obtiene noticias de Google News sobre tenis."""
        return interface.get_news(query, curr_date)

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
        tournament_key: Annotated[str, "Clave del torneo de The Odds API (ej: 'tennis_atp_canadian_open', 'tennis_wta_us_open')"]
    ) -> str:
        """Obtiene las cuotas de apuestas para un torneo específico usando su clave de API."""
        return interface.get_tennis_odds(tournament_key)

    @tool
    def get_mock_odds_data(
        player1: Annotated[str, "Nombre del jugador 1"],
        player2: Annotated[str, "Nombre del jugador 2"],
    ) -> str:
        """Devuelve cuotas simuladas para pruebas."""
        return interface.get_mock_odds_data(player1, player2)

    # PLAYERS ANALYST TOOLS

    @tool
    def get_atp_rankings() -> str:
        """Obtiene el ranking ATP actual con los IDs de los jugadores. Usa esta herramienta primero para obtener los IDs necesarios para get_recent_matches."""
        return interface.get_atp_rankings()


    @tool
    def get_recent_matches(
        player_id: Annotated[int, "ID del jugador (obtener desde get_atp_rankings)"],
        opponent_id: Annotated[int, "ID del oponente (obtener desde get_atp_rankings)"],
        num_matches: Annotated[int, "Número de partidos recientes"] = 30,
    ) -> str:
        """Obtiene los últimos partidos jugados entre dos jugadores específicos. IMPORTANTE: Primero usa get_atp_rankings para obtener los IDs de los jugadores, luego usa esos IDs aquí."""
        return interface.get_recent_matches(player_id, opponent_id, num_matches)

    @tool
    def get_surface_winrate(
        player_id: Annotated[int, "Id del jugador"],
        surface: Annotated[str, "Superficie (clay, hard, grass)"],
    ) -> str:
        """Obtiene el winrate del jugador en una superficie dada."""
        return interface.get_surface_winrate(player_id, surface)

    @tool
    def get_head_to_head(
        player_id: Annotated[int, "ID del jugador (obtener desde get_atp_rankings)"],
        opponent_id: Annotated[int, "ID del oponente (obtener desde get_atp_rankings)"],
    ) -> str:
        """Obtiene las estadisticas H2H entre dos jugadores."""
        return interface.get_head_to_head(player_id, opponent_id)

    @tool
    def get_injury_reports() -> str:
        """Obtiene reportes de lesiones de todos los jugadores"""
        return interface.get_injury_reports()

    # SOCIAL MEDIA ANALYST TOOLS

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
        return interface.get_mock_tournament_data(tournament, year=2025 )

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