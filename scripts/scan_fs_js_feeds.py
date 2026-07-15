import importlib.util
import re

spec = importlib.util.spec_from_file_location("client", "tennisAgents/dataflows/flashscore_scraper/client.py")
client_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(client_mod)
c = client_mod.FlashscoreClient(locale="es")

for fname in [
    "https://www.flashscore.es/res/_fs/build/framework.afc3133.js",
    "https://www.flashscore.es/res/_fs/build/loader.3e0b4c8.js",
    "https://www.flashscore.es/res/_fs/build/modules.8f6f816.js",
]:
    js = c._get_text(fname)
    feeds = sorted(set(re.findall(r"/x/feed/[a-z0-9_{}]+", js)))
    injury_related = [f for f in feeds if any(x in f for x in ("pi", "inj", "pn", "pm", "pr", "pu", "pd"))]
    print("\nFILE", fname.split("/")[-1], "feeds", len(feeds))
    for f in injury_related[:60]:
        print(" ", f)

    for term in ["InjuryHistory", "injuryHistory", "playerInjury", "INJURY_HISTORY", "pij_", "piu_", "pn_1", "pn_2"]:
        if term in js:
            idx = js.find(term)
            print("TERM", term, js[idx : idx + 180])
