import re
import requests

html = requests.get(
    "https://edx.atptour.com/en/h2h",
    headers={"User-Agent": "Mozilla/5.0"},
    timeout=30,
).text
print("len", len(html))

for pat in ["PlayerSearch", "H2H", "head-2-head", "playerId", "SearchPlayer", "autocomplete", "GetH2H"]:
    print(pat, "count", len(re.findall(pat, html, re.I)))

for m in re.finditer(r"/[-~][^\"'\s<>]+", html):
    s = m.group(0)
    if any(k in s.lower() for k in ["h2h", "player", "search"]):
        print("path", s[:100])

# ng-app / angular data
for m in re.finditer(r"https?://[^\"'\s<>]+", html):
    u = m.group(0)
    if any(k in u.lower() for k in ["h2h", "player", "search", "api"]):
        print("url", u[:140])
