import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

for name, fname in [("Programme", "scratch/creator_programme_raw.html"), ("Agreement", "scratch/creator_agreement_raw.html")]:
    with open(fname, "r", encoding="utf-8") as f:
        text = f.read()
    print(f"=== {name} ===")
    for m in re.finditer(r'<sc-if\s+value=["\']\{\{\s*(\w+)\s*\}\}["\'][^>]*>(.*?)</sc-if>', text, re.DOTALL):
        val_name = m.group(1)
        inner = m.group(2)
        print(f"--- sc-if: {val_name} ---")
        print(inner.strip()[:400])
