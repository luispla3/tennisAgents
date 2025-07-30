from news_utils import fetch_news
from odds_utils import fetch_tennis_odds
from odds_utils import generate_mock_odds
from player_utils import fetch_atp_rankings
from player_utils import fetch_recent_matches
from player_utils import fetch_surface_winrate
from player_utils import fetch_head_to_head

def get_news(query: str, curr_date: str) -> str:
    """
    Interfaz que prepara y formatea las noticias obtenidas desde Google News.
    """
    noticias = fetch_news(query, curr_date)

    if not noticias:
        return f"No se encontraron noticias sobre '{query}' para la fecha {curr_date}."

    noticias_str = f"## Noticias sobre '{query}' para el {curr_date}:\n\n"
    for noticia in noticias:
        noticias_str += f"### {noticia['title']}\n"
        noticias_str += f"{noticia['description']}\n"
        noticias_str += f"[Enlace]({noticia['url']})\n\n"

    return noticias_str


def get_atp_news(curr_date: str) -> str:
    """
    Obtiene noticias recientes sobre el circuito ATP desde una API (NewsAPI).
    """
    noticias = fetch_news("ATP tennis", curr_date)

    if not noticias:
        return f"No se encontraron noticias sobre ATP en la fecha {curr_date}."

    noticias_str = f"## Noticias sobre ATP para el {curr_date}:\n\n"
    for noticia in noticias:
        noticias_str += f"### {noticia['title']}\n"
        noticias_str += f"{noticia['description']}\n"
        noticias_str += f"[Enlace]({noticia['url']})\n\n"

    return noticias_str


def get_tennisworld_news(curr_date: str) -> str:
    """
    Busca noticias recientes sobre tenis relacionadas con TennisWorld u otras fuentes relevantes usando NewsAPI.
    """
    noticias = fetch_news("tennis news", curr_date)

    if not noticias:
        return f"No se encontraron noticias relevantes en la fecha {curr_date}."

    noticias_str = f"## Noticias tipo TennisWorld del {curr_date}:\n\n"
    for noticia in noticias:
        noticias_str += f"### {noticia['title']}\n"
        noticias_str += f"{noticia['description']}\n"
        noticias_str += f"[Leer más]({noticia['url']})\n\n"

    return noticias_str


def get_tennis_odds(player1: str, player2: str, match_date: str) -> str:
    """
    Consulta las cuotas de apuestas reales para un partido de tenis usando una API.
    """
    odds_data = fetch_tennis_odds(player1, player2, match_date)

    if not odds_data:
        return f"No se encontraron cuotas para el partido {player1} vs {player2} el {match_date}."

    result = f"## Cuotas para {player1} vs {player2} ({match_date}):\n\n"
    for bookmaker, cuota in odds_data.items():
        result += f"- **{bookmaker}**: {player1} → {cuota['player1']}, {player2} → {cuota['player2']}\n"
    return result



def get_mock_odds_data(player1: str, player2: str) -> str:
    """
    Devuelve una simulación realista de cuotas para un partido entre dos jugadores.
    """
    odds_data = generate_mock_odds(player1, player2)

    result = f"## Cuotas simuladas para {player1} vs {player2}:\n\n"
    for bookmaker, cuota in odds_data.items():
        result += f"- **{bookmaker}**: {player1} → {cuota['player1']}, {player2} → {cuota['player2']}\n"
    return result


def get_atp_rankings() -> str:
    """
    Consulta el ranking ATP actual y lo devuelve formateado.
    """
    rankings = fetch_atp_rankings()

    if not rankings:
        return "No se pudo obtener el ranking ATP."

    result = "## Ranking ATP actual:\n\n"
    for jugador in rankings:
        result += f"{jugador['rank']}. {jugador['name']} ({jugador['country']}) - {jugador['points']} pts\n"
    return result


def get_recent_matches(player_name: str, num_matches: int = 5) -> str:
    """
    Devuelve los últimos partidos jugados por el jugador especificado.
    """
    matches = fetch_recent_matches(player_name, num_matches)

    if not matches:
        return f"No se encontraron partidos recientes para {player_name}."

    result = f"## Últimos {num_matches} partidos de {player_name}:\n\n"
    for m in matches:
        result += f"- {m['date']} | {m['tournament']} | vs {m['opponent']} | Resultado: {m['result']} | Superficie: {m['surface']}\n"

    return result


def get_surface_winrate(player_name: str, surface: str) -> str:
    """
    Devuelve el porcentaje de victorias del jugador en una superficie específica.
    """
    stats = fetch_surface_winrate(player_name, surface)

    if not stats:
        return f"No se encontraron datos sobre {player_name} en {surface}."

    return (
        f"## Rendimiento de {player_name} en {surface}:\n\n"
        f"- Partidos ganados: {stats['wins']}\n"
        f"- Partidos perdidos: {stats['losses']}\n"
        f"- Winrate: {stats['winrate']}%"
    )


def get_head_to_head(player1: str, player2: str) -> str:
    """
    Devuelve el historial H2H entre dos jugadores de tenis.
    """
    data = fetch_head_to_head(player1, player2)

    if not data:
        return f"No se encontró historial H2H entre {player1} y {player2}."

    resumen = f"## Historial H2H entre {player1} y {player2}:\n\n"
    resumen += f"- Victorias de {player1}: {data['wins_p1']}\n"
    resumen += f"- Victorias de {player2}: {data['wins_p2']}\n"
    resumen += f"- Total de enfrentamientos: {data['total']}\n\n"

    resumen += "### Últimos partidos:\n"
    for match in data["recent_matches"]:
        resumen += (
            f"- {match['date']} | {match['tournament']} | {match['winner']} ganó en {match['score']} "
            f"(Superficie: {match['surface']})\n"
        )

    return resumen

