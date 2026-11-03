import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

for name, fname in [("Programme", "scratch/creator_programme_raw.html"), ("Agreement", "scratch/creator_agreement_raw.html")]:
    with open(fname, "r", encoding="utf-8") as f:
        text = f.read()
    print(f"=== {name} ===")
    bindings = set(re.findall(r'\{\{\s*([^}]+)\s*\}\}', text))
    print(f"Bindings ({len(bindings)}):")
    for b in sorted(bindings):
        print(f"  {b}")
    
    tags = set(re.findall(r'<sc-[a-z0-9-]+[^>]*>', text))
    print(f"sc- tags ({len(tags)}):")
    for t in sorted(tags):
        print(f"  {t}")
