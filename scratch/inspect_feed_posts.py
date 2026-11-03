import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open("scratch/creator_programme_raw.html", "r", encoding="utf-8") as f:
    text = f.read()

# Search for feed usage
feed_m = re.search(r'(<div[^>]*class=["\']rise d4 floaty["\'].*?</div>\s*</div>\s*</div>)', text, re.DOTALL)
if feed_m:
    print("=== Hero Floating Feed ===")
    print(feed_m.group(1)[:2000])

# Search for posts usage
posts_m = re.search(r'(<section[^>]*>.*?Posts that write themselves.*?<\/section>)', text, re.DOTALL)
if posts_m:
    print("=== Posts Section ===")
    print(posts_m.group(1)[:2000])
