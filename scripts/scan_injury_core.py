import importlib.util
import re

spec = importlib.util.spec_from_file_location("client", "tennisAgents/dataflows/flashscore_scraper/client.py")
client_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(client_mod)
c = client_mod.FlashscoreClient(locale="es")
js = c._get_text("https://www.flashscore.es/x/js/core_13_2306000000.js")

for m in re.finditer(r".{0,80}injur.{0,120}", js, re.I):
    s = m.group(0)
    if "TRANS_" not in s and "BOXING" not in s and "MMA" not in s:
        print(s[:200])

# search for pnf
for term in ["pnf_", "p_2_", "participantInjury", "injuryHistory", "InjuryHistory"]:
    if term in js:
        idx = js.find(term)
        print("\nTERM", term, js[idx - 100 : idx + 200])
