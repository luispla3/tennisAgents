import importlib.util
import re

spec = importlib.util.spec_from_file_location("client", "tennisAgents/dataflows/flashscore_scraper/client.py")
client_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(client_mod)
c = client_mod.FlashscoreClient(locale="es")
js = c._get_text("https://www.flashscore.es/res/_fs/build/teamPage.client.05ca532.js")

for term in ["injury_from", "injuriesT", "injuries:", "getInjur", "Injuries"]:
    idx = 0
    count = 0
    while count < 8:
        idx = js.find(term, idx)
        if idx == -1:
            break
        print(f"\n=== {term} @ {idx} ===")
        print(js[max(0, idx - 150) : idx + 250])
        idx += len(term)
        count += 1

# search persisted query patterns
for m in re.finditer(r"operationName\":\"([^\"]+)\"", js):
    name = m.group(1)
    if "njur" in name.lower() or "layer" in name.lower() or "articipant" in name.lower() or "team" in name.lower():
        print("op", name)

for m in re.finditer(r"injuries[A-Za-z_]*", js):
    s = m.group(0)
    if s not in ("injuries",):
        pass

terms = sorted(set(re.findall(r"injuries[A-Za-z_]{0,20}", js)))
print("injury terms", terms[:30])
