import importlib.util
import json
import re

spec = importlib.util.spec_from_file_location("client", "tennisAgents/dataflows/flashscore_scraper/client.py")
client_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(client_mod)
c = client_mod.FlashscoreClient(locale="es")

urls = [
    "https://www.flashscore.es/jugador/van-de-zandschulp-botic/YwiLpILD/",
    "https://www.flashscore.es/jugador/van-de-zandschulp-botic/YwiLpILD/historial-de-lesiones/",
]
for url in urls:
    html = c._get_text(url)
    print("\nURL", url)
    print("len", len(html))
    for needle in ["injury_history", "injury_from", "teamPageEnvironment", "02.10.2025", "CADERA", "ingle"]:
        print(needle, needle in html)

    m = re.search(r"window\.teamPageEnvironment\s*=\s*(\{.*?\});", html, re.DOTALL)
    if m:
        blob = m.group(1)
        print("teamPageEnvironment len", len(blob))
        if "injury" in blob.lower():
            idx = blob.lower().find("injury")
            print("injury snippet", blob[max(0, idx - 100) : idx + 500])
    else:
        # try alternate patterns
        for pat in [
            r'"injuries"\s*:\s*(\{.*?\})\s*,\s*"matchRecord"',
            r'"injury_history"\s*:\s*(\[.*?\])',
        ]:
            mm = re.search(pat, html, re.DOTALL)
            if mm:
                print("pat hit", pat[:40], mm.group(1)[:400])

# parse p feed for injury keys PIL PIN PIT PIW
text = c._get_text(f"{c.feed_base}/2/x/feed/p_2_139_YwiLpILD_2_es_1")
for key in ["PIL", "PIN", "PIT", "PIW", "PIH", "PII", "PIJ", "PIK", "PIU", "PIR", "PID"]:
    if key in text:
        print("p feed has", key)
        idx = text.find(key)
        print(repr(text[idx : idx + 120]))

rows = text.split("\xac")
for r in rows:
    if any(k in r for k in ("PIL", "PIN", "PIT", "PIW", "PIH", "PII", "PIJ")):
        print("ROW", repr(r[:250]))
