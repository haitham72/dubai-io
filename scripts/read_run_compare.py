import os

run_compare_path = r"G:\Haitham\lab-data\comparison\run_compare.py"
if os.path.exists(run_compare_path):
    with open(run_compare_path, "r", encoding="utf-8") as f:
        code = f.read()
    print(f"run_compare.py size: {len(code)} chars, {len(code.splitlines())} lines")
    print("First 80 lines:")
    for line in code.splitlines()[:80]:
        print(line)
else:
    print("run_compare.py not found")
