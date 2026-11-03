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
    tmpl = json.loads(m_template.group(1))
    
    # Strip <helmet>...</helmet>
    tmpl_clean = re.sub(r'<helmet>.*?</helmet>', '', tmpl, flags=re.DOTALL)
    print(f"==================== {name} ====================")
    lines = [l for l in tmpl_clean.split('\n') if l.strip()]
    for l in lines[:60]:
        print(l[:120])
