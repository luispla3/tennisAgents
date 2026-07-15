import importlib.util
import re

spec = importlib.util.spec_from_file_location("client", "tennisAgents/dataflows/flashscore_scraper/client.py")
client_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(client_mod)
c = client_mod.FlashscoreClient(locale="es")
js = c._get_text("https://www.flashscore.es/x/js/core_13_2306000000.js")

for term in ["graphql", "lsapp", "TEAM_PAGE", "InjuryHistory", "injuryHistory", "playerInjury"]:
    for m in re.finditer(re.escape(term), js, re.I):
        print("\n===", term, "at", m.start(), "===")
        print(js[m.start() - 120 : m.start() + 220])
        break
