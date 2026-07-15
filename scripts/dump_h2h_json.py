import json
import requests

r = requests.get(
    "https://edx.atptour.com/en/-/www/h2h/C0JP/SU87",
    headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"},
    timeout=20,
)
print(json.dumps(r.json(), indent=2)[:4000])
