import json
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

for fpath, out_name in [
    (r"C:/Users/Owner/.gemini/antigravity/brain/ed7dcfb3-b12d-4492-9ba4-972f4f3e3a50/scratch/unpacked_pages/6_Lavoo_Creator_Programme.html", "creator_programme_raw.html"),
    (r"C:/Users/Owner/.gemini/antigravity/brain/ed7dcfb3-b12d-4492-9ba4-972f4f3e3a50/scratch/unpacked_pages/11_Lavoo_Creator_Agreement.html", "creator_agreement_raw.html")
]:
    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()
    m_template = re.search(r'<script[^>]*type=["\']__bundler/template["\'][^>]*>(.*?)</script>', text, re.DOTALL)
    tmpl = json.loads(m_template.group(1))
    
    # Save raw template to scratch for inspection
    out_path = f"scratch/{out_name}"
    with open(out_path, "w", encoding="utf-8") as out:
        out.write(tmpl)
    print(f"Saved {out_path} ({len(tmpl)} chars)")
