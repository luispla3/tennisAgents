import importlib.util
import re

spec = importlib.util.spec_from_file_location("client", "tennisAgents/dataflows/flashscore_scraper/client.py")
client_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(client_mod)
c = client_mod.FlashscoreClient(locale="es")
pid = "YwiLpILD"
text = c._get_text(f"{c.feed_base}/2/x/feed/pm_1_{pid}")

# find injury-related LV keys
for m in re.finditer(r"LV[^\x00-\x1f]*", text):
    chunk = m.group(0)
    if any(x in chunk.lower() for x in ("inj", "les", "hip", "cadera", "ill", "abs", "med")):
        print(chunk[:200])

# dump all unique LV key prefixes
keys = sorted(set(re.findall(r"LV[^\x00-\x1f]{0,20}", text)))
print("LV count", len(keys))
for k in keys:
    if "INJ" in k or "PI" in k or "IH" in k or "ABS" in k:
        print(k)

# search for PI* rows in pm feed
rows = text.split("\xac")
pi_rows = [r for r in rows if r.startswith("PI") or "PI" in r[:4]]
print("pi rows", len(pi_rows))
for r in pi_rows[:20]:
    print(repr(r[:200]))

# brute force pm with suffixes
for suffix in ["_2_es_1", "_1_es_1", "_2_es_1_s", "_1_es_1_s", "_167_2_es_1"]:
    path = f"/2/x/feed/pm_1_{pid}{suffix}"
    try:
        t = c._get_text(c.feed_base + path)
        if t and len(t) > 100:
            pi = [r for r in t.split("\xac") if r.startswith("PI")]
            print(path, "len", len(t), "PI rows", len(pi))
            if pi:
                print(" sample", repr(pi[0][:250]))
    except Exception:
        pass
