import json
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

for fpath, name in [
    (r"C:/Users/Owner/.gemini/antigravity/brain/ed7dcfb3-b12d-4492-9ba4-972f4f3e3a50/scratch/unpacked_pages/6_Lavoo_Creator_Programme.html", "Creator Programme"),
    (r"C:/Users/Owner/.gemini/antigravity/brain/ed7dcfb3-b12d-4492-9ba4-972f4f3e3a50/scratch/unpacked_pages/11_Lavoo_Creator_Agreement.html", "Creator Agreement")
]:
    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()
    m_template = re.search(r'<script[^>]*type=["\']__bundler/template["\'][^>]*>(.*?)</script>', text, re.DOTALL)
    m_manifest = re.search(r'<script[^>]*type=["\']__bundler/manifest["\'][^>]*>(.*?)</script>', text, re.DOTALL)
    print(f"=== {name} ===")
    if m_template:
        tmpl = json.loads(m_template.group(1))
        print("Template length:", len(tmpl))
        title_m = re.search(r'<title>(.*?)</title>', tmpl, re.I)
        print("Title:", title_m.group(1) if title_m else "None")
    if m_manifest:
        manifest = json.loads(m_manifest.group(1))
        print("Manifest entries:", len(manifest))
