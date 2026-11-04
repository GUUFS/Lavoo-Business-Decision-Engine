import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

for name, fname in [("Programme", "scratch/creator_programme_raw.html"), ("Agreement", "scratch/creator_agreement_raw.html")]:
    with open(fname, "r", encoding="utf-8") as f:
        text = f.read()
    print(f"==================== {name} Sections ====================")
    sections = re.findall(r'(<(?:header|section|footer)[^>]*>.*?</(?:header|section|footer)>)', text, re.DOTALL)
    print(f"Found {len(sections)} major blocks")
    for idx, s in enumerate(sections):
        tag_m = re.match(r'<(\w+)([^>]*)>', s)
        tag_name = tag_m.group(1)
        attrs = tag_m.group(2)
        # find id or class or first heading
        h = re.search(r'<h[1-6][^>]*>(.*?)</h[1-6]>', s, re.DOTALL)
        h_text = re.sub(r'<[^>]+>', '', h.group(1)).strip() if h else "No heading"
        id_m = re.search(r'id=["\']([^"\']+)["\']', attrs)
        cls_m = re.search(r'class=["\']([^"\']+)["\']', attrs)
        print(f"[{idx+1}] <{tag_name}> id='{id_m.group(1) if id_m else ''}' class='{cls_m.group(1) if cls_m else ''}' | Heading: {h_text[:60]}")
