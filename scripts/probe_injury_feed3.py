import importlib.util
import re

spec = importlib.util.spec_from_file_location("client", "tennisAgents/dataflows/flashscore_scraper/client.py")
client_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(client_mod)
c = client_mod.FlashscoreClient(locale="es")
pid = "YwiLpILD"

text = c._get_text(f"{c.feed_base}/2/x/feed/pm_1_{pid}")
print("pm feed length", len(text))
for needle in ["INJ", "inj", "CADERA", "LES", "absence", "PIJ", "PIU", "PII"]:
    if needle in text:
        print("found", needle)

# dump unique row starters
rows = text.split("~")
starts = sorted({r.split("¬")[0][:3] if r else "" for r in rows if r})
print("row starts", starts[:40])

# search core js file saved locally
js = c._get_text("https://www.flashscore.es/x/js/core_13_2306000000.js")
patterns = [
    r"playerInjury[A-Za-z_]*",
    r"injuryHistory[A-Za-z_]*",
    r"InjuryHistory[A-Za-z_]*",
    r"pij_[0-9]",
    r"piu_[0-9]",
    r"/feed/pi[a-z]_",
]
for pat in patterns:
    hits = sorted(set(re.findall(pat, js)))
    if hits:
        print("PAT", pat, hits[:20])

# brute short: pi + letter feeds with _1_pid only
for suffix in "abcdefghijklmnopqrstuvwxyz":
    prefix = "pi" + suffix
    p = f"/2/x/feed/{prefix}_1_{pid}"
    try:
        t = c._get_text(c.feed_base + p)
        if t and t != "0" and len(t) > 5 and prefix not in ("pi1", "pi2"):
            print("HIT", prefix, len(t), repr(t[:200]))
    except Exception:
        pass
