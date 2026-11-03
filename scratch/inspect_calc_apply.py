import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open("scratch/creator_programme_raw.html", "r", encoding="utf-8") as f:
    text = f.read()

# Let's inspect the calculator section in detail
calc_m = re.search(r'(<section[^>]*id=["\']calculator["\'][^>]*>.*?</section>)', text, re.DOTALL)
if calc_m:
    print("=== Calculator Section ===")
    print(calc_m.group(1)[:2500])

# Let's inspect the application form section
apply_m = re.search(r'(<section[^>]*id=["\']apply["\'][^>]*>.*?</section>)', text, re.DOTALL)
if apply_m:
    print("=== Apply Section ===")
    print(apply_m.group(1)[:2500])
