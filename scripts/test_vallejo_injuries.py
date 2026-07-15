import importlib.util
import sys
import types

sys.path.insert(0, ".")
for pkg in ["tennisAgents", "tennisAgents.dataflows", "tennisAgents.dataflows.flashscore_scraper"]:
    sys.modules.setdefault(pkg, types.ModuleType(pkg))

spec = importlib.util.spec_from_file_location("client", "tennisAgents/dataflows/flashscore_scraper/client.py")
client_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(client_mod)
c = client_mod.FlashscoreClient(locale="es")

pid = "U5RiWEZu"
pm = c.get_player_meta(pid)
print("slug search", __import__("re").search(r"/player/[^|]+", pm).group(0))
html = c._get_text("https://www.flashscore.es/jugador/vallejo-adolfo-daniel/U5RiWEZu/")
print("injury_history in html", "injury_history" in html)
idx = html.find('"injury_history"')
print(html[idx : idx + 800])
