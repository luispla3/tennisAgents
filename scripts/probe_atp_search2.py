import requests

BASE = "https://edx.atptour.com"
HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json, text/plain, */*"}

# H2H endpoint variants
for url in [
    f"{BASE}/en/-/www/h2h/d875/bt72",
    f"{BASE}/-/www/h2h/d875/bt72",
    f"{BASE}/en/-/www/h2h/M0CI/HB71",
]:
    r = requests.get(url, headers=HEADERS, timeout=20)
    print(url, r.status_code, r.headers.get("content-type", "")[:40], r.text[:120])

# Player search POST variants
search_url = f"{BASE}/en/-/www/players/find/byname"
payloads = [
    {"searchText": "Sonego"},
    "Sonego",
    {"query": "Sonego"},
]
for p in payloads:
    for headers in [
        HEADERS,
        {**HEADERS, "Content-Type": "application/json"},
        {**HEADERS, "Content-Type": "application/x-www-form-urlencoded"},
    ]:
        if isinstance(p, str):
            r = requests.post(search_url, headers=headers, data=p, timeout=20)
        else:
            r = requests.post(search_url, headers=headers, json=p, timeout=20)
        ctype = r.headers.get("content-type", "")
        if "json" in ctype:
            print("POST HIT", p, headers.get("Content-Type"), r.text[:500])
        elif "404" not in r.text[:200]:
            print("POST", p, headers.get("Content-Type"), ctype, r.text[:80])

# GET with path suffix
for suffix in ["Sonego", "lorenzo-sonego", "Collignon"]:
    r = requests.get(f"{search_url}/{suffix}", headers=HEADERS, timeout=20)
    if "json" in r.headers.get("content-type", ""):
        print("GET suffix", suffix, r.text[:500])
