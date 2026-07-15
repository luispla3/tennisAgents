import sys
sys.path.insert(0, r"C:\Users\luisp\tennisAgents")

PLAYER = "Tabur"
OPPONENT = "Rinderknech"
TOURNAMENT = "Gstaad"
DATE = "2026-07-15"

results = {}

# News
from tennisAgents.dataflows.news_utils import fetch_news_for_match
news = fetch_news_for_match(PLAYER, OPPONENT, TOURNAMENT, DATE)
results["news"] = {
    "ok": "Sin resultados" not in news and len(news) > 500,
    "len": len(news),
    "empty": "Sin resultados" in news or "No se encontraron" in news,
}

# Players - sub-tools
from tennisAgents.dataflows.player_utils import (
    fetch_atp_rankings,
    fetch_injury_reports,
    fetch_surface_winrate,
    fetch_recent_matches,
    fetch_head_to_head,
)

for name, fn, args in [
    ("rankings", fetch_atp_rankings, (PLAYER, OPPONENT)),
    ("injuries", fetch_injury_reports, (PLAYER, OPPONENT)),
    ("surface_p1", fetch_surface_winrate, (PLAYER, "clay")),
    ("surface_p2", fetch_surface_winrate, (OPPONENT, "clay")),
    ("recent", fetch_recent_matches, (PLAYER, OPPONENT, 10)),
    ("h2h", fetch_head_to_head, (PLAYER, OPPONENT)),
]:
    try:
        out = fn(*args) if name != "recent" else fn(PLAYER, OPPONENT, 10)
        bad = any(x in (out or "") for x in (
            "No se encontr", "Error al", "No hay estadísticas", "no verificado",
        ))
        results[f"players_{name}"] = {
            "ok": bool(out) and len(out) > 100 and not out.startswith("Error"),
            "len": len(out or ""),
            "weak": bad,
            "sample": (out or "")[:120].replace("\n", " "),
        }
    except Exception as exc:
        results[f"players_{name}"] = {"ok": False, "error": str(exc)}

# Tournament
from tennisAgents.dataflows.interface import get_tournament_data
tournament = get_tournament_data(TOURNAMENT, "atp", DATE)
results["tournament"] = {
    "ok": bool(tournament) and "Error" not in tournament[:80],
    "len": len(tournament or ""),
    "has_surface": "clay" in (tournament or "").lower() or "tierra" in (tournament or "").lower(),
    "sample": (tournament or "")[:120].replace("\n", " "),
}

# Weather
from tennisAgents.dataflows.interface import get_weather_forecast
weather = get_weather_forecast(TOURNAMENT, f"{DATE} 14:00", "Gstaad, Switzerland")
results["weather"] = {
    "ok": bool(weather) and not weather.startswith("Error"),
    "len": len(weather or ""),
    "has_temp": any(x in (weather or "").lower() for x in ("temp", "°", "viento", "wind", "lluvia", "rain")),
    "sample": (weather or "")[:120].replace("\n", " "),
}

print("=== HEALTH CHECK Rinderknech vs Tabur @ Gstaad ===")
for key, data in results.items():
    print(key, data)
