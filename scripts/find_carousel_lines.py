with open("design/demo/quest_memory_management_mockup.html", "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if ".carousel-card-item" in line or ".horizontal-scroll-deck" in line or "carousel-track" in line:
        for j in range(max(0, i-5), min(len(lines), i+30)):
            print(f"L{j+1}: {lines[j]}", end="")
        break
