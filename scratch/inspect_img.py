import json
import re
import base64
import sys

sys.stdout.reconfigure(encoding='utf-8')

file_path = r"C:/Users/Owner/.gemini/antigravity/brain/ed7dcfb3-b12d-4492-9ba4-972f4f3e3a50/scratch/unpacked_pages/6_Lavoo_Creator_Programme.html"

with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
    text = f.read()

m_manifest = re.search(r'<script[^>]*type=["\']__bundler/manifest["\'][^>]*>(.*?)</script>', text, re.DOTALL)
manifest = json.loads(m_manifest.group(1))

img_uuid = "fcb366f7-70de-4e95-9e2f-f78c0dda4cf3"
if img_uuid in manifest:
    raw_b64 = manifest[img_uuid]["data"]
    img_data = base64.b64decode(raw_b64)
    with open("scratch/logo_or_img.png", "wb") as f_out:
        f_out.write(img_data)
    print(f"Saved scratch/logo_or_img.png ({len(img_data)} bytes)")

m_template = re.search(r'<script[^>]*type=["\']__bundler/template["\'][^>]*>(.*?)</script>', text, re.DOTALL)
tmpl = json.loads(m_template.group(1))

# Find the context where img_uuid is used
for m in re.finditer(re.escape(img_uuid), tmpl):
    start = max(0, m.start() - 100)
    end = min(len(tmpl), m.end() + 100)
    print("Context:\n", tmpl[start:end])
