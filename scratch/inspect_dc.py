import json
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

file_path = r"C:/Users/Owner/.gemini/antigravity/brain/ed7dcfb3-b12d-4492-9ba4-972f4f3e3a50/scratch/unpacked_pages/6_Lavoo_Creator_Programme.html"

with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
    text = f.read()

m_template = re.search(r'<script[^>]*type=["\']__bundler/template["\'][^>]*>(.*?)</script>', text, re.DOTALL)
tmpl = json.loads(m_template.group(1))

# Check for scripts inside template
scripts = re.findall(r'<script[^>]*>(.*?)</script>', tmpl, re.DOTALL)
print(f"Number of script tags inside template: {len(scripts)}")
for idx, s in enumerate(scripts):
    print(f"--- Script {idx+1} (len {len(s)}) ---")
    print(s[:300].strip())

# Check for all tags with sc-
sc_tags = set(re.findall(r'<(sc-[a-z0-9-]+|\w+\s+[^>]*sc-[a-z0-9-]+[^>]*)', tmpl))
print(f"SC tags / attributes found: {len(sc_tags)}")
for t in list(sc_tags)[:15]:
    print("  ", t[:80])
