import json
import re
import requests

html = requests.get(
    "https://edx.atptour.com/en/h2h",
    headers={"User-Agent": "Mozilla/5.0"},
    timeout=30,
).text

patterns = [
    r"/-/www/[^\"'\s<>]+",
    r"api/v2/[^\"'\s<>]+",
    r"findPlayer[^\"'\s<>]{0,80}",
    r"searchPlayer[^\"'\s<>]{0,80}",
]
found = set()
for pat in patterns:
    for m in re.finditer(pat, html, re.I):
        found.add(m.group(0)[:120])

for item in sorted(found):
    if any(k in item.lower() for k in ["player", "h2h", "search", "find", "gateway"]):
        print(item)

# Full h2h json structure
r = requests.get(
    "https://edx.atptour.com/-/www/h2h/d875/bt72",
    headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"},
    timeout=20,
)
data = r.json()
print("\nTournaments sample:")
print(json.dumps(data.get("Tournaments", [])[:2], indent=2)[:2500])
print("\nOtherTournaments sample:")
print(json.dumps(data.get("OtherTournaments", [])[:2], indent=2)[:1500])
