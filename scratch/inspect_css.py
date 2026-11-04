import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open("scratch/creator_programme_raw.html", "r", encoding="utf-8") as f:
    text = f.read()

# Extract styles
styles = re.findall(r'<style[^>]*>(.*?)</style>', text, re.DOTALL)
print(f"Total style tags: {len(styles)}")
for idx, s in enumerate(styles):
    # filter out font-face
    s_clean = re.sub(r'@font-face\s*\{[^}]*\}', '', s)
    if len(s_clean.strip()) > 50:
        print(f"--- Style {idx+1} (len {len(s_clean)}) ---")
        print(s_clean[:1200].strip())

# Check images or SVGs
imgs = re.findall(r'<img[^>]*src=["\']([^"\']+)["\']', text)
print("Image sources:", imgs)
svgs = re.findall(r'<svg[^>]*>', text)
print(f"Total SVGs: {len(svgs)}")
