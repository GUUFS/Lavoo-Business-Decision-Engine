import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open("scratch/creator_programme_raw.html", "r", encoding="utf-8") as f:
    text = f.read()

calc_m = re.search(r'(<section id="calculator".*?</section>)', text, re.DOTALL)
if calc_m:
    print(calc_m.group(1))
