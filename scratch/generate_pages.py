import re
import json
import base64
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

raw_prog_path = "scratch/creator_programme_raw.html"
raw_agree_path = "scratch/creator_agreement_raw.html"

with open(raw_prog_path, "r", encoding="utf-8") as f:
    prog_tmpl = f.read()

with open(raw_agree_path, "r", encoding="utf-8") as f:
    agree_tmpl = f.read()

with open("scratch/programme.css", "r", encoding="utf-8") as f:
    prog_css = f.read()

with open("scratch/agreement.css", "r", encoding="utf-8") as f:
    agree_css = f.read()

print(f"Loaded prog_tmpl ({len(prog_tmpl)} chars) and agree_tmpl ({len(agree_tmpl)} chars)")
