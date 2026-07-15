import importlib.util

spec = importlib.util.spec_from_file_location("client", "tennisAgents/dataflows/flashscore_scraper/client.py")
client_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(client_mod)
c = client_mod.FlashscoreClient(locale="es")
pid = "YwiLpILD"

# Extended brute force 2-3 letter prefixes
hits = []
for a in "pqrstuvwxyz":
    for b in "abcdefghijklmnopqrstuvwxyz":
        prefix = a + b
        for suffix in (f"_1_{pid}", f"_2_{pid}", f"_1_167_{pid}", f"_2_167_{pid}_1_es_1"):
            pattern = f"/2/x/feed/{prefix}{suffix}"
            try:
                text = c._get_text(c.feed_base + pattern)
                if text and text != "0" and len(text) > 20:
                    hits.append((pattern, len(text), text[:120]))
            except Exception:
                pass

for h in sorted(hits, key=lambda x: -x[1]):
    print(h[0], "len", h[1], repr(h[2]))

print("total hits", len(hits))
