# Schoolhud: the before and after sheet of tests/schoolhud_shots.py output. One row a shot that both folders have, BEFORE
# left and AFTER right, each scaled to half its size with a label strip.
# Usage: .venv/bin/python tools/schoolhud_sheet.py <before_dir> <after_dir> <out.png> [name filter]
import os, sys
from PIL import Image, ImageDraw
bd, ad, out = sys.argv[1:4]; flt = sys.argv[4] if len(sys.argv) > 4 else ''
names = sorted(n for n in os.listdir(ad) if n.endswith('.png') and flt in n and os.path.exists(os.path.join(bd, n)))
rows = []
for n in names:
    a, b = Image.open(os.path.join(bd, n)).convert('RGB'), Image.open(os.path.join(ad, n)).convert('RGB')
    s = 0.5 if a.width > 1200 else 0.6
    a = a.resize((int(a.width * s), int(a.height * s))); b = b.resize((int(b.width * s), int(b.height * s)))
    rows.append((n[:-4], a, b))
W = max(r[1].width + r[2].width for r in rows) + 30; H = sum(max(r[1].height, r[2].height) + 34 for r in rows) + 10
sheet = Image.new('RGB', (W, H), (18, 20, 24)); d = ImageDraw.Draw(sheet); y = 10
for name, a, b in rows:
    d.text((10, y), 'BEFORE  ' + name, fill=(230, 230, 230)); d.text((a.width + 20, y), 'AFTER  ' + name, fill=(140, 220, 255))
    sheet.paste(a, (10, y + 18)); sheet.paste(b, (a.width + 20, y + 18)); y += max(a.height, b.height) + 34
sheet.save(out); print(out, len(rows), 'rows')
