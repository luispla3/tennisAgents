import importlib.util
import re

spec = importlib.util.spec_from_file_location("client", "tennisAgents/dataflows/flashscore_scraper/client.py")
client_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(client_mod)
c = client_mod.FlashscoreClient(locale="es")
js = c._get_text("https://www.flashscore.es/res/_fs/build/teamPage.client.05ca532.js")

# Extract module 23277 area - team page provider with fetcher
idx = js.find("23277(e,t,s)")
print("module start", idx)
print(js[idx : idx + 8000])
