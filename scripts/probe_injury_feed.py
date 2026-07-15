import importlib.util
import re

spec = importlib.util.spec_from_file_location("client", "tennisAgents/dataflows/flashscore_scraper/client.py")
client_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(client_mod)
c = client_mod.FlashscoreClient(locale="es")
pid = "YwiLpILD"

# Brute force short feed prefixes
prefixes = [
    "pi", "pj", "pk", "pl", "pm", "pn", "po", "pp", "pq", "pr", "ps", "pt", "pu", "pv", "pw", "px", "py", "pz",
    "pia", "pib", "pic", "pid", "pie", "pif", "pig", "pih", "pii", "pij", "pik", "pil", "pim", "pin", "pio", "pip",
    "inj", "abs", "med", "ph", "pd", "pe", "pf", "pg",
    "ti", "tm", "to", "tp",
]
for prefix in prefixes:
    for pattern in (
        f"/2/x/feed/{prefix}_1_{pid}",
        f"/2/x/feed/{prefix}_2_{pid}",
        f"/2/x/feed/{prefix}_1_167_{pid}",
        f"/2/x/feed/{prefix}_2_167_{pid}_1_es_1",
    ):
        try:
            text = c._get_text(c.feed_base + pattern)
            if text and text != "0" and len(text) > 5:
                print("HIT", pattern, "len", len(text), repr(text[:250]))
        except Exception:
            pass

print("\n--- injury page ---")
html = c._get_text(f"https://www.flashscore.es/jugador/van-de-zandschulp-botic/{pid}/historial-de-lesiones/")
print("has dates", "02.10.2025" in html, "CADERA" in html)
for needle in ("02.10.2025", "CADERA", "ISQUIOTIBIALES", "Historial de lesiones"):
    if needle in html:
        idx = html.find(needle)
        print(needle, "->", repr(html[idx - 80 : idx + 120]))
