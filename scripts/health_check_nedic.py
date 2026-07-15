import sys
sys.path.insert(0, r"C:\Users\luisp\tennisAgents")

PLAYER = "Nedic A."
OPPONENT = "Dalla Valle E."
TOURNAMENT = "Cordenons"
DATE = "2026-07-15"

results = {}

from tennisAgents.dataflows.news_utils import fetch_news_for_match
news = fetch_news_for_match(PLAYER, OPPONENT, TOURNAMENT, DATE)
results["news"] = {
    "ok": "Sin resultados" not in news and len(news) > 200,
    "len": len(news),
    "sample": news[:150].replace("\n", " "),
}

from tennisAgents.dataflows.player_utils import (
    fetch_atp_rankings,
    fetch_injury_reports,
    fetch_surface_winrate,
    fetch_recent_matches,
    fetch_head_to_head,
)
from tennisAgents.dataflows.tournament_utils import resolve_tournament_surface, resolve_tournament_location

surface = resolve_tournament_surface(TOURNAMENT) or "clay"
location = resolve_tournament_location(TOURNAMENT) or TOURNAMENT
results["surface_resolved"] = surface
results["location_resolved"] = location

for name, fn, args in [
    ("rankings", fetch_atp_rankings, (PLAYER, OPPONENT)),
    ("injuries", fetch_injury_reports, (PLAYER, OPPONENT)),
    ("surface_p1", fetch_surface_winrate, (PLAYER, surface)),
    ("surface_p2", fetch_surface_winrate, (OPPONENT, surface)),
    ("recent", fetch_recent_matches, (PLAYER, OPPONENT, 10)),
    ("h2h", fetch_head_to_head, (PLAYER, OPPONENT)),
]:
    try:
        out = fn(*args) if name != "recent" else fn(PLAYER, OPPONENT, 10)
        bad = any(x in (out or "") for x in (
            "No se encontr", "Error al", "No hay estadísticas", "no verificado",
        ))
        results[f"players_{name}"] = {
            "ok": bool(out) and len(out) > 80 and not (out or "").startswith("Error"),
            "len": len(out or ""),
            "weak": bad,
            "sample": (out or "")[:150].replace("\n", " "),
        }
    except Exception as exc:
        results[f"players_{name}"] = {"ok": False, "error": str(exc)}

from tennisAgents.dataflows.interface import get_tournament_data, get_weather_forecast

tournament = get_tournament_data(TOURNAMENT, "atp", DATE)
results["tournament"] = {
    "ok": bool(tournament) and "Error" not in (tournament or "")[:80],
    "len": len(tournament or ""),
    "sample": (tournament or "")[:150].replace("\n", " "),
}

weather = get_weather_forecast(TOURNAMENT, f"{DATE} 14:00", location)
results["weather"] = {
    "ok": bool(weather) and not (weather or "").startswith("Error"),
    "len": len(weather or ""),
    "sample": (weather or "")[:150].replace("\n", " "),
}

print(f"=== HEALTH CHECK {PLAYER} vs {OPPONENT} @ {TOURNAMENT} ===")
for key, data in results.items():
    print(key, data)
