import os

paths = [
    r"G:\Haitham\lab-data\hindsight-info",
    r"G:\Haitham\lab-data\comparison\hs_stub\hindsight_api",
    r"G:\Haitham\lab-data\mamty-hindsight"
]

for p in paths:
    print(f"=== {p} ===")
    if os.path.exists(p):
        for item in os.listdir(p):
            sub = os.path.join(p, item)
            is_dir = os.path.isdir(sub)
            kind = "DIR" if is_dir else "FILE"
            size = os.path.getsize(sub) if not is_dir else 0
            print(f"  [{kind}] {item} ({size} bytes)")
