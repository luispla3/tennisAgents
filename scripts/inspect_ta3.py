import re
import requests

slug = "StanWawrinka"
js = requests.get(
    f"https://www.tennisabstract.com/jsfrags/{slug}.js",
    headers={"User-Agent": "Mozilla/5.0"},
    timeout=15,
).text

for section in ["career-splits", "head-to-head", "Career Splits", "Head-to-Head", "h2h", "splits"]:
    print(section, js.lower().find(section.lower()))

# Find all h1/h2 section headers in player_frag
headers = re.findall(r'<h1 id="([^"]+)"', js)
print("h1 ids:", headers)

# career splits table id
for tid in re.findall(r'id="([^"]+)"', js):
    if "split" in tid.lower() or "h2h" in tid.lower() or "head" in tid.lower():
        print("table id:", tid)
