import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open("scratch/creator_programme_raw.html", "r", encoding="utf-8") as f:
    text = f.read()

# Find all blocks with sc-for
for m in re.finditer(r'<sc-for\s+list=["\']\{\{\s*(\w+)\s*\}\}["\'][^>]*>(.*?)</sc-for>', text, re.DOTALL):
    list_name = m.group(1)
    inner = m.group(2)
    print(f"=== sc-for: {list_name} ===")
    print(inner.strip()[:600])
    print("-----------------------------------")
