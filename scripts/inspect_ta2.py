import re
import requests

html = requests.get(
    "https://www.tennisabstract.com/cgi-bin/player.cgi?p=StanWawrinka",
    headers={"User-Agent": "Mozilla/5.0"},
    timeout=15,
).text

scripts = re.findall(r'src="([^"]+\.js[^"]*)"', html)
print("scripts:", scripts)

for name in ["player_frag", "frag_menu", "recent-results", "id=\"recent"]:
    idx = html.find(name)
    if idx >= 0:
        print(name, "at", idx)
        print(repr(html[idx : idx + 300]))

# Look for embedded table HTML
if "recent-results" in html:
    idx = html.find('id="recent-results"')
    print("\nrecent-results tag:", repr(html[idx : idx + 500]))

# Search for match-like patterns
for pat in [r"<tr><td>\d{2}-", r"Wimbledon", r"Roland Garros", r"6-4"]:
    m = re.search(pat, html)
    print(pat, "->", "found" if m else "not found")
