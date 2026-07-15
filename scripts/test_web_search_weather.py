import sys
sys.path.insert(0, r"C:\Users\luisp\tennisAgents")

from tennisAgents.dataflows.web_search_utils import perform_web_search
from tennisAgents.dataflows.weather_utils import fetch_weather_forecast

queries = [
    "weather forecast Cordenons Italy 2026-07-15",
    "Cordenons Italy weather July 15",
    "CHALLENGER MEN - SINGLES: Cordenons (Italy), clay weather",
]

print("=== WEB SEARCH TESTS ===")
for q in queries:
    r = perform_web_search(q, num_results=5, lang="en")
    empty = "No se encontraron" in r
    err = r.startswith("Error")
    print(f"Q: {q}")
    print(f"  len={len(r)} empty={empty} error={err}")
    print(f"  sample: {r[:250].replace(chr(10), ' | ')}")
    print()

print("=== OPEN-METEO / WEATHER PIPELINE ===")
for loc in [
    "Cordenons, Italy",
    "CHALLENGER MEN - SINGLES: Cordenons (Italy), clay",
    "Cordenons",
]:
    data = fetch_weather_forecast(loc, "2026-07-15 14:00", "Cordenons")
    src = data.get("source", "?")
    info = (data.get("weather_info") or data.get("error", ""))[:250]
    print(f"LOC: {loc}")
    print(f"  source={src}")
    print(f"  info: {info.replace(chr(10), ' | ')}")
    print()
