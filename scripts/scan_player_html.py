import importlib.util
import re

spec = importlib.util.spec_from_file_location("client", "tennisAgents/dataflows/flashscore_scraper/client.py")
client_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(client_mod)
c = client_mod.FlashscoreClient(locale="es")
html = c._get_text("https://www.flashscore.es/jugador/van-de-zandschulp-botic/YwiLpILD/")

needles = ["02.10.2025", "12.10.2025", "CADERA", "ISQUIOTIBIALES", "Historial de lesiones", "injury", "INJURY"]
for n in needles:
    print(n, n in html)

# embedded json blobs
for pat in [r"window\.environment\s*=\s*(\{.*?\});", r"__NUXT__\s*=\s*(\{.*?\});", r"\"injuries\"\s*:\s*(\[.*?\])"]:
    m = re.search(pat, html, re.S)
    if m:
        print("PAT", pat[:30], "len", len(m.group(1)))

# find all flashscore.ninja urls in html
urls = re.findall(r"https://[a-z0-9.-]*flashscore\.ninja[^\"'\s<>]+", html)
print("ninja urls", urls[:20])

# save snippet around historial
idx = html.lower().find("historial")
if idx >= 0:
    print("context", repr(html[idx : idx + 500]))
