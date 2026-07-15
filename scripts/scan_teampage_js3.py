import importlib.util
import re

spec = importlib.util.spec_from_file_location("client", "tennisAgents/dataflows/flashscore_scraper/client.py")
client_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(client_mod)
c = client_mod.FlashscoreClient(locale="es")
js = c._get_text("https://www.flashscore.es/res/_fs/build/teamPage.client.05ca532.js")

for term in ["injury_history", "setInjuries", "i.injuries", "_injuries", "injury_name", "injury_until"]:
    for m in re.finditer(re.escape(term), js):
        print(f"\n=== {term} @ {m.start()} ===")
        print(js[max(0, m.start() - 200) : m.start() + 300])
        break

# find feed fetcher related to injuries
for m in re.finditer(r".{0,80}injuries.{0,200}", js):
    chunk = m.group(0)
    if "feed" in chunk.lower() or "fetch" in chunk.lower() or "parse" in chunk.lower() or "Feed" in chunk:
        print("\nFEED CHUNK:", chunk[:280])

# search for p_ feed pattern near injuries
idx = js.find("injury_history")
while idx != -1:
    sub = js[idx : idx + 500]
    if "feed" in sub.lower() or "p_" in sub:
        print("\nNEAR injury_history:", sub[:400])
    idx = js.find("injury_history", idx + 1)
