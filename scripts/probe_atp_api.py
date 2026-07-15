import json
import requests

BASE = "https://edx.atptour.com"
HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}

def try_get(url, params=None):
    r = requests.get(url, headers=HEADERS, params=params, timeout=20)
    print("\n===", url, params, "===")
    print("status", r.status_code, "type", r.headers.get("content-type", "")[:50])
    text = r.text[:2000]
    print(text)
    return r

# Player search
for params in [
    {"name": "Lorenzo Sonego"},
    {"search": "Lorenzo Sonego"},
    {"query": "Sonego"},
    {"playerName": "Sonego"},
]:
    try_get(f"{BASE}/-/www/players/find/byname", params)

try_get(f"{BASE}/-/www/h2h", {"playerId1": "d875", "playerId2": "bt72"})
try_get(f"{BASE}/-/www/h2h", {"player1Id": "d875", "player2Id": "bt72"})
try_get(f"{BASE}/-/www/h2h/d875/bt72")
