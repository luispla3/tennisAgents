import re
import requests

html = requests.get(
    "https://edx.atptour.com/en/h2h",
    headers={"User-Agent": "Mozilla/5.0"},
    timeout=30,
).text

scripts = re.findall(r'<script[^>]+src="([^"]+)"', html)
for s in scripts:
    if any(k in s.lower() for k in ["h2h", "head", "player", "atp"]):
        print("script", s)

# hidden inputs
for m in re.finditer(r'<input[^>]+class="atp_[^"]+"[^>]*>', html):
    print(m.group(0)[:200])

# download likely bundle
for s in scripts:
    if "head" in s.lower() or "h2h" in s.lower():
        url = s if s.startswith("http") else "https://edx.atptour.com" + s
        js = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30).text
        print("js len", len(js), url)
        for term in ["find/byname", "searchText", "searchPlayers", "PlayerId"]:
            i = js.find(term)
            if i >= 0:
                print(term, js[max(0,i-80):i+200])
