import re

with open("design/demo/quest_memory_management_mockup.html", "r", encoding="utf-8") as f:
    text = f.read()

tabs = re.findall(r'tab-button[^>]*>([^<]+)<', text)
print("Tab buttons:", tabs)
views = re.findall(r'id=["\']view-([^"\']+)["\']', text)
print("Views:", views)
nav = re.findall(r'<nav.*?</nav>', text, re.DOTALL)
print("Nav elements count:", len(nav))
if nav:
    print("Nav sample:", nav[0][:300])
