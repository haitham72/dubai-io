with open("design/demo/quest_memory_management_mockup.html", "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "switchMainTab" in line or "bottom-dock" in line or "dock-item" in line or "main-tab" in line:
        print(f"L{i+1}: {line.strip()[:100]}")
