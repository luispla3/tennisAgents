import importlib.util
import re

spec = importlib.util.spec_from_file_location("client", "tennisAgents/dataflows/flashscore_scraper/client.py")
client_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(client_mod)
c = client_mod.FlashscoreClient(locale="es")
js = c._get_text("https://www.flashscore.es/res/_fs/build/teamPage.client.05ca532.js")

# Find class that parses injuries from feed
for m in re.finditer(r"injury_history", js):
    ctx = js[max(0, m.start() - 400) : m.start() + 400]
    if "parse" in ctx.lower() or "feed" in ctx.lower() or "fetch" in ctx.lower() or "PI" in ctx:
        print("=== @", m.start(), "===")
        print(ctx)
        print()

# search PI* keys in feed parser style
for m in re.finditer(r'"PI[A-Z]"', js):
    print(m.group(0), js[m.start()-80:m.start()+80])

# find module that sets injuries from parsed data
for term in ["injuries:", "injuries=", ".injuries"]:
    idx = 0
    while True:
        idx = js.find(term, idx)
        if idx == -1:
            break
        ctx = js[max(0, idx - 300) : idx + 300]
        if "parse" in ctx.lower() or "feed" in ctx.lower() or "PI" in ctx or "injury" in ctx.lower():
            print(f"\n--- {term} @ {idx} ---")
            print(ctx)
        idx += len(term)
