with open("design/demo/quest_memory_management_mockup.html", "r", encoding="utf-8") as f:
    html = f.read()

# Replace variables
html = html.replace("--bg-canvas: #F5F3EC;", "--bg-canvas: #FFFFFF;")
html = html.replace("--bg-inset: #F0EDE4;", "--bg-inset: #F7F8FA;")
html = html.replace("--bg-card-subtle: #FDFBF7;", "--bg-card-subtle: #FAFAFB;")

old_block = """.categorized-carousel {
    display: flex;
    gap: 12px;
    overflow-x: auto;
    padding-bottom: 6px;
    scrollbar-width: none;
  }
  .categorized-carousel::-webkit-scrollbar {
    display: none;
  }
  .carousel-card-item {
    flex: 0 0 185px;
    background: var(--bg-card);
    border-radius: var(--radius-md);
    padding: 12px;
    border: 1px solid var(--border-subtle);
    box-shadow: 0 4px 14px rgba(28, 26, 23, 0.04);
    cursor: pointer;
    transition: transform 0.15s ease;
  }
  .carousel-card-item:active {
    transform: scale(0.975);
  }
  .carousel-card-media {
    width: 100%;
    height: 90px;
    border-radius: var(--radius-sm);
    overflow: hidden;
    background: var(--bg-inset);
    margin-bottom: 8px;
    position: relative;
  }"""

new_block = """.categorized-carousel {
    display: flex;
    gap: 16px;
    overflow-x: auto;
    scroll-snap-type: x mandatory;
    margin: 0 -20px;
    padding: 4px 20px 18px 20px;
    scrollbar-width: none;
  }
  .categorized-carousel::-webkit-scrollbar {
    display: none;
  }
  /* 1 card prominent (78% width) with next card peeking to imply horizontal swipe */
  .carousel-card-item {
    flex: 0 0 78%;
    max-width: 300px;
    scroll-snap-align: start;
    background: #FFFFFF;
    border-radius: 24px;
    padding: 14px;
    border: 1px solid rgba(0, 0, 0, 0.07);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.06);
    cursor: pointer;
    transition: transform 0.15s ease, box-shadow 0.15s ease;
  }
  .carousel-card-item:active {
    transform: scale(0.98);
  }
  /* Vertical 3:4 aspect ratio hero media */
  .carousel-card-media {
    width: 100%;
    height: 220px;
    aspect-ratio: 3 / 4;
    border-radius: 18px;
    overflow: hidden;
    background: #F7F8FA;
    margin-bottom: 12px;
    position: relative;
  }"""

if old_block in html:
    html = html.replace(old_block, new_block)
    print("Successfully replaced with 1-card peeking 3:4 carousel!")
else:
    print("Match failed. Inspecting slice around 8029:")
    print(repr(html[8029:8029+len(old_block)]))

with open("design/demo/quest_memory_management_mockup.html", "w", encoding="utf-8") as f:
    f.write(html)
