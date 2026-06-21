#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'data' / 'latest.json'
OUT = ROOT / 'agent-arcade-preview.png'

W, H = 1400, 1000
img = Image.new('RGB', (W, H), '#100b18')
d = ImageDraw.Draw(img)

try:
    title_font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Bold.ttf', 82)
    h_font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Bold.ttf', 34)
    b_font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf', 22)
    s_font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf', 18)
except Exception:
    title_font = h_font = b_font = s_font = ImageFont.load_default()

payload = json.loads(DATA.read_text())
agents = payload['agents']

# gradient-ish backdrop
for y in range(H):
    r = int(16 + 25 * y / H)
    g = int(11 + 8 * y / H)
    b = int(24 + 35 * (1 - y / H))
    d.line((0, y, W, y), fill=(r, g, b))

cream = '#f7f0d8'
muted = '#c9c1b6'
cyan = '#66f0ff'
panel = '#141320'
border = '#343146'
green = '#88ffb3'
yellow = '#ffd766'

x0 = 90
d.text((x0, 55), 'LOCAL STATIC DASHBOARD', fill=cyan, font=s_font)
d.text((x0, 90), 'Agent Arcade', fill=cream, font=title_font)
d.text((x0, 185), 'Local-first dashboard for Hermes operators', fill=muted, font=b_font)

scores = [
    ('HERMES', payload['hermes']['version'].get('version') or 'unknown'),
    ('GATEWAY', 'Online' if payload['hermes']['gateway'].get('running') else 'Offline'),
    ('CRON JOBS', str(payload['hermes']['cron_list'].get('count', 0))),
    ('GIT', 'Clean' if payload['repo'].get('clean') else f"{payload['repo'].get('changed_files', 0)} changed"),
]
card_w, card_h = 285, 92
for i, (label, value) in enumerate(scores):
    x = x0 + i * (card_w + 24)
    y = 240
    d.rounded_rectangle((x, y, x + card_w, y + card_h), radius=18, fill=panel, outline=border, width=2)
    d.text((x + 24, y + 20), label, fill=muted, font=s_font)
    d.text((x + 24, y + 48), value, fill=cream, font=b_font)

d.text((x0, 365), 'Live snapshot loaded from ../data/latest.json', fill=muted, font=s_font)
d.text((935, 365), f"Snapshot: {payload['generated_at'][:16].replace('T', ' ')}", fill=muted, font=s_font)

cols = 4
cw, ch = 285, 275
gapx, gapy = 24, 26
start_y = 420
for idx, a in enumerate(agents[:8]):
    col, row = idx % cols, idx // cols
    x = x0 + col * (cw + gapx)
    y = start_y + row * (ch + gapy)
    d.rounded_rectangle((x, y, x + cw, y + ch), radius=22, fill=panel, outline=border, width=2)
    status = a.get('status', 'ready').upper()
    pill_color = yellow if status == 'ACTIVE' else green if status == 'READY' else '#ff865e'
    d.rounded_rectangle((x + cw - 100, y + 26, x + cw - 22, y + 58), radius=16, fill=pill_color)
    d.text((x + cw - 84, y + 34), status, fill='#111111', font=s_font)
    role = a.get('role','').upper()
    d.text((x + 24, y + 32), role[:22], fill=muted, font=s_font)
    d.text((x + 24, y + 74), a.get('label',''), fill=cream, font=h_font)
    tagline = a.get('tagline','')
    # simple wrap
    words, lines, line = tagline.split(), [], ''
    for w in words:
        if len(line + ' ' + w) > 30:
            lines.append(line); line = w
        else:
            line = (line + ' ' + w).strip()
    if line: lines.append(line)
    for j, line in enumerate(lines[:3]):
        d.text((x + 24, y + 125 + j*27), line, fill=cream, font=b_font)
    d.line((x + 24, y + 205, x + cw - 24, y + 205), fill=border, width=1)
    d.text((x + 24, y + 220), 'SIGNAL', fill=muted, font=s_font)
    signal = a.get('signal','Standing by.')
    d.text((x + 24, y + 244), signal[:34], fill=cream, font=s_font)

img.save(OUT)
print(OUT)
