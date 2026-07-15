import importlib.util
import json
import re

spec = importlib.util.spec_from_file_location("client", "tennisAgents/dataflows/flashscore_scraper/client.py")
client_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(client_mod)
c = client_mod.FlashscoreClient(locale="es")

html = c._get_text("https://www.flashscore.es/jugador/van-de-zandschulp-botic/YwiLpILD/")

# Extract injuries block
m = re.search(r'"injuries"\s*:\s*(\{.*?\})\s*,\s*"matchRecord"', html, re.DOTALL)
if m:
    blob = m.group(1)
    print("injuries blob len", len(blob))
    print(blob[:2000])
    try:
        data = json.loads(blob)
        print("\nParsed injuries keys:", data.keys())
        print("injury_history count:", len(data.get("injury_history", [])))
        for item in data.get("injury_history", [])[:5]:
            print(item)
    except json.JSONDecodeError as e:
        print("JSON error", e)
else:
    # try injury_history directly
    m2 = re.search(r'"injury_history"\s*:\s*(\[.*?\])\s*,\s*"header"', html, re.DOTALL)
    if m2:
        print("history array", m2.group(1)[:1500])
    else:
        idx = html.find('"injury_history"')
        print("idx", idx)
        print(html[idx : idx + 1500])
