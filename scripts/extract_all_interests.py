import sqlite3
import shutil
import tempfile
import os
import json
import re
from urllib.parse import urlparse

p6 = os.path.expandvars(r'%LOCALAPPDATA%\Google\Chrome\User Data\Profile 6\History')

with tempfile.NamedTemporaryFile(suffix='.sqlite', delete=False) as tmp:
    tmp_name = tmp.name

try:
    shutil.copy2(p6, tmp_name)
    conn = sqlite3.connect(tmp_name)
    c = conn.cursor()
    c.execute("""
        SELECT url, title, visit_count, datetime(last_visit_time/1000000-11644473600, 'unixepoch') as dt
        FROM urls
        WHERE title != ''
        ORDER BY last_visit_time DESC
        LIMIT 50000
    """)
    rows = c.fetchall()
    
    # Categorization buckets
    interests = {
        "gaming": [],
        "great_learning": [],
        "design_creative": [],
        "llm_benchmarks": [],
        "career_jobs": [],
        "shopping_hardware": []
    }
    
    for r in rows:
        url, title, visits, dt = r
        u_lower = url.lower()
        t_lower = title.lower()
        comb = t_lower + " " + u_lower
        
        # 1. Gaming
        if any(k in comb for k in [
            'steam', 'rockstar', 'gta', 'ps5', 'playstation', 'league of legends',
            'moon sweepers', 'that damn grass', 'wukong', 'cyberpunk', 'gameplay',
            'call of duty', 'dubaigaming', 'crimson desert', 'wolverine'
        ]):
            interests["gaming"].append({"title": title, "url": url, "visits": visits, "time": dt})
            
        # 2. Great Learning
        if 'mygreatlearning' in comb or 'olympus' in comb:
            interests["great_learning"].append({"title": title, "url": url, "visits": visits, "time": dt})
            
        # 3. Design & Creative
        if any(k in comb for k in ['figma', 'affectui', 'higgsfield', 'canva', 'ui/ux', 'design system']):
            interests["design_creative"].append({"title": title, "url": url, "visits": visits, "time": dt})
            
        # 4. LLM Benchmarking & Research
        if any(k in comb for k in ['artificialanalysis', 'langsmith', 'smith.langchain', 'colab.research', 'huggingface']):
            interests["llm_benchmarks"].append({"title": title, "url": url, "visits": visits, "time": dt})
            
        # 5. Career & Jobs
        if any(k in comb for k in ['linkedin.com/jobs', 'naukrigulf', 'indeed', 'talentgrator', 'onelink']):
            interests["career_jobs"].append({"title": title, "url": url, "visits": visits, "time": dt})
            
        # 6. Shopping & Hardware
        if any(k in comb for k in ['amazon.ae', 'dubizzle.com', 'sharaf dg', 'qd oled', 'iphone 16', 'trade-in']):
            interests["shopping_hardware"].append({"title": title, "url": url, "visits": visits, "time": dt})

    summary = {k: {"count": len(v), "sample": v[:15]} for k, v in interests.items()}
    print("Categorized Interest Counts:")
    for k, v in summary.items():
        print(f"  {k:20s}: {v['count']} records")

    with open("data/sync/user_interests_deep.json", "w", encoding="utf-8") as out:
        json.dump(interests, out, indent=2, ensure_ascii=False)
        
    conn.close()
finally:
    if os.path.exists(tmp_name):
        try:
            os.remove(tmp_name)
        except:
            pass
