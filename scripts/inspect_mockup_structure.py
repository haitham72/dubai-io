import re

with open("design/demo/quest_memory_management_mockup.html", "r", encoding="utf-8") as f:
    text = f.read()

print("File size:", len(text))
# find button tags or dock elements
buttons = re.findall(r'<button[^>]*>.*?</button>', text, re.DOTALL)
print(f"Total buttons: {len(buttons)}")
for b in buttons[:10]:
    clean = re.sub(r'\s+', ' ', b).strip()
    print(" ", clean[:100])

# check switchTab or similar JS functions
funcs = re.findall(r'function\s+([a-zA-Z0-9_]+)\s*\(', text)
print("JS Functions:", funcs)
