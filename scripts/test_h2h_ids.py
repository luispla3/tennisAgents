import json
import requests

HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
BASE = "https://edx.atptour.com"

for ids in [("C0JP", "SU87"), ("SU87", "C0JP"), ("d875", "bt72")]:
    url = f"{BASE}/en/-/www/h2h/{ids[0]}/{ids[1]}"
    r = requests.get(url, headers=HEADERS, timeout=20)
    print("\n", url, r.status_code)
    if "json" in r.headers.get("content-type", ""):
        data = r.json()
        p1 = data["PlayerTeam1"]["PlayerFullName"]
        p2 = data["PlayerTeam2"]["PlayerFullName"]
        r1 = data["PlayerTeam1"]["Record"]
        r2 = data["PlayerTeam2"]["Record"]
        print(p1, r1, "-", p2, r2)
        print("tournaments", len(data.get("Tournaments", [])))
        if data.get("Tournaments"):
            t = data["Tournaments"][0]
            m = t["Matches"][0]
            print("sample match", t["EventYear"], t["EventName"], m["ResultString"], "winner", m["Winner"])
