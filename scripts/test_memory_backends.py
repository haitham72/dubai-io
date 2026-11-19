import json
import subprocess
import sys

def inspect_pip_show(package):
    res = subprocess.run([sys.executable, "-m", "pip", "show", package], capture_output=True, text=True)
    return res.stdout

print("Installed mem0ai info:")
print(inspect_pip_show("mem0ai"))
