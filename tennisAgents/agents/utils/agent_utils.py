from langchain_core.messages import HumanMessage, RemoveMessage
from typing import Annotated
from langchain_core.tools import tool
from tennisAgents.dataflows import interface
from tennisAgents.dataflows.config import get_config
from tennisAgents.default_config import DEFAULT_CONFIG
from tennisAgents.utils.enumerations import STATE

import json
from datetime import datetime


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


def _record_tool_output(tool_name: str, args: dict, output: str) -> str:
    """Guarda salida cruda de tools para auditoría de predicciones web."""
    try:
        log_path = get_config().get("tool_outputs_log")
        if log_path:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(
                    json.dumps(
                        {
                            "timestamp": datetime.now().isoformat(),
                            "tool": tool_name,
                            "args": args,
                            "output": output,
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
    except Exception:
        pass
    return output

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
        query: Annotated[str, "Consulta para buscar noticias relevantes de tenis"],
        curr_date: Annotated[str, "Fecha en formato yyyy-mm-dd"],
    ) -> str:
        """Obtiene noticias de tenis mediante búsqueda web."""
        result = interface.get_news(query, curr_date)
        return _record_tool_output("get_news", {"query": query, "curr_date": curr_date}, result)


    # PLAYERS ANALYST TOOLS


    @tool
    def get_atp_rankings(
        player1_name: Annotated[str, "Nombre del primer jugador"],
        player2_name: Annotated[str, "Nombre del segundo jugador"],
    ) -> str:
        """Busca en la pagina web de la ATP el ranking ATP actual y el mejor ranking de su carrera para ambos jugadores."""
        result = interface.get_atp_rankings(player1_name, player2_name)
        return _record_tool_output(
            "get_atp_rankings",
            {"player1_name": player1_name, "player2_name": player2_name},
            result,
        )

    @tool
    def get_recent_matches(
       player_name: Annotated[str, "Nombre del jugador"],
       opponent_name: Annotated[str, "Nombre del oponente"],
       num_matches: Annotated[int, "Número de partidos recientes"] = 30,
    ) -> str:
        """Obtiene los últimos partidos jugados entre dos jugadores específicos usando sus nombres."""
        result = interface.get_recent_matches(player_name, opponent_name, num_matches)
        return _record_tool_output(
            "get_recent_matches",
            {"player_name": player_name, "opponent_name": opponent_name, "num_matches": num_matches},
            result,
        )

    @tool
    def get_surface_winrate(
        player_name: Annotated[str, "Nombre del jugador"],
        surface: Annotated[str, "Superficie (clay, hard, grass)"],
    ) -> str:
        """Obtiene el winrate del jugador en una superficie dada usando su nombre."""
        result = interface.get_surface_winrate(player_name, surface)
        return _record_tool_output(
            "get_surface_winrate",
            {"player_name": player_name, "surface": surface},
            result,
        )

    @tool
    def get_head_to_head(
        player_name: Annotated[str, "Nombre del jugador"],
        opponent_name: Annotated[str, "Nombre del oponente"],
    ) -> str:
        """Obtiene las estadisticas H2H entre dos jugadores usando sus nombres."""
        result = interface.get_head_to_head(player_name, opponent_name)
        return _record_tool_output(
            "get_head_to_head",
            {"player_name": player_name, "opponent_name": opponent_name},
            result,
        )

    @tool
    def get_injury_reports(
        player1_name: Annotated[str, "Nombre del jugador"],
        player2_name: Annotated[str, "Nombre del oponente"],
    ) -> str:
        """Obtiene el historial de lesiones de ambos jugadores desde Flashscore."""
        result = interface.get_injury_reports(player1_name, player2_name)
        return _record_tool_output(
            "get_injury_reports",
            {"player1_name": player1_name, "player2_name": player2_name},
            result,
        )

    @tool
    def get_match_live_data(
        player_a: Annotated[str, "Nombre del primer jugador"],
        player_b: Annotated[str, "Nombre del segundo jugador"],
        tournament: Annotated[str, "Nombre del torneo"],
    ) -> str:
        """Obtiene el marcador en vivo y estadísticas del partido desde Flashscore."""
        result = interface.get_match_live_data(player_a, player_b, tournament)
        return _record_tool_output(
            "get_match_live_data",
            {"player_a": player_a, "player_b": player_b, "tournament": tournament},
            result,
        )


    # TOURNAMENT ANALYST TOOLS


    @tool
    def get_tournament_info(
        tournament: Annotated[str, "Nombre del torneo"],
        category: Annotated[str, "Categoría del torneo: atpgs: Atp tournaments + grand Slams, atp: Atp circuit, gs: grand slams, 1000: Masters 1000, ch: Challenger Circuit"],
        date: Annotated[str, "Fecha del torneo en formato yyyy-mm-dd"],
    ) -> str:
        """Obtiene información y estadísticas del torneo."""
        result = interface.get_tournament_data(tournament, category, date)
        return _record_tool_output(
            "get_tournament_info",
            {"tournament": tournament, "category": category, "date": date},
            result,
        )


    # WEATHER ANALYST TOOLS

    
    @tool
    def get_weather_forecast(
        tournament: Annotated[str, "Nombre del torneo"],
        fecha_hora: Annotated[str, "Fecha y hora del partido yyyy-mm-dd hh:mm"],
        location: Annotated[str, "Ubicación del torneo (ciudad, país, etc.)"],
    ) -> str:
        """Obtiene la previsión meteorológica para el partido usando búsqueda web + LLM."""
        result = interface.get_weather_forecast(tournament, fecha_hora, location)
        return _record_tool_output(
            "get_weather_forecast",
            {"tournament": tournament, "fecha_hora": fecha_hora, "location": location},
            result,
        )
