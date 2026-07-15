import importlib.util
import re

spec = importlib.util.spec_from_file_location("client", "tennisAgents/dataflows/flashscore_scraper/client.py")
client_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(client_mod)
c = client_mod.FlashscoreClient(locale="es")
js = c._get_text("https://www.flashscore.es/x/js/core_13_2306000000.js")

for term in ["graphql", "lsapp", "injury", "Injury", "pij", "piu", "participant", "teamPage", "TEAM_PAGE"]:
    if term.lower() in js.lower():
        print("has", term)

urls = sorted(set(re.findall(r"https?://[a-zA-Z0-9._/-]+", js)))
for u in urls:
    if any(x in u.lower() for x in ("graphql", "lsapp", "feed", "ninja", "ds.")):
        print("URL", u)

# search feed template strings
for m in re.finditer(r"feed/[a-z_0-9{}]+", js):
    s = m.group(0)
    if len(s) < 40:
        print("FEED", s)
