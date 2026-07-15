import requests

BASE = "https://edx.atptour.com"
HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}

def try_url(url, params=None):
    r = requests.get(url, headers=HEADERS, params=params, timeout=20)
    print("\n", url, params)
    print("status", r.status_code, r.headers.get("content-type", "")[:50])
    print(r.text[:1200])

for params in [
    {"searchText": "Sonego"},
    {"searchTerm": "Sonego"},
    {"term": "Sonego"},
    {"name": "Lorenzo Sonego"},
    {"query": "Sonego"},
]:
    try_url(f"{BASE}/en/-/www/players/find/byname", params)

# H2H Collignon vs Sonego - need IDs first
try_url(f"{BASE}/en/-/www/players/find/byname", {"searchText": "Collignon"})
try_url(f"{BASE}/en/-/www/players/find/byname", {"searchText": "Sonego"})
