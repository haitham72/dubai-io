with open("design/demo/quest_memory_management_mockup.html", "r", encoding="utf-8") as f:
    text = f.read()

import re
matches = re.findall(r'(\.carousel[^{]+{[^}]+})', text)
for m in matches[:5]:
    print(m)
