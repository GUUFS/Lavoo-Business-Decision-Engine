import json
import re
import base64
import gzip
import sys

sys.stdout.reconfigure(encoding='utf-8')

file_path = r"C:/Users/Owner/.gemini/antigravity/brain/ed7dcfb3-b12d-4492-9ba4-972f4f3e3a50/scratch/unpacked_pages/6_Lavoo_Creator_Programme.html"

with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
    text = f.read()

m_manifest = re.search(r'<script[^>]*type=["\']__bundler/manifest["\'][^>]*>(.*?)</script>', text, re.DOTALL)
manifest = json.loads(m_manifest.group(1))

for uuid, entry in manifest.items():
    raw_b64 = entry.get("data", "")
    is_comp = entry.get("compressed", False)
    content_type = entry.get("type", "")
    data_bytes = base64.b64decode(raw_b64)
    if is_comp:
        data_bytes = gzip.decompress(data_bytes)
    
    first_bytes = data_bytes[:50]
    print(f"UUID: {uuid}")
    print(f"  Type: {content_type}, Comp: {is_comp}, Size: {len(data_bytes)} bytes")
    try:
        preview = data_bytes.decode('utf-8')[:100].replace('\n', ' ')
        print(f"  Text preview: {preview}")
    except Exception:
        print(f"  Binary preview: {first_bytes}")
