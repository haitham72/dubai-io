import mem0
from mem0 import Memory

print(f"mem0 version: {mem0.__version__ if hasattr(mem0, '__version__') else 'unknown'}")

# Check default config and providers
import inspect
print("Memory __init__ signature:")
print(inspect.signature(Memory.__init__))
