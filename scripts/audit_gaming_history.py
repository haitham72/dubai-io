import sqlite3
import shutil
import tempfile
import os
import re
import json

def check_history(db_path, name):
    if not os.path.exists(db_path):
        print(f"Path does not exist: {db_path}")
        return []
    with tempfile.NamedTemporaryFile(suffix='.sqlite', delete=False) as tmp:
        tmp_name = tmp.name
    try:
        shutil.copy2(db_path, tmp_name)
        conn = sqlite3.connect(tmp_name)
        c = conn.cursor()
        query = """
            SELECT title, url, visit_count, datetime(last_visit_time/1000000-11644473600, 'unixepoch') as dt
            FROM urls
            WHERE title != ''
            ORDER BY last_visit_time DESC
            LIMIT 50000
        """
        c.execute(query)
        rows = c.fetchall()
        print(f"=== {name}: Total URLs fetched: {len(rows)} ===")
        gaming_terms = [
            'steam', 'steampowered', 'playstation', 'ps5', 'ps4', 'xbox', 'nintendo', 'epicgames',
            'ubisoft', 'blizzard', 'battlenet', 'rockstar', 'gta', 'witcher', 'cyberpunk',
            'elden ring', 'fromsoftware', 'dark souls', 'bloodborne', 'sekiro', 'monster hunter',
            'resident evil', 'silent hill', 'final fantasy', 'zelda', 'mario', 'pokemon', 'genshin',
            'honkai', 'wuthering', 'black myth', 'wukong', 'valorant', 'league of legends', 'dota',
            'overwatch', 'apex legends', 'fortnite', 'call of duty', 'warzone', 'battlefield',
            'destiny', 'game pass', 'ign.com', 'gamespot', 'kotaku', 'pcgamer', 'eurogamer',
            'gematsu', 'nexusmods', 'moddb', 'emulator', 'rpcs3', 'yuzu', 'ryujinx', 'retroarch',
            'gameplay', 'walkthrough', 'gamepass', 'gaming', 'switch 2'
        ]
        
        found = []
        for r in rows:
            title, url, visits, dt = r
            combined = (title + " " + url).lower()
            for t in gaming_terms:
                if re.search(r'\b' + re.escape(t) + r'\b', combined):
                    found.append({'time': dt, 'title': title, 'url': url, 'visits': visits, 'matched': t})
                    break
        print(f"  Found {len(found)} gaming matches in {name}!")
        for f in found[:30]:
            print(f"    [{f['time']}] (term={f['matched']}) {f['title'][:70]} | {f['url'][:60]}")
        conn.close()
        return found
    finally:
        if os.path.exists(tmp_name):
            try:
                os.remove(tmp_name)
            except Exception:
                pass

p6 = os.path.expandvars(r'%LOCALAPPDATA%\Google\Chrome\User Data\Profile 6\History')
p7 = os.path.expandvars(r'%LOCALAPPDATA%\Google\Chrome\User Data\Profile 7\History')
edge = os.path.expandvars(r'%LOCALAPPDATA%\Microsoft\Edge\User Data\Default\History')

f6 = check_history(p6, "Chrome Profile 6")
f7 = check_history(p7, "Chrome Profile 7")
fe = check_history(edge, "Edge Default")

all_gaming = f6 + f7 + fe
with open("data/sync/gaming_history_extracted.json", "w", encoding="utf-8") as out:
    json.dump(all_gaming, out, indent=2, ensure_ascii=False)
print(f"Total all gaming extracted: {len(all_gaming)}")
