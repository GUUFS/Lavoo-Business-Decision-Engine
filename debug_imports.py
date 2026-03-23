import sys
import os

print(f"Python executable: {sys.executable}")
print(f"Current working directory: {os.getcwd()}")
print("Python path:")
for p in sys.path:
    print(f"  - {p}")

try:
    import api
    print("✅ Successfully imported 'api'")
except ImportError as e:
    print(f"❌ Failed to import 'api': {e}")

try:
    from api import main
    print("✅ Successfully imported 'api.main'")
except ImportError as e:
    print(f"❌ Failed to import 'api.main': {e}")
