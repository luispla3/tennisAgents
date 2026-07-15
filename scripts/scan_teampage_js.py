import importlib.util
import re

spec = importlib.util.spec_from_file_location("client", "tennisAgents/dataflows/flashscore_scraper/client.py")
client_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(client_mod)
c = client_mod.FlashscoreClient(locale="es")
js = c._get_text("https://www.flashscore.es/res/_fs/build/teamPage.client.05ca532.js")
print("len", len(js))
for term in ["injuryTable", "InjuryHistory", "injuryHistory", "pnf_", "sha256Hash", "/x/feed/", "participantInjury"]:
    print("has", term, term in js)

for m in re.finditer(r".{0,60}injuryTable.{0,120}", js):
    print("CTX", m.group(0)[:220])

feeds = sorted(set(re.findall(r"/x/feed/[a-zA-Z0-9_{}$]+", js)))
print("feeds", feeds)

for m in re.finditer(r"sha256Hash\":\"([a-f0-9]{64})\"", js):
    start = max(0, m.start() - 200)
    ctx = js[start : m.start() + 100]
    if any(x in ctx for x in ("Injur", "injur", "articipant", "layer", "Team")):
        print("HASH", m.group(1))
        print(ctx[:250])
