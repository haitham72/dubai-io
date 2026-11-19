with open("design/demo/quest_memory_management_mockup.html", "r", encoding="utf-8") as f:
    text = f.read()

import re
for m in re.finditer(r'<div class="view-panel[^"]*" id="tab-([^"]+)-content">', text):
    print(m.group(0), "at pos", m.start())
