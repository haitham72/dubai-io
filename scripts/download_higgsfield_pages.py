import json
import os
import subprocess
import time
import urllib.request

out_dir = r"design\references\quest\generated"
os.makedirs(out_dir, exist_ok=True)

jobs = [
    ("page1_coding_agent", "ce60117b-3f6d-49ef-9fb9-cdf4d43218bc"),
    ("page2_creative_journey", "4785abd0-3a34-45e5-a0b2-f2c785b671ae"),
    ("page3_proactive_chat", "077cedde-7be3-442a-bf71-e4e41ba94de0"),
    ("page4_knowledge_connector", "4d0e9354-b843-4c03-978f-bb344449ba75"),
]

completed = {}

for name, jid in jobs:
    print(f"Waiting for job {name} ({jid})...")
    for attempt in range(15):
        res = subprocess.run(f"higgsfield generate get {jid} --json", shell=True, capture_output=True, text=True)
        try:
            data = json.loads(res.stdout)
            status = data.get("status")
            if status == "completed":
                url = data.get("url") or (data.get("output", [{}])[0].get("url") if isinstance(data.get("output"), list) else None)
                if not url and "results" in data:
                    url = data["results"][0].get("url")
                # Fallback parse from table text if json key is different
                if not url:
                    # check table format
                    res_table = subprocess.run(f"higgsfield generate get {jid}", shell=True, capture_output=True, text=True)
                    for line in res_table.stdout.splitlines():
                        if "http" in line:
                            parts = line.split()
                            for p in parts:
                                if p.startswith("http"):
                                    url = p
                print(f"  [DONE] {name}: {url}")
                if url:
                    dest_file = os.path.join(out_dir, f"{name}.png")
                    urllib.request.urlretrieve(url, dest_file)
                    print(f"  Saved to {dest_file} ({os.path.getsize(dest_file):,} bytes)")
                    completed[name] = {"id": jid, "url": url, "path": dest_file}
                break
            elif status == "failed":
                print(f"  [FAILED] {name}: {data}")
                break
            else:
                print(f"  Status: {status}... waiting 3s")
                time.sleep(3)
        except Exception as e:
            time.sleep(3)

manifest_file = os.path.join(out_dir, "manifest.json")
with open(manifest_file, "w", encoding="utf-8") as f:
    json.dump(completed, f, indent=2)

print(f"\nAll downloaded! Manifest: {manifest_file}")
