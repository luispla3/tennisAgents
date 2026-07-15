import sys

sys.path.insert(0, r"C:\Users\luisp\tennisAgents")

from tennisAgents.dataflows.tournament_utils import normalize_tournament
from tennisAgents.dataflows.interface import get_weather_forecast, get_tournament_data

CASES = [
    "CHALLENGER MEN - SINGLES: Cordenons (Italy), clay",
    "ATP 250 - Gstaad (Switzerland), clay",
    "Swiss Open Gstaad",
    "Cordenons CH",
    "Wimbledon",
    "Miami Open",
    "Roland Garros - Paris, France",
    "Indian Wells Masters",
    "ATP 500 - Barcelona (Spain), clay",
    "Trieste CH",
]

print("=== NORMALIZE TOURNAMENT ===")
for case in CASES:
    identity = normalize_tournament(case)
    print(f"IN:  {case}")
    print(f"OUT: display={identity.display_name}")
    print(f"     search={identity.search_name} | loc={identity.location} | surf={identity.surface} | cat={identity.category}")
    print()

print("=== BETFAIR CORDENONS WEATHER ===")
report = get_weather_forecast(
    "CHALLENGER MEN - SINGLES: Cordenons (Italy), clay",
    "2026-07-15 14:00",
    "CHALLENGER MEN - SINGLES: Cordenons (Italy), clay",
)
print(report[:400])
print()

print("=== BETFAIR CORDENONS TOURNAMENT ===")
print(get_tournament_data("CHALLENGER MEN - SINGLES: Cordenons (Italy), clay", "atp", "2026-07-15")[:350])
