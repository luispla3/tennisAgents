import json
import requests

GATEWAY = "https://app.atptour.com/api/v2/gateway"
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
    "Content-Type": "application/json",
}

payloads = [
    {"operationName": "searchPlayers", "variables": {"searchTerm": "Sonego"}},
    {"query": "searchPlayers", "searchTerm": "Sonego"},
    {"searchTerm": "Sonego"},
    {"name": "Sonego"},
]

for p in payloads:
    for method in ["POST", "GET"]:
        try:
            r = requests.request(method, GATEWAY, headers=HEADERS, json=p if method == "POST" else None, params=p if method == "GET" else None, timeout=20)
            print(method, p, "->", r.status_code, r.text[:500])
        except Exception as e:
            print(method, p, "ERR", e)

# Try direct player find patterns on app.atptour.com
for url in [
    "https://app.atptour.com/api/v2/players/search?query=Sonego",
    "https://app.atptour.com/api/v2/players/find?searchTerm=Sonego",
    "https://app.atptour.com/api/v2/player/search/Sonego",
]:
    r = requests.get(url, headers=HEADERS, timeout=20)
    print(url, r.status_code, r.text[:400])
