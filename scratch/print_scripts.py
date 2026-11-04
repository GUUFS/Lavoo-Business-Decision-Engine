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
    
    scripts = re.findall(r'<script[^>]*>(.*?)</script>', tmpl, re.DOTALL)
    print(f"==================== {name} Scripts ====================")
    for idx, s in enumerate(scripts):
        if len(s.strip()) > 0:
            print(f"--- Script {idx+1} ---")
            print(s.strip())
