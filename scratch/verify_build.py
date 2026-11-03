import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

for fname in [
    r"c:\Users\Owner\dev\projects\lavoo\lavoo-founder\public\index.html",
    r"c:\Users\Owner\dev\projects\lavoo\lavoo-founder\public\creator-agreement.html"
]:
    with open(fname, "r", encoding="utf-8") as f:
        content = f.read()
    
    print(f"=== Verifying {fname} ===")
    leftover_bindings = re.findall(r'\{\{\s*[^}]+\s*\}\}', content)
    print(f"Leftover {{ ... }} bindings: {len(leftover_bindings)}")
    if leftover_bindings:
        print("  Found:", leftover_bindings[:10])
    
    sc_tags = re.findall(r'<sc-[a-z0-9-]+[^>]*>', content)
    print(f"Leftover <sc-...> tags: {len(sc_tags)}")
    if sc_tags:
        print("  Found:", sc_tags[:10])

    uuid_matches = re.findall(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', content)
    print(f"UUID asset references remaining: {len(uuid_matches)}")
    if uuid_matches:
        print("  Found:", uuid_matches[:10])
