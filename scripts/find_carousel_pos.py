with open("design/demo/quest_memory_management_mockup.html", "r", encoding="utf-8") as f:
    text = f.read()

pos = text.find(".categorized-carousel")
print("Position:", pos)
if pos != -1:
    print(repr(text[pos:pos+500]))
