import importlib.util

spec = importlib.util.spec_from_file_location("client", "tennisAgents/dataflows/flashscore_scraper/client.py")
client_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(client_mod)
c = client_mod.FlashscoreClient(locale="es")
pid = "YwiLpILD"

bases = [
    "https://global.flashscore.ninja",
    "https://13.flashscore.ninja",
    "https://2.flashscore.ninja",
]

feeds = [
    f"/2/x/feed/p_2_139_{pid}_2_es_1",
    f"/13/x/feed/p_2_139_{pid}_2_es_1",
    f"/2/x/feed/p_2_139_{pid}_1_es_1",
    f"/2/x/feed/p_2_{pid}_2_es_1",
    f"/2/x/feed/p_1_{pid}",
    f"/2/x/feed/pm_1_{pid}",
    f"/2/x/feed/pm_2_{pid}",
    f"/2/x/feed/pij_1_{pid}",
    f"/2/x/feed/pij_2_{pid}",
    f"/2/x/feed/piu_1_{pid}",
    f"/2/x/feed/piu_2_{pid}",
    f"/2/x/feed/pii_1_{pid}",
    f"/2/x/feed/pii_2_{pid}",
    f"/2/x/feed/pi_1_{pid}",
    f"/2/x/feed/pi_2_{pid}",
]

for base in bases:
    for path in feeds:
        url = base + path
        try:
            text = c._get_text(url)
        except Exception as e:
            continue
        if not text or text == "0" or len(text) < 10:
            continue
        markers = ["injury", "INJ", "CADERA", "ISQUI", "PIJ", "PIU", "PII", "PIH", "PIF"]
        found = [m for m in markers if m in text]
        has_dates = any(x in text for x in ["2025", "2024", "2026", ".10.", ".05."])
        if found or has_dates:
            print("HIT", url, "len", len(text), "markers", found)
            print(repr(text[:500]))
            print("---")
