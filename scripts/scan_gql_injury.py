import importlib.util
import re

spec = importlib.util.spec_from_file_location("client", "tennisAgents/dataflows/flashscore_scraper/client.py")
client_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(client_mod)
c = client_mod.FlashscoreClient(locale="es")

files = [
    "https://www.flashscore.es/res/_fs/build/modules.8f6f816.js",
    "https://www.flashscore.es/res/_fs/build/framework.afc3133.js",
    "https://www.flashscore.es/x/js/core_13_2306000000.js",
]
for fname in files:
    js = c._get_text(fname)
    for term in ["InjuryHistory", "injuryHistory", "playerInjury", "ParticipantInjury", "injury_history", "INJURY_HISTORY"]:
        if term in js:
            print("\nFILE", fname.split("/")[-1], "TERM", term)
            idx = js.find(term)
            print(js[idx - 150 : idx + 300])

    for m in re.finditer(r"operationName[:\"']+[A-Za-z0-9_]*Injur[A-Za-z0-9_]*", js):
        print("OP", fname.split("/")[-1], m.group(0))

    for m in re.finditer(r"[A-Za-z0-9_]*[Ii]njur[A-Za-z0-9_]*", js):
        s = m.group(0)
        if len(s) > 8 and len(s) < 60:
            print("ID", s)
