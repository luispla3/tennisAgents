import importlib.util
import re

spec = importlib.util.spec_from_file_location("client", "tennisAgents/dataflows/flashscore_scraper/client.py")
client_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(client_mod)
c = client_mod.FlashscoreClient(locale="es")
js = c._get_text("https://www.flashscore.es/res/_fs/build/teamPage.client.05ca532.js")

for term in ["matchRecord", "injury_history_title", "InjuryParser", "TeamInjur", "getTeamInjur", "TeamPageParser", "ParticipantInjur"]:
    if term in js:
        print("has", term)

for m in re.finditer(r"matchRecord", js):
    ctx = js[max(0, m.start() - 250) : m.start() + 350]
    if "injur" in ctx.lower():
        print("\n=== matchRecord+injury @", m.start(), "===")
        print(ctx)

# search chunk 11083 or injury parser module numbers
for m in re.finditer(r"Injur[a-zA-Z_]*Parser|Injur[a-zA-Z_]*Feed|getTeamInjur[a-zA-Z_]*|getInjur[a-zA-Z_]*Feed", js):
    print("PAT", m.group(0), "@", m.start())

# find where i.injuries is assigned - search broader init function around line 32277
idx = js.find("setInjuries(i.injuries)")
print("\ninit context:")
print(js[idx - 2000 : idx + 500])
