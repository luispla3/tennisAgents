import json
import requests

BASE = "https://edx.atptour.com"
HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}

def try_req(method, url, **kwargs):
    r = requests.request(method, url, headers=HEADERS, timeout=20, **kwargs)
    print("\n===", method, url, kwargs.get("params"), kwargs.get("json"), "===")
    print("status", r.status_code, r.headers.get("content-type", "")[:60])
    print(r.text[:1500])

# Player search variants
paths = [
    "/-/www/players/find/byname/Sonego",
    "/-/www/players/find/byname?searchTerm=Sonego",
    "/-/www/players/find/byname?searchString=Sonego",
    "/-/www/players/find/byname?term=Sonego",
    "/-/www/players/find/byname?query=Sonego",
    "/-/www/players/search/Sonego",
    "/-/www/players/search?query=Sonego",
    "/-/www/playersearch/Sonego",
]
for p in paths:
    try_req("GET", BASE + p)

try_req("POST", BASE + "/-/www/players/find/byname", json={"searchTerm": "Sonego"})
try_req("POST", BASE + "/-/www/players/find/byname", data={"searchTerm": "Sonego"})

# Full H2H JSON sample
r = requests.get(f"{BASE}/-/www/h2h/d875/bt72", headers=HEADERS, timeout=20)
data = r.json()
print("\nkeys", data.keys())
print("events", len(data.get("Events") or data.get("events") or []))
for k in data:
    if k.lower().startswith("event") or "match" in k.lower():
        print(k, type(data[k]), str(data[k])[:200])
