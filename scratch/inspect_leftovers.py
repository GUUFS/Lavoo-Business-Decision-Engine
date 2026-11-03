import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open(r"c:\Users\Owner\dev\projects\lavoo\lavoo-founder\public\index.html", "r", encoding="utf-8") as f:
    prog = f.read()

for m in re.finditer(r'\{\{\s*curName\s*\}\}', prog):
    start = max(0, m.start() - 60)
    end = min(len(prog), m.end() + 60)
    print("Prog {{ curName }} context:\n", prog[start:end])

with open(r"c:\Users\Owner\dev\projects\lavoo\lavoo-founder\public\creator-agreement.html", "r", encoding="utf-8") as f:
    agree = f.read()

for m in re.finditer(r'65d2e99b-ba67-4f52-9329-569fb5317c60', agree):
    start = max(0, m.start() - 60)
    end = min(len(agree), m.end() + 60)
    print("Agree UUID context:\n", agree[start:end])

toc_m = re.search(r'(<div class="toc-mobile.*?</div>\s*</div>)', agree, re.DOTALL)
if toc_m:
    print("Agree TOC context:\n", toc_m.group(1)[:400])
else:
    print("Agree TOC regex didn't match!")
