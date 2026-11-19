import sqlite3
import shutil
import tempfile
import os
from collections import Counter
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
        ORDER BY last_visit_time DESC
        LIMIT 50000
    """)
    rows = c.fetchall()
    print(f"Total rows: {len(rows)}")

    domains = Counter()
    for r in rows:
        url = r[0]
        try:
            domain = urlparse(url).netloc
            domains[domain] += 1
        except Exception:
            pass

    print("\nTop 30 Domains visited:")
    for d, cnt in domains.most_common(30):
        print(f"  {d:35s}: {cnt}")

    conn.close()
finally:
    if os.path.exists(tmp_name):
        try:
            os.remove(tmp_name)
        except:
            pass
