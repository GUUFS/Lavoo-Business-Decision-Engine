import re
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open("scratch/creator_programme_raw.html", "r", encoding="utf-8") as f:
    prog_tmpl = f.read()

with open("scratch/creator_agreement_raw.html", "r", encoding="utf-8") as f:
    agree_tmpl = f.read()

with open("scratch/programme.css", "r", encoding="utf-8") as f:
    prog_css = f.read()

with open("scratch/agreement.css", "r", encoding="utf-8") as f:
    agree_css = f.read()

# -------------------------------------------------------------
# 1. BUILD CREATOR PROGRAMME PAGE (public/index.html)
# -------------------------------------------------------------
def build_programme_page():
    content = re.sub(r'<helmet>.*?</helmet>', '', prog_tmpl, flags=re.DOTALL)
    content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL)
    content = content.replace("<x-dc>", "").replace("</x-dc>", "")
    
    # Replace logo image uuid with local asset
    content = content.replace("fcb366f7-70de-4e95-9e2f-f78c0dda4cf3", "/assets/lavoo-logo.png")
    
    # Update navigation links
    content = content.replace('href="Creators.dc.html"', 'href="/"')
    content = content.replace('href="Creators.dc.html#calculator"', 'href="#calculator"')
    content = content.replace('href="Creators.dc.html#who"', 'href="#who"')
    content = content.replace('href="Creators.dc.html#path"', 'href="#how"')
    content = content.replace('href="CreatorTerms.dc.html"', 'href="/creator-agreement"')
    content = content.replace('href="Main.dc.html"', 'href="https://lavoo.io"')

    # Replace <sc-raw-select ...> with <select ...>
    content = re.sub(r'<sc-raw-select([^>]*)>', r'<select\1>', content)
    content = content.replace('</sc-raw-select>', '</select>')

    # Mobile menu burger toggle
    burger_replacement = '''<button type="button" class="nav-burger" aria-label="Menu" aria-expanded="false" onclick="toggleMenu()" style="background:transparent; border:0; cursor:pointer; padding:8px; display:none; align-items:center; justify-content:center; color:#1a1a1a;">
<svg id="burger-icon" aria-hidden="true" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><path id="burger-path" d="M4 9h16M4 15h16"></path></svg>
</button>'''
    content = re.sub(r'<button type="button" class="nav-burger"[^>]*>.*?</button>', burger_replacement, content, flags=re.DOTALL)

    # Mobile nav container
    mobile_nav_replacement = '''<nav id="mobile-menu" aria-label="Mobile" class="nav-mobile fadein" style="display: none; padding: 8px 20px 28px; flex-direction: column">
<a href="#worth" onclick="closeMenu()" style="font-family: Montserrat, sans-serif; font-weight: 600; font-size: 26px; color: #1a1a1a; text-decoration: none; padding: 16px 0; border-bottom: 1px solid #EDEDED">What you earn</a>
<a href="#how" onclick="closeMenu()" style="font-family: Montserrat, sans-serif; font-weight: 600; font-size: 26px; color: #1a1a1a; text-decoration: none; padding: 16px 0; border-bottom: 1px solid #EDEDED">How it works</a>
<a href="#calculator" onclick="closeMenu()" style="font-family: Montserrat, sans-serif; font-weight: 600; font-size: 26px; color: #1a1a1a; text-decoration: none; padding: 16px 0; border-bottom: 1px solid #EDEDED">Calculator</a>
<a href="#faq" onclick="closeMenu()" style="font-family: Montserrat, sans-serif; font-weight: 600; font-size: 26px; color: #1a1a1a; text-decoration: none; padding: 16px 0; border-bottom: 1px solid #EDEDED">Questions</a>
<a href="/creator-agreement" onclick="closeMenu()" style="font-family: Montserrat, sans-serif; font-weight: 600; font-size: 26px; color: #e87a02; text-decoration: none; padding: 16px 0; border-bottom: 1px solid #EDEDED">Agreement</a>
<a href="https://lavoo.io" style="font-family: Montserrat, sans-serif; font-weight: 600; font-size: 26px; color: #1a1a1a; text-decoration: none; padding: 16px 0">What is Lavoo?</a>
</nav>'''
    content = re.sub(r'<sc-if value="\{\{\s*menuOpen\s*\}\}"[^>]*>.*?</sc-if>', mobile_nav_replacement, content, flags=re.DOTALL)

    # Floating Card Feed in Hero
    feed_replacement = '''<div class="slidein" style="display: flex; align-items: center; gap: 14px; background: #141414; border: 1px solid #222222; border-radius: 18px; padding: 14px 16px; animation-delay: .9s">
<span aria-hidden="true" style="width: 40px; height: 40px; flex: 0 0 40px; border-radius: 12px; background: #262626; color: #FFFFFF; display: flex; align-items: center; justify-content: center; font-family: Montserrat, sans-serif; font-weight: 700; font-size: 14px">A</span>
<span style="flex: 1 1 auto; min-width: 0; display: flex; flex-direction: column; gap: 2px"><span style="font-family: Montserrat, sans-serif; font-weight: 600; font-size: 15px">Pro</span><span style="font-size: 13px; color: #8A8A8A">Paid monthly</span></span>
<span class="num feed-item-amt" id="feed-amt-0" style="font-family: Montserrat, sans-serif; font-weight: 700; font-size: 17px; color: #FFFFFF">₦9,302</span>
</div>
<div class="slidein" style="display: flex; align-items: center; gap: 14px; background: #141414; border: 1px solid #222222; border-radius: 18px; padding: 14px 16px; animation-delay: 1.1s">
<span aria-hidden="true" style="width: 40px; height: 40px; flex: 0 0 40px; border-radius: 12px; background: #5a3200; color: #FFFFFF; display: flex; align-items: center; justify-content: center; font-family: Montserrat, sans-serif; font-weight: 700; font-size: 14px">T</span>
<span style="flex: 1 1 auto; min-width: 0; display: flex; flex-direction: column; gap: 2px"><span style="font-family: Montserrat, sans-serif; font-weight: 600; font-size: 15px">Premium</span><span style="font-size: 13px; color: #8A8A8A">Paid monthly</span></span>
<span class="num feed-item-amt" id="feed-amt-1" style="font-family: Montserrat, sans-serif; font-weight: 700; font-size: 17px; color: #FFFFFF">₦16,279</span>
</div>
<div class="slidein" style="display: flex; align-items: center; gap: 14px; background: #141414; border: 1px solid #222222; border-radius: 18px; padding: 14px 16px; animation-delay: 1.3s">
<span aria-hidden="true" style="width: 40px; height: 40px; flex: 0 0 40px; border-radius: 12px; background: #e87a02; color: #000000; display: flex; align-items: center; justify-content: center; font-family: Montserrat, sans-serif; font-weight: 700; font-size: 14px">K</span>
<span style="flex: 1 1 auto; min-width: 0; display: flex; flex-direction: column; gap: 2px"><span style="font-family: Montserrat, sans-serif; font-weight: 600; font-size: 15px">Premium</span><span style="font-size: 13px; color: #8A8A8A">Paid yearly</span></span>
<span class="num feed-item-amt" id="feed-amt-2" style="font-family: Montserrat, sans-serif; font-weight: 700; font-size: 17px; color: #FFFFFF">₦152,093</span>
</div>'''
    content = re.sub(r'<sc-for list="\{\{\s*feed\s*\}\}"[^>]*>.*?</sc-for>', feed_replacement, content, flags=re.DOTALL)

    # 6 progress bars in "One person" section
    six_bars_1 = '''<span style="flex: 1 1 0; height: 8px; border-radius: 999px; background: #3a2000"></span>''' * 6
    six_bars_2 = '''<span style="flex: 1 1 0; height: 8px; border-radius: 999px; background: #a65800"></span>''' * 6
    content = re.sub(r'<sc-for list="\{\{\s*six\s*\}\}"[^>]*>.*?background: #3a2000.*?</sc-for>', six_bars_1, content, flags=re.DOTALL)
    content = re.sub(r'<sc-for list="\{\{\s*six\s*\}\}"[^>]*>.*?background: #a65800.*?</sc-for>', six_bars_2, content, flags=re.DOTALL)

    # 3 Posts Inspiration
    posts_replacement = '''<div class="reveal tilt" style="width: 100%; max-width: 320px; aspect-ratio: 9 / 16; background: #000000; color: #FFFFFF; border-radius: 34px; padding: 22px; display: flex; flex-direction: column; justify-content: space-between; position: relative; overflow: hidden; box-shadow: 0 40px 80px rgba(0,0,0,0.18); transform: rotate(-2deg); animation-delay: 0s">
<div aria-hidden="true" style="position: absolute; inset: auto -40% -30% -40%; height: 70%; background: radial-gradient(closest-side, rgba(232,122,2,0.35), rgba(232,122,2,0)); pointer-events: none"></div>
<div style="position: relative; display: flex; flex-direction: column; gap: 8px">
<span style="align-self: flex-start; font-family: Montserrat, sans-serif; font-weight: 600; font-size: 11px; letter-spacing: 0.8px; text-transform: uppercase; background: #1a1a1a; color: #e87a02; border-radius: 999px; padding: 5px 12px">Check-up reveal</span>
<h3 style="margin: 0; font-family: Montserrat, sans-serif; font-weight: 700; font-size: 20px; line-height: 1.25">"I asked a business doctor what is really wrong with my business."</h3>
</div>
<div style="position: relative; display: flex; flex-direction: column; gap: 10px; background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.08); border-radius: 20px; padding: 14px">
<span style="font-size: 12px; color: #A3A3A3; text-transform: uppercase; letter-spacing: 0.6px; font-weight: 600">The Idea</span>
<p style="margin: 0; font-size: 14px; line-height: 1.5; color: #E0E0E0">Run your check-up on camera. Read out the first thing it tells you to fix.</p>
</div>
</div>
<div class="reveal tilt" style="width: 100%; max-width: 320px; aspect-ratio: 9 / 16; background: #000000; color: #FFFFFF; border-radius: 34px; padding: 22px; display: flex; flex-direction: column; justify-content: space-between; position: relative; overflow: hidden; box-shadow: 0 40px 80px rgba(0,0,0,0.18); transform: rotate(1.5deg); animation-delay: 2s">
<div aria-hidden="true" style="position: absolute; inset: auto -40% -30% -40%; height: 70%; background: radial-gradient(closest-side, rgba(232,122,2,0.35), rgba(232,122,2,0)); pointer-events: none"></div>
<div style="position: relative; display: flex; flex-direction: column; gap: 8px">
<span style="align-self: flex-start; font-family: Montserrat, sans-serif; font-weight: 600; font-size: 11px; letter-spacing: 0.8px; text-transform: uppercase; background: #1a1a1a; color: #e87a02; border-radius: 999px; padding: 5px 12px">Mission diary</span>
<h3 style="margin: 0; font-family: Montserrat, sans-serif; font-weight: 700; font-size: 20px; line-height: 1.25">"Day 1 of doing exactly what Lavoo told me to fix first."</h3>
</div>
<div style="position: relative; display: flex; flex-direction: column; gap: 10px; background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.08); border-radius: 20px; padding: 14px">
<span style="font-size: 12px; color: #A3A3A3; text-transform: uppercase; letter-spacing: 0.6px; font-weight: 600">The Idea</span>
<p style="margin: 0; font-size: 14px; line-height: 1.5; color: #E0E0E0">Post one short update for each daily Mission. Show what changed.</p>
</div>
</div>
<div class="reveal tilt" style="width: 100%; max-width: 320px; aspect-ratio: 9 / 16; background: #000000; color: #FFFFFF; border-radius: 34px; padding: 22px; display: flex; flex-direction: column; justify-content: space-between; position: relative; overflow: hidden; box-shadow: 0 40px 80px rgba(0,0,0,0.18); transform: rotate(-1deg); animation-delay: 4s">
<div aria-hidden="true" style="position: absolute; inset: auto -40% -30% -40%; height: 70%; background: radial-gradient(closest-side, rgba(232,122,2,0.35), rgba(232,122,2,0)); pointer-events: none"></div>
<div style="position: relative; display: flex; flex-direction: column; gap: 8px">
<span style="align-self: flex-start; font-family: Montserrat, sans-serif; font-weight: 600; font-size: 11px; letter-spacing: 0.8px; text-transform: uppercase; background: #1a1a1a; color: #e87a02; border-radius: 999px; padding: 5px 12px">Tool check</span>
<h3 style="margin: 0; font-family: Montserrat, sans-serif; font-weight: 700; font-size: 20px; line-height: 1.25">"Stop buying business tools until you have done this."</h3>
</div>
<div style="position: relative; display: flex; flex-direction: column; gap: 10px; background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.08); border-radius: 20px; padding: 14px">
<span style="font-size: 12px; color: #A3A3A3; text-transform: uppercase; letter-spacing: 0.6px; font-weight: 600">The Idea</span>
<p style="margin: 0; font-size: 14px; line-height: 1.5; color: #E0E0E0">Show how the check-up told you which tool you need, or that you need none.</p>
</div>
</div>'''
    content = re.sub(r'<sc-for list="\{\{\s*posts\s*\}\}"[^>]*>.*?</sc-for>', posts_replacement, content, flags=re.DOTALL)

    # Calculator currency dropdown selector
    cur_replacement = '''<div class="reveal" style="display: flex; flex-direction: column; align-items: center; gap: 10px">
<p style="margin: 0; font-size: 14px; color: #8A8A8A">Showing <span class="val-cur-name">naira</span>. <button type="button" onclick="toggleCur()" id="cur-toggle-btn" aria-expanded="false" style="font-family: Poppins, sans-serif; font-size: 14px; color: #e87a02; background: transparent; border: 0; padding: 10px 4px; cursor: pointer">Change</button></p>
<div id="cur-selector" class="fadein" role="group" aria-label="Currency" style="display: none; gap: 4px; background: #1a1a1a; border-radius: 999px; padding: 4px">
<button type="button" class="seg" id="cur-opt-NGN" aria-pressed="true" onclick="setCurrency('NGN')" style="font-family: Montserrat, sans-serif; font-weight: 600; font-size: 15px; border: 0; border-radius: 999px; padding: 10px 22px; min-height: 44px; cursor: pointer; background: #FFFFFF; color: #000000">₦ Naira</button>
<button type="button" class="seg" id="cur-opt-GBP" aria-pressed="false" onclick="setCurrency('GBP')" style="font-family: Montserrat, sans-serif; font-weight: 600; font-size: 15px; border: 0; border-radius: 999px; padding: 10px 22px; min-height: 44px; cursor: pointer; background: transparent; color: #CCCCCC">£ Pounds</button>
<button type="button" class="seg" id="cur-opt-USD" aria-pressed="false" onclick="setCurrency('USD')" style="font-family: Montserrat, sans-serif; font-weight: 600; font-size: 15px; border: 0; border-radius: 999px; padding: 10px 22px; min-height: 44px; cursor: pointer; background: transparent; color: #CCCCCC">$ Dollars</button>
</div>
</div>'''
    content = re.sub(r'<div class="reveal"[^>]*>\s*<p[^>]*>Showing \{\{\s*curName\s*\}\}.*?<\/sc-if>\s*<\/div>', cur_replacement, content, flags=re.DOTALL)

    # Calculator input slider and track
    slider_replacement = '''<label for="members" style="font-size: clamp(17px, 1.6vw, 20px); color: #CCCCCC">If <strong id="val-n" class="num" style="font-family: Montserrat, sans-serif; font-weight: 700; color: #FFFFFF; font-size: 1.3em">10</strong> <span id="val-people-word">people pay to</span> join through you each month</label>
<input id="members" type="range" min="1" max="100" step="1" value="10" oninput="updateMembers(this.value)" style="max-width: 640px; background: linear-gradient(90deg, #e87a02 0%, #e87a02 9.09%, #2a2a2a 9.09%, #2a2a2a 100%)">'''
    content = re.sub(r'<label for="members"[^>]*>.*?</label>\s*<input id="members"[^>]*>', slider_replacement, content, flags=re.DOTALL)

    # Calculator 6 bars & month labels
    bars_replacement = '''<div aria-hidden="true" id="bars-graphic" style="display: flex; align-items: flex-end; gap: clamp(8px, 2vw, 18px); height: 200px; border-bottom: 1px solid #2a2a2a">
  <div style="flex: 1 1 0; min-width: 0; height: 100%; display: flex; flex-direction: column; justify-content: flex-end; align-items: center; gap: 8px">
    <span class="num" id="bar-val-0" style="font-size: 12px; white-space: nowrap; color: #8A8A8A">₦44k</span>
    <div class="bar" id="bar-h-0" style="width: 100%; max-width: 76px; height: 34px; background: linear-gradient(180deg, #a65800, #5a3200); border-radius: 12px 12px 4px 4px; box-shadow: none"></div>
  </div>
  <div style="flex: 1 1 0; min-width: 0; height: 100%; display: flex; flex-direction: column; justify-content: flex-end; align-items: center; gap: 8px">
    <span class="num" id="bar-val-1" style="font-size: 12px; white-space: nowrap; color: #8A8A8A">₦84k</span>
    <div class="bar" id="bar-h-1" style="width: 100%; max-width: 76px; height: 64px; background: linear-gradient(180deg, #a65800, #5a3200); border-radius: 12px 12px 4px 4px; box-shadow: none"></div>
  </div>
  <div style="flex: 1 1 0; min-width: 0; height: 100%; display: flex; flex-direction: column; justify-content: flex-end; align-items: center; gap: 8px">
    <span class="num" id="bar-val-2" style="font-size: 12px; white-space: nowrap; color: #8A8A8A">₦120k</span>
    <div class="bar" id="bar-h-2" style="width: 100%; max-width: 76px; height: 92px; background: linear-gradient(180deg, #a65800, #5a3200); border-radius: 12px 12px 4px 4px; box-shadow: none"></div>
  </div>
  <div style="flex: 1 1 0; min-width: 0; height: 100%; display: flex; flex-direction: column; justify-content: flex-end; align-items: center; gap: 8px">
    <span class="num" id="bar-val-3" style="font-size: 12px; white-space: nowrap; color: #8A8A8A">₦152k</span>
    <div class="bar" id="bar-h-3" style="width: 100%; max-width: 76px; height: 117px; background: linear-gradient(180deg, #a65800, #5a3200); border-radius: 12px 12px 4px 4px; box-shadow: none"></div>
  </div>
  <div style="flex: 1 1 0; min-width: 0; height: 100%; display: flex; flex-direction: column; justify-content: flex-end; align-items: center; gap: 8px">
    <span class="num" id="bar-val-4" style="font-size: 12px; white-space: nowrap; color: #8A8A8A">₦181k</span>
    <div class="bar" id="bar-h-4" style="width: 100%; max-width: 76px; height: 139px; background: linear-gradient(180deg, #a65800, #5a3200); border-radius: 12px 12px 4px 4px; box-shadow: none"></div>
  </div>
  <div style="flex: 1 1 0; min-width: 0; height: 100%; display: flex; flex-direction: column; justify-content: flex-end; align-items: center; gap: 8px">
    <span class="num" id="bar-val-5" style="font-size: 12px; white-space: nowrap; color: #FFFFFF">₦209k</span>
    <div class="bar" id="bar-h-5" style="width: 100%; max-width: 76px; height: 160px; background: linear-gradient(180deg, #ffb04a, #e87a02); border-radius: 12px 12px 4px 4px; box-shadow: 0 0 34px rgba(232,122,2,0.6)"></div>
  </div>
</div>
<div aria-hidden="true" style="display: flex; gap: clamp(8px, 2vw, 18px); margin-top: -14px">
  <span style="flex: 1 1 0; min-width: 0; text-align: center; font-size: 12px; color: #8A8A8A">Month 1</span>
  <span style="flex: 1 1 0; min-width: 0; text-align: center; font-size: 12px; color: #8A8A8A">Month 2</span>
  <span style="flex: 1 1 0; min-width: 0; text-align: center; font-size: 12px; color: #8A8A8A">Month 3</span>
  <span style="flex: 1 1 0; min-width: 0; text-align: center; font-size: 12px; color: #8A8A8A">Month 4</span>
  <span style="flex: 1 1 0; min-width: 0; text-align: center; font-size: 12px; color: #8A8A8A">Month 5</span>
  <span style="flex: 1 1 0; min-width: 0; text-align: center; font-size: 12px; color: #8A8A8A">Month 6</span>
</div>'''
    content = re.sub(r'<div aria-hidden="true" style="display: flex; align-items: flex-end; gap: clamp\(8px, 2vw, 18px\); height: 200px; border-bottom: 1px solid #2a2a2a">.*?<\/div>\s*<div aria-hidden="true" style="display: flex; gap: clamp\(8px, 2vw, 18px\); margin-top: -14px">.*?<\/div>', bars_replacement, content, flags=re.DOTALL)

    # Application form & confirmation
    apply_replacement = '''<form id="apply-form" onsubmit="handleApply(event)" class="reveal" style="background: #FFFFFF; border-radius: 28px; padding: clamp(24px, 4vw, 40px); display: flex; flex-direction: column; gap: 18px">
<div style="display: flex; flex-wrap: wrap; gap: 18px">
<div style="flex: 1 1 240px; display: flex; flex-direction: column; gap: 8px"><label for="ap-name" class="lbl">Full name</label><input id="ap-name" required type="text" autocomplete="name" class="field" placeholder="Your name"></div>
<div style="flex: 1 1 240px; display: flex; flex-direction: column; gap: 8px"><label for="ap-email" class="lbl">Email</label><input id="ap-email" required type="email" autocomplete="email" class="field" placeholder="you@domain.com"></div>
</div>
<div style="display: flex; flex-wrap: wrap; gap: 18px">
<div style="flex: 1 1 240px; display: flex; flex-direction: column; gap: 8px"><label for="ap-platform" class="lbl">Main platform</label><select id="ap-platform" class="field"><option>Instagram</option><option>TikTok</option><option>YouTube</option><option>X (Twitter)</option><option>LinkedIn</option><option>Facebook</option><option>Other</option></select></div>
<div style="flex: 1 1 240px; display: flex; flex-direction: column; gap: 8px"><label for="ap-size" class="lbl">Followers</label><select id="ap-size" class="field"><option>Under 10k</option><option>10k to 100k</option><option>100k+</option><option>I make UGC for brands</option></select></div>
</div>
<div style="display: flex; flex-direction: column; gap: 8px"><label for="ap-link" class="lbl">Link to your profile</label><input id="ap-link" required type="url" placeholder="https://" class="field"></div>
<button type="submit" class="btn" style="font-family: Montserrat, sans-serif; font-weight: 600; font-size: 16px; background: #e87a02; color: #000000; border: 0; border-radius: 999px; padding: 17px 24px; min-height: 52px; cursor: pointer; margin-top: 6px">Send application <span class="arrow">→</span></button>
<p style="margin: 0; font-size: 13px; color: #666666; text-align: center">By applying you agree to our <a href="/creator-agreement" style="color: #1a1a1a; text-decoration: underline">Founding Creator Agreement</a>.</p>
</form>
<div id="apply-success" class="fadein" style="display: none; background: #000000; color: #FFFFFF; border-radius: 28px; padding: clamp(32px, 5vw, 56px); text-align: center; flex-direction: column; align-items: center; gap: 12px">
<span aria-hidden="true" style="width: 56px; height: 56px; border-radius: 50%; background: #e87a02; color: #000000; display: flex; align-items: center; justify-content: center"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6L9 17l-5-5"></path></svg></span>
<h3 style="margin: 0; font-family: Montserrat, sans-serif; font-weight: 700; font-size: 24px">Application received</h3>
<p style="margin: 0; font-size: 16px; color: #CCCCCC; max-width: 440px">Thanks for applying. We review every application by hand and reply within 48 hours with your unique creator link.</p>
</div>'''
    content = re.sub(r'<sc-if value="\{\{\s*notApplied\s*\}\}"[^>]*>.*?<\/sc-if>\s*<sc-if value="\{\{\s*applied\s*\}\}"[^>]*>.*?<\/sc-if>', apply_replacement, content, flags=re.DOTALL)

    # Dynamic value placeholders
    content = content.replace("{{ feedTotal }}", '<span id="val-feed-total">₦44,175</span>')
    content = content.replace("{{ month6 }}", '<span id="val-month6">₦208,610</span>')
    content = content.replace("{{ total6 }}", '<span id="val-total6">₦676,647</span>')
    content = content.replace("{{ perMember }}", '<span id="val-per-member">₦44,175</span>')
    content = content.replace("{{ taxText }}", '<span id="val-tax-text">7.5% VAT</span>')
    content = content.replace("{{ proMonth }}", '<span id="val-pro-month">₦9,302</span>')
    content = content.replace("{{ pro6 }}", '<span id="val-pro-6">₦55,814</span>')
    content = content.replace("{{ premMonth }}", '<span id="val-prem-month">₦16,279</span>')
    content = content.replace("{{ prem6 }}", '<span id="val-prem-6">₦97,674</span>')
    content = content.replace("{{ premYear }}", '<span id="val-prem-year">₦152,093</span>')
    
    # Replace all occurrences of {{ curName }}
    content = re.sub(r'\{\{\s*curName\s*\}\}', '<span class="val-cur-name">naira</span>', content)

    # Add client-side script for interactive calculator and UI
    client_js = '''
<script>
var CUR = {
  NGN: { label: '₦ Naira', name: 'naira', sym: '₦', pro: 20000, prem: 35000, proY: 187000, premY: 327000, vat: 0.075, tax: '7.5% VAT' },
  GBP: { label: '£ Pounds', name: 'pounds', sym: '£', pro: 15, prem: 27, proY: 140, premY: 252, vat: 0.20, tax: '20% VAT' },
  USD: { label: '$ Dollars', name: 'dollars', sym: '$', pro: 19, prem: 35, proY: 177, premY: 327, vat: 0.0, tax: 'any sales tax' }
};
var currentCurKey = 'NGN';
var currentN = 10;
var FEE = 0.03, RATE = 0.5, STAY = 0.9, SHARE_PRO = 0.5;

function detectCurrency() {
  var tz = '';
  try { tz = Intl.DateTimeFormat().resolvedOptions().timeZone || ''; } catch (e) {}
  if (tz.indexOf('Lagos') !== -1 || tz.indexOf('Africa') !== -1) return 'NGN';
  if (tz.indexOf('London') !== -1 || tz.indexOf('Europe/London') !== -1) return 'GBP';
  return 'NGN';
}

function net(v, c) { return (v / (1 + c.vat)) * (1 - FEE) * RATE; }
function geo(k) { var s = 0; for (var a = 0; a < k; a++) { s += Math.pow(STAY, a); } return s; }

function fmt(v, sym) { return sym + Math.round(v).toLocaleString('en-GB'); }
function compact(v, sym) {
  if (v >= 1e6) return sym + (v / 1e6).toFixed(v >= 1e7 ? 0 : 1) + 'm';
  if (v >= 1e3) return sym + (v / 1e3).toFixed(v >= 1e5 ? 0 : 1) + 'k';
  return sym + Math.round(v);
}

function updateCalculator() {
  var c = CUR[currentCurKey];
  var n = currentN;
  var sym = c.sym;

  var avg = SHARE_PRO * c.pro + (1 - SHARE_PRO) * c.prem;
  var perPayment = net(avg, c);
  var months = [];
  for (var m = 1; m <= 6; m++) { months.push(n * perPayment * geo(m)); }
  var total6 = months.reduce(function (a, b) { return a + b; }, 0);
  var perMember = perPayment * geo(6);

  var proM = net(c.pro, c);
  var premM = net(c.prem, c);
  var premYr = net(c.premY, c);

  // Update DOM elements
  var elN = document.getElementById('val-n'); if (elN) elN.textContent = n;
  var elPW = document.getElementById('val-people-word'); if (elPW) elPW.textContent = (n === 1 ? 'person pays to' : 'people pay to');
  var elM6 = document.getElementById('val-month6'); if (elM6) elM6.textContent = fmt(months[5], sym);
  var elT6 = document.getElementById('val-total6'); if (elT6) elT6.textContent = fmt(total6, sym);
  var elPM = document.getElementById('val-per-member'); if (elPM) elPM.textContent = fmt(perMember, sym);
  var elTT = document.getElementById('val-tax-text'); if (elTT) elTT.textContent = c.tax;
  
  // All occurrences of val-cur-name
  document.querySelectorAll('.val-cur-name').forEach(function(el) { el.textContent = c.name; });

  // Plan breakdowns
  var elPMon = document.getElementById('val-pro-month'); if (elPMon) elPMon.textContent = fmt(proM, sym);
  var elP6 = document.getElementById('val-pro-6'); if (elP6) elP6.textContent = fmt(proM * 6, sym);
  var elPrM = document.getElementById('val-prem-month'); if (elPrM) elPrM.textContent = fmt(premM, sym);
  var elPr6 = document.getElementById('val-prem-6'); if (elPr6) elPr6.textContent = fmt(premM * 6, sym);
  var elPrY = document.getElementById('val-prem-year'); if (elPrY) elPrY.textContent = fmt(premYr, sym);

  // Hero feed values
  var elFT = document.getElementById('val-feed-total'); if (elFT) elFT.textContent = fmt(proM + premM + premYr, sym);
  var elFA0 = document.getElementById('feed-amt-0'); if (elFA0) elFA0.textContent = fmt(proM, sym);
  var elFA1 = document.getElementById('feed-amt-1'); if (elFA1) elFA1.textContent = fmt(premM, sym);
  var elFA2 = document.getElementById('feed-amt-2'); if (elFA2) elFA2.textContent = fmt(premYr, sym);

  // Bar graphics
  var max = months[5] || 1;
  for (var i = 0; i < 6; i++) {
    var v = months[i];
    var h = Math.max(6, Math.round((v / max) * 160)) + 'px';
    var barEl = document.getElementById('bar-h-' + i);
    var valEl = document.getElementById('bar-val-' + i);
    if (barEl) barEl.style.height = h;
    if (valEl) valEl.textContent = compact(v, sym);
  }

  // Slider track
  var pct = ((n - 1) / 99) * 100;
  var slider = document.getElementById('members');
  if (slider) slider.style.background = 'linear-gradient(90deg, #e87a02 0%, #e87a02 ' + pct + '%, #2a2a2a ' + pct + '%, #2a2a2a 100%)';
}

function updateMembers(val) {
  currentN = Number(val);
  updateCalculator();
}

function setCurrency(key) {
  currentCurKey = key;
  ['NGN', 'GBP', 'USD'].forEach(function(k) {
    var btn = document.getElementById('cur-opt-' + k);
    if (btn) {
      if (k === key) {
        btn.style.background = '#FFFFFF';
        btn.style.color = '#000000';
        btn.setAttribute('aria-pressed', 'true');
      } else {
        btn.style.background = 'transparent';
        btn.style.color = '#CCCCCC';
        btn.setAttribute('aria-pressed', 'false');
      }
    }
  });
  updateCalculator();
  toggleCur();
}

function toggleCur() {
  var sel = document.getElementById('cur-selector');
  var btn = document.getElementById('cur-toggle-btn');
  if (sel) {
    var isOpen = sel.style.display !== 'none';
    sel.style.display = isOpen ? 'none' : 'flex';
    if (btn) btn.setAttribute('aria-expanded', (!isOpen).toString());
  }
}

function toggleMenu() {
  var menu = document.getElementById('mobile-menu');
  var path = document.getElementById('burger-path');
  if (menu) {
    var isOpen = menu.style.display !== 'none';
    menu.style.display = isOpen ? 'none' : 'flex';
    if (path) path.setAttribute('d', isOpen ? 'M4 9h16M4 15h16' : 'M6 6l12 12M18 6L6 18');
  }
}

function closeMenu() {
  var menu = document.getElementById('mobile-menu');
  var path = document.getElementById('burger-path');
  if (menu) menu.style.display = 'none';
  if (path) path.setAttribute('d', 'M4 9h16M4 15h16');
}

function handleApply(e) {
  e.preventDefault();
  var form = document.getElementById('apply-form');
  var success = document.getElementById('apply-success');
  if (form && success) {
    form.style.display = 'none';
    success.style.display = 'flex';
  }
}

document.addEventListener('DOMContentLoaded', function() {
  currentCurKey = detectCurrency();
  setCurrency(currentCurKey);
  toggleCur(); // keep dropdown closed initially
});
</script>'''

    final_html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Lavoo: Founding Creator Programme</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700;800;900&family=Poppins:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<style>
{prog_css}
</style>
</head>
<body>
{content}
{client_js}
</body>
</html>'''
    return final_html

# -------------------------------------------------------------
# 2. BUILD CREATOR AGREEMENT PAGE (public/creator-agreement.html)
# -------------------------------------------------------------
def build_agreement_page():
    content = re.sub(r'<helmet>.*?</helmet>', '', agree_tmpl, flags=re.DOTALL)
    content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL)
    content = content.replace("<x-dc>", "").replace("</x-dc>", "")
    
    # Replace logo image uuid with local asset
    content = content.replace("65d2e99b-ba67-4f52-9329-569fb5317c60", "/assets/lavoo-logo.png")
    content = content.replace("fcb366f7-70de-4e95-9e2f-f78c0dda4cf3", "/assets/lavoo-logo.png")

    # Update links
    content = content.replace('href="Creators.dc.html"', 'href="/"')
    content = content.replace('href="Creators.dc.html#calculator"', 'href="/#calculator"')
    content = content.replace('href="Creators.dc.html#who"', 'href="/#who"')
    content = content.replace('href="Creators.dc.html#path"', 'href="/#how"')
    content = content.replace('href="Creators.dc.html#apply"', 'href="/#apply"')
    content = content.replace('href="CreatorTerms.dc.html"', 'href="/creator-agreement"')
    content = content.replace('href="Main.dc.html"', 'href="https://lavoo.io"')

    # Burger icon & toggle
    burger_replacement = '''<button type="button" class="nav-burger" aria-label="Menu" aria-expanded="false" onclick="toggleMenu()" style="background:transparent; border:0; cursor:pointer; padding:8px; display:none; align-items:center; justify-content:center; color:#1a1a1a;">
<svg id="burger-icon" aria-hidden="true" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><path id="burger-path" d="M4 9h16M4 15h16"></path></svg>
</button>'''
    content = re.sub(r'<button type="button" class="nav-burger"[^>]*>.*?</button>', burger_replacement, content, flags=re.DOTALL)

    # Mobile menu
    mobile_nav_replacement = '''<nav id="mobile-menu" aria-label="Mobile" class="nav-mobile fadein" style="display: none; padding: 8px 20px 28px; flex-direction: column">
<a href="/#calculator" onclick="closeMenu()" style="font-family: Montserrat, sans-serif; font-weight: 600; font-size: 26px; color: #1a1a1a; text-decoration: none; padding: 16px 0; border-bottom: 1px solid #EDEDED">Earnings</a>
<a href="/#who" onclick="closeMenu()" style="font-family: Montserrat, sans-serif; font-weight: 600; font-size: 26px; color: #1a1a1a; text-decoration: none; padding: 16px 0; border-bottom: 1px solid #EDEDED">Who it is for</a>
<a href="/#how" onclick="closeMenu()" style="font-family: Montserrat, sans-serif; font-weight: 600; font-size: 26px; color: #1a1a1a; text-decoration: none; padding: 16px 0; border-bottom: 1px solid #EDEDED">How it grows</a>
<a href="/creator-agreement" onclick="closeMenu()" style="font-family: Montserrat, sans-serif; font-weight: 600; font-size: 26px; color: #e87a02; text-decoration: none; padding: 16px 0; border-bottom: 1px solid #EDEDED">Agreement</a>
<a href="https://lavoo.io" style="font-family: Montserrat, sans-serif; font-weight: 600; font-size: 26px; color: #1a1a1a; text-decoration: none; padding: 16px 0">What is Lavoo?</a>
</nav>'''
    content = re.sub(r'<sc-if value="\{\{\s*menuOpen\s*\}\}"[^>]*>.*?</sc-if>', mobile_nav_replacement, content, flags=re.DOTALL)

    # Table of contents accordion on mobile
    toc_replacement = '''<div class="toc-mobile" style="margin-bottom: 8px">
<button type="button" onclick="toggleToc()" id="toc-btn" aria-expanded="false" style="width: 100%; display: flex; justify-content: space-between; align-items: center; font-family: Montserrat, sans-serif; font-weight: 600; font-size: 15px; background: #F5F5F5; color: #1a1a1a; border: 0; border-radius: 18px; padding: 16px 20px; min-height: 52px; cursor: pointer">
<span>Table of contents</span><span id="toc-icon" style="font-size: 18px">+</span>
</button>
<nav id="toc-mobile-menu" class="toc fadein" aria-label="Contents" style="display: none; flex-direction: column; padding: 8px 20px 4px">
<a href="#s1" onclick="closeToc()"><span>01</span>This agreement</a>
<a href="#s2" onclick="closeToc()"><span>02</span>Your contract period</a>
<a href="#s3" onclick="closeToc()"><span>03</span>What you earn</a>
<a href="#s4" onclick="closeToc()"><span>04</span>Content and deliverables</a>
<a href="#s5" onclick="closeToc()"><span>05</span>How you get paid</a>
<a href="#s6" onclick="closeToc()"><span>06</span>House rules & end of contract</a>
</nav>
</div>'''
    content = re.sub(r'<div class="toc-mobile"[^>]*>.*?<\/sc-if>\s*<\/div>', toc_replacement, content, flags=re.DOTALL)

    # Print button hook
    content = re.sub(r'sc-camel-on-click="\{\{\s*printPage\s*\}\}"', 'onclick="window.print()"', content)

    # Clean any other sc- directives
    content = re.sub(r'<sc-[a-z0-9-]+[^>]*>', '', content)
    content = re.sub(r'</sc-[a-z0-9-]+>', '', content)

    # Client-side JS for Agreement page
    client_js = '''
<script>
function toggleMenu() {
  var menu = document.getElementById('mobile-menu');
  var path = document.getElementById('burger-path');
  if (menu) {
    var isOpen = menu.style.display !== 'none';
    menu.style.display = isOpen ? 'none' : 'flex';
    if (path) path.setAttribute('d', isOpen ? 'M4 9h16M4 15h16' : 'M6 6l12 12M18 6L6 18');
  }
}

function closeMenu() {
  var menu = document.getElementById('mobile-menu');
  var path = document.getElementById('burger-path');
  if (menu) menu.style.display = 'none';
  if (path) path.setAttribute('d', 'M4 9h16M4 15h16');
}

function toggleToc() {
  var toc = document.getElementById('toc-mobile-menu');
  var icon = document.getElementById('toc-icon');
  var btn = document.getElementById('toc-btn');
  if (toc) {
    var isOpen = toc.style.display !== 'none';
    toc.style.display = isOpen ? 'none' : 'flex';
    if (icon) icon.textContent = isOpen ? '+' : '−';
    if (btn) btn.setAttribute('aria-expanded', (!isOpen).toString());
  }
}

function closeToc() {
  var toc = document.getElementById('toc-mobile-menu');
  var icon = document.getElementById('toc-icon');
  var btn = document.getElementById('toc-btn');
  if (toc) toc.style.display = 'none';
  if (icon) icon.textContent = '+';
  if (btn) btn.setAttribute('aria-expanded', 'false');
}

// Active TOC indicator on scroll
document.addEventListener('DOMContentLoaded', function() {
  var sections = document.querySelectorAll('.sec');
  var tocLinks = document.querySelectorAll('.toc a');
  window.addEventListener('scroll', function() {
    var scrollPos = window.scrollY + 120;
    sections.forEach(function(sec) {
      if (sec.offsetTop <= scrollPos && (sec.offsetTop + sec.offsetHeight) > scrollPos) {
        var id = sec.getAttribute('id');
        tocLinks.forEach(function(link) {
          if (link.getAttribute('href') === '#' + id) {
            link.style.color = '#e87a02';
          } else {
            link.style.color = '#666666';
          }
        });
      }
    });
  });
});
</script>'''

    final_html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Lavoo: Creator Agreement</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700;800;900&family=Poppins:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<style>
{agree_css}
</style>
</head>
<body>
{content}
{client_js}
</body>
</html>'''
    return final_html

# Generate pages
prog_html = build_programme_page()
agree_html = build_agreement_page()

dest_dir = r"c:\Users\Owner\dev\projects\lavoo\lavoo-founder\public"

with open(os.path.join(dest_dir, "index.html"), "w", encoding="utf-8") as f:
    f.write(prog_html)
print(f"Generated {os.path.join(dest_dir, 'index.html')} ({len(prog_html)} bytes)")

with open(os.path.join(dest_dir, "creator-agreement.html"), "w", encoding="utf-8") as f:
    f.write(agree_html)
print(f"Generated {os.path.join(dest_dir, 'creator-agreement.html')} ({len(agree_html)} bytes)")
