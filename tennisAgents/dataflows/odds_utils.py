from openai import OpenAI
from tennisAgents.dataflows.config import get_config
from datetime import datetime
import json
import random

def fetch_tennis_odds(player_a: str, player_b: str, tournament: str) -> dict:
    """
    Consulta cuotas de apuestas de Betfair para un partido específico usando OpenAI.
    
    Args:
        player_a (str): Nombre del primer jugador
        player_b (str): Nombre del segundo jugador
        tournament (str): Nombre del torneo
    
    Returns:
        dict: Cuotas estructuradas para el partido consultado
    """
    try:
        config = get_config()
        client = OpenAI(base_url=config["backend_url"])

        # Crear el prompt para OpenAI
        prompt_text = f"""Obtén las cuotas de apuestas de Betfair (o del mejor comparador disponible que muestre las cuotas de Betfair) para el partido de tenis {player_a} vs {player_b} en {tournament}.

Necesito los siguientes mercados en formato estructurado (JSON):

1. Match Winner:
   Apuesta sobre quién gana el partido completo (ejemplo: "{player_a} gana el partido", "{player_b} gana el partido").

2. Set Betting:
   Cuotas para resultados en sets (ejemplo: 2-0 gana {player_a}, 2-1 gana {player_b}, 3-1 gana {player_a}, etc.).

3. Set Score:
   Cuotas para marcadores específicos de un determinadoset para un jugador (ejemplo: "{player_a} set 1 gana 6-4").

4. Both Win Set:
   Cuota de que ambos jugadores ganan al menos un set.

5. Player Set Win:
   Cuota de que cada jugador gana al menos un set (ejemplo: "{player_a} gana 1 set", "{player_b} gana 1 set").

6. Combined Bet:
   Combinaciones de quién gana el set y cuál es el resultado en juegos (ejemplo: "{player_a} gana el set 1 por 6-4").

IMPORTANTE:  
- Es posible que alguno de estos mercados no esté disponible para este partido en Betfair.  
- En ese caso, debes indicarlo explícitamente en el JSON con el valor "No disponible" en lugar de inventar datos.  

Devuelve únicamente un objeto JSON con esta estructura:

{{
  "Match Winner": {{ "{player_a}": cuota, "{player_b}": cuota }} o "No disponible",
  "Set Betting": {{ "2-0 gana {player_a}": cuota, "2-1 gana {player_b}": cuota, "3-1 gana {player_a}": cuota, ... }} o "No disponible",
  "Set Score": {{ "{player_a} set 1 gana 6-4": cuota, "{player_b} set 1 gana 6-4": cuota, ... }} o "No disponible",
  "Both Win Set": {{ "{player_a} y {player_b} ganan al menos un set": cuota }} o "No disponible",
  "Player Set Win": {{ "{player_a} gana 1 set": cuota, "{player_b} gana 1 set": cuota }} o "No disponible",
  "Combined Bet": {{ "{player_a} gana el set 1 por 6-4": cuota, "{player_b} gana el set 1 por 6-4": cuota, ... }} o "No disponible"
}}

IMPORTANTE: Responde SOLO con el JSON, sin texto adicional antes o después."""

        response = client.responses.create(
            model=config["quick_think_llm"],
            input=[
            {
                "role": "system",
                "content": [
                {
                    "type": "input_text",
                    "text": "Eres un experto en apuestas deportivas especializado en tenis. Tu tarea es obtener cuotas reales de Betfair para partidos de tenis y devolverlas en formato JSON estructurado. NO inventes datos - si algo no está disponible, indícalo claramente.",
                }
                ],
            },
            {
                "role": "user",
                "content": [
                {
                    "type": "input_text",
                    "text": prompt_text,
                }
                ],
            }
            ],
            text={"format": {"type": "text"}},
            reasoning={},
            tools=[
            {
                "type": "web_search_preview",
                "user_location": {"type": "approximate"},
                "search_context_size": "medium",
            }
            ],
            temperature=0.1,
            max_output_tokens=2000,
            top_p=1,
            store=True,
        )

        # Extraer la respuesta del modelo
        response_text = response.output[1].content[0].text
        
        # Intentar parsear el JSON de la respuesta
        try:
            # Limpiar la respuesta para extraer solo el JSON
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                if json_end != -1:
                    response_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                if json_end != -1:
                    response_text = response_text[json_start:json_end].strip()
            
            odds_data = json.loads(response_text)
            
            # Agregar metadatos
            odds_data["success"] = True
            odds_data["fetched_at"] = datetime.now().isoformat()
            odds_data["player_a"] = player_a
            odds_data["player_b"] = player_b
            odds_data["tournament"] = tournament
            
            return odds_data
            
        except json.JSONDecodeError as e:
            return {
                "error": f"Error al parsear JSON de OpenAI: {str(e)}",
                "raw_response": response_text,
                "player_a": player_a,
                "player_b": player_b,
                "tournament": tournament,
                "success": False
            }
        
    except Exception as e:
        return {
            "error": f"Error al consultar OpenAI: {str(e)}",
            "player_a": player_a,
            "player_b": player_b,
            "tournament": tournament,
            "success": False
        }


def mock_tennis_odds(player_a: str, player_b: str, tournament: str) -> dict:
    """
    Genera datos ficticios de cuotas de apuestas para un partido específico.
    
    Args:
        player_a (str): Nombre del primer jugador
        player_b (str): Nombre del segundo jugador
        tournament (str): Nombre del torneo
    
    Returns:
        dict: Cuotas ficticias estructuradas para el partido consultado
    """
    
    # Generar cuotas realistas basadas en nombres de jugadores conocidos
    # Simular que algunos jugadores son favoritos
    top_players = ["Djokovic", "Alcaraz", "Sinner", "Medvedev", "Zverev", "Tsitsipas"]
    
    # Determinar quién es el favorito basado en el nombre
    player_a_rank = 1 if any(top in player_a for top in top_players) else random.randint(2, 50)
    player_b_rank = 1 if any(top in player_b for top in top_players) else random.randint(2, 50)
    
    # Ajustar cuotas basándose en el ranking simulado
    if player_a_rank < player_b_rank:
        favorite = player_a
        underdog = player_b
        favorite_odds = round(random.uniform(1.20, 1.80), 2)
        underdog_odds = round(random.uniform(2.20, 4.50), 2)
    else:
        favorite = player_b
        underdog = player_a
        favorite_odds = round(random.uniform(1.20, 1.80), 2)
        underdog_odds = round(random.uniform(2.20, 4.50), 2)
    
    # Generar cuotas para Set Betting
    set_betting_odds = {
        f"2-0 gana {favorite}": round(random.uniform(1.80, 2.50), 2),
        f"2-1 gana {favorite}": round(random.uniform(2.50, 3.50), 2),
        f"2-0 gana {underdog}": round(random.uniform(4.00, 8.00), 2),
        f"2-1 gana {underdog}": round(random.uniform(3.00, 5.00), 2)
    }
    
    # Generar cuotas para Set Score
    set_score_odds = {
        f"{favorite} set 1 gana 6-4": round(random.uniform(2.50, 3.50), 2),
        f"{favorite} set 1 gana 6-3": round(random.uniform(2.20, 3.00), 2),
        f"{favorite} set 1 gana 7-5": round(random.uniform(3.00, 4.00), 2),
        f"{underdog} set 1 gana 6-4": round(random.uniform(3.50, 5.00), 2),
        f"{underdog} set 1 gana 6-3": round(random.uniform(4.00, 6.00), 2)
    }
    
    # Generar cuotas para Both Win Set
    both_win_set_odds = {
        f"{player_a} y {player_b} ganan al menos un set": round(random.uniform(1.40, 1.80), 2)
    }
    
    # Generar cuotas para Player Set Win
    player_set_win_odds = {
        f"{favorite} gana 1 set": round(random.uniform(1.10, 1.30), 2),
        f"{underdog} gana 1 set": round(random.uniform(1.60, 2.20), 2)
    }
    
    # Generar cuotas para Combined Bet
    combined_bet_odds = {
        f"{favorite} gana el set 1 por 6-4": round(random.uniform(3.50, 4.50), 2),
        f"{favorite} gana el set 1 por 6-3": round(random.uniform(3.00, 4.00), 2),
        f"{underdog} gana el set 1 por 6-4": round(random.uniform(4.50, 6.00), 2),
        f"{underdog} gana el set 1 por 6-3": round(random.uniform(4.00, 5.50), 2)
    }
    
    # Crear el diccionario de cuotas
    odds_data = {
        "Match Winner": {
            player_a: favorite_odds if favorite == player_a else underdog_odds,
            player_b: favorite_odds if favorite == player_b else underdog_odds
        },
        "Set Betting": set_betting_odds,
        "Set Score": set_score_odds,
        "Both Win Set": both_win_set_odds,
        "Player Set Win": player_set_win_odds,
        "Combined Bet": combined_bet_odds,
        "success": True,
        "fetched_at": datetime.now().isoformat(),
        "player_a": player_a,
        "player_b": player_b,
        "tournament": tournament,
        "favorite": favorite,
        "underdog": underdog,
        "note": "Datos ficticios generados para propósitos de demostración"
    }
    
    return odds_data