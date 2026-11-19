import sqlite3, os, tempfile, shutil

chrome_hist_path = r"C:\Users\h.ibrahim\AppData\Local\Google\Chrome\User Data\Profile 6\History"
tmp_hist = os.path.join(tempfile.gettempdir(), "Chrome_Hist_Check_HF.db")
shutil.copy2(chrome_hist_path, tmp_hist)
conn = sqlite3.connect(tmp_hist)
cur = conn.cursor()
cur.execute("SELECT url, title FROM urls WHERE url LIKE '%higgsfield%' OR title LIKE '%higgsfield%' OR url LIKE '%flare%' ORDER BY id DESC LIMIT 20")
rows = cur.fetchall()
conn.close()

print(f"Found {len(rows)} Higgsfield/Flare rows in Chrome History:")
for r in rows:
    print(f"  {r[1]} -> {r[0]}")
