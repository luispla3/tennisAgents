from langchain_core.messages import HumanMessage, RemoveMessage
from typing import Annotated
from langchain_core.tools import tool
from tennisAgents.dataflows import interface
from tennisAgents.default_config import DEFAULT_CONFIG
from tennisAgents.utils.enumerations import STATE


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


    # ODDS ANALYST TOOLS

    
    @tool
    def get_odds_data(
        player_a: Annotated[str, "Nombre del primer jugador"],
        player_b: Annotated[str, "Nombre del segundo jugador"],
        tournament: Annotated[str, "Nombre del torneo"]
    ) -> str:
        """Obtiene las cuotas de apuestas de Betfair para un partido específico usando OpenAI."""
        return interface.get_tennis_odds(player_a, player_b, tournament)

    @tool
    def mock_tennis_odds(
        player_a: Annotated[str, "Nombre del primer jugador"],
        player_b: Annotated[str, "Nombre del segundo jugador"],
        tournament: Annotated[str, "Nombre del torneo"]
    ) -> str:
        """Genera cuotas ficticias realistas para un partido específico."""
        return interface.mock_tennis_odds(player_a, player_b, tournament)


    # PLAYERS ANALYST TOOLS


    @tool
    def get_atp_rankings() -> str:
        """Obtiene el ranking ATP actual. Usa esta herramienta para obtener información sobre el ranking de los jugadores."""
        return interface.get_atp_rankings()

    @tool
    def get_recent_matches(
       player_name: Annotated[str, "Nombre del jugador"],
       opponent_name: Annotated[str, "Nombre del oponente"],
       num_matches: Annotated[int, "Número de partidos recientes"] = 30,
    ) -> str:
        """Obtiene los últimos partidos jugados entre dos jugadores específicos usando sus nombres."""
        return interface.get_recent_matches(player_name, opponent_name, num_matches)

    @tool
    def get_surface_winrate(
        player_name: Annotated[str, "Nombre del jugador"],
        surface: Annotated[str, "Superficie (clay, hard, grass)"],
    ) -> str:
        """Obtiene el winrate del jugador en una superficie dada usando su nombre."""
        return interface.get_surface_winrate(player_name, surface)

    @tool
    def get_head_to_head(
        player_name: Annotated[str, "Nombre del jugador"],
        opponent_name: Annotated[str, "Nombre del oponente"],
    ) -> str:
        """Obtiene las estadisticas H2H entre dos jugadores usando sus nombres."""
        return interface.get_head_to_head(player_name, opponent_name)

    @tool
    def get_injury_reports() -> str:
        """Obtiene reportes de lesiones para un jugador específico"""
        return interface.get_injury_reports()


    # SOCIAL MEDIA ANALYST TOOLS


    @tool
    def get_sentiment(
        player_name: Annotated[str, "Nombre del jugador"],
    ) -> str:
        """Analiza sentimiento en Twitter sobre el jugador."""
        return interface.get_sentiment(player_name)
        

    # TOURNAMENT ANALYST TOOLS


    @tool
    def get_tournament_info(
        tournament: Annotated[str, "Nombre del torneo"],
        category: Annotated[str, "Categoría del torneo: atpgs: Atp tournaments + grand Slams, atp: Atp circuit, gs: grand slams, 1000: Masters 1000, ch: Challenger Circuit"],
        date: Annotated[str, "Fecha del torneo en formato yyyy-mm-dd"],
    ) -> str:
        """Obtiene información y estadísticas del torneo."""
        return interface.get_tournament_data(tournament, category, date)


    # WEATHER ANALYST TOOLS

    
    @tool
    def get_weather_forecast(
        tournament: Annotated[str, "Nombre del torneo"],
        fecha_hora: Annotated[str, "Fecha y hora del partido yyyy-mm-dd hh:mm"],
        location: Annotated[str, "Ubicación del torneo (ciudad, país, etc.)"],
    ) -> str:
        """Obtiene la previsión meteorológica para el partido usando OpenAI con búsqueda web."""
        return interface.get_weather_forecast(tournament, fecha_hora, location)