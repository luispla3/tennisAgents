import importlib.util
import re
from datetime import datetime

spec = importlib.util.spec_from_file_location("client", "tennisAgents/dataflows/flashscore_scraper/client.py")
client_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(client_mod)
c = client_mod.FlashscoreClient(locale="es")
pid = "YwiLpILD"

dates = [
    "24.04.2026",
    "04.05.2026",
    "25.04.2025",
    "22.05.2025",
    "25.07.2023",
    "22.08.2023",
]
ts_list = [int(datetime.strptime(d, "%d.%m.%Y").timestamp()) for d in dates]
print("timestamps", ts_list)

for name, url in [
    ("pm1", f"https://13.flashscore.ninja/13/x/feed/pm_1_{pid}"),
    ("pm2", f"https://13.flashscore.ninja/13/x/feed/pm_2_{pid}"),
    ("pi1", f"https://13.flashscore.ninja/13/x/feed/pi_1_{pid}"),
    ("pi2", f"https://13.flashscore.ninja/13/x/feed/pi_2_{pid}"),
    ("pnf", f"https://13.flashscore.ninja/13/x/feed/pnf_{pid}"),
    ("global_pm", f"https://global.flashscore.ninja/2/x/feed/pm_1_{pid}"),
]:
    t = c._get_text(url)
    hits = [ts for ts in ts_list if str(ts) in t]
    print(name, "len", len(t), "ts hits", hits)
    if hits:
        for ts in hits:
            idx = t.find(str(ts))
            print(" context", repr(t[idx - 80 : idx + 120]))

# dump unique keys in pm1
from tennisAgents.dataflows.flashscore_scraper.parser import _split_rows, _parse_cells

text = c._get_text(f"https://13.flashscore.ninja/13/x/feed/pm_1_{pid}")
keys = set()
for cells in _split_rows(text):
    data = _parse_cells(cells)
    keys.update(data.keys())
print("pm1 keys", sorted(keys))
