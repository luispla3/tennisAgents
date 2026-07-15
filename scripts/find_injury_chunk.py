import importlib.util
import re

spec = importlib.util.spec_from_file_location("client", "tennisAgents/dataflows/flashscore_scraper/client.py")
client_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(client_mod)
c = client_mod.FlashscoreClient(locale="es")

js_files = re.findall(
    r"https://www\.flashscore\.es/[^\"']+\.js",
    c._get_text("https://www.flashscore.es/jugador/van-de-zandschulp-botic/YwiLpILD/"),
)
print("js files", len(js_files))

for url in js_files:
    try:
        js = c._get_text(url)
    except Exception:
        continue
    if "injuryTable" in js or "InjuryHistory" in js or "injuryHistory" in js:
        print("FOUND in", url.split("/")[-1])
        idx = js.find("injuryTable") if "injuryTable" in js else js.find("injuryHistory")
        print(js[idx - 150 : idx + 400])

    for m in re.finditer(r"sha256Hash\":\"([a-f0-9]{64})\"", js):
        start = max(0, m.start() - 200)
        ctx = js[start : m.start() + 80]
        if any(x in ctx.lower() for x in ("injur", "participant", "player", "team")):
            print("HASH", url.split("/")[-1], m.group(1), ctx[:120])
