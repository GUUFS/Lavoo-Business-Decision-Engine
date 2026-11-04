import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

for name, fname, out_css in [
    ("Programme", "scratch/creator_programme_raw.html", "scratch/programme.css"),
    ("Agreement", "scratch/creator_agreement_raw.html", "scratch/agreement.css")
]:
    with open(fname, "r", encoding="utf-8") as f:
        text = f.read()
    styles = re.findall(r'<style[^>]*>(.*?)</style>', text, re.DOTALL)
    combined = []
    for s in styles:
        s_clean = re.sub(r'@font-face\s*\{[^}]*\}', '', s).strip()
        if s_clean:
            combined.append(s_clean)
    with open(out_css, "w", encoding="utf-8") as out:
        out.write("\n\n/* ------------------------- */\n\n".join(combined))
    print(f"Wrote {out_css} ({len(combined)} blocks)")
