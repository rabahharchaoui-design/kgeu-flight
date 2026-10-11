# Graphics session before/after sheet: every shot name found in both dirs laid out baseline | new with a label, and the
# numbers that make colour drift measurable: the mean luminance of each (0..255, PIL's L: 0.299 R + 0.587 G + 0.114 B
# on the sRGB values), new/baseline ratio, and the mean absolute pixel difference over RGB.
#   .venv/bin/python tests/graphics_compare.py <baseline_dir> <new_dir> <out_sheet.jpg> [--w 640]
import os, sys
from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageStat

def stats(a, b):
    if a.size != b.size: b = b.resize(a.size, Image.BILINEAR)
    la, lb = ImageStat.Stat(a.convert('L')).mean[0], ImageStat.Stat(b.convert('L')).mean[0]
    mad = sum(ImageStat.Stat(ImageChops.difference(a, b)).mean) / 3
    return la, lb, (lb / la if la else float('nan')), mad

def main():
    args = [x for x in sys.argv[1:]]
    W = 640
    if '--w' in args: i = args.index('--w'); W = int(args[i + 1]); del args[i:i + 2]
    if len(args) != 3: sys.exit(__doc__ or 'usage: graphics_compare.py <baseline_dir> <new_dir> <out_sheet.jpg> [--w 640]')
    base, new, out = args
    names = sorted(n for n in os.listdir(base) if n.endswith('.png') and os.path.exists(os.path.join(new, n)))
    if not names: sys.exit('no shot names in both dirs')
    try: font = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 18)
    except Exception: font = ImageFont.load_default()
    rows = []
    print(f"{'shot':<16}{'lum base':>10}{'lum new':>10}{'ratio':>8}{'mad':>8}")
    for n in names:
        a = Image.open(os.path.join(base, n)).convert('RGB'); b = Image.open(os.path.join(new, n)).convert('RGB')
        la, lb, r, mad = stats(a, b)
        print(f"{n[:-4]:<16}{la:>10.1f}{lb:>10.1f}{r:>8.3f}{mad:>8.1f}")
        h = round(a.height * W / a.width)
        rows.append((n[:-4], a.resize((W, h), Image.LANCZOS), b.resize((W, h), Image.LANCZOS), la, lb, r, mad))
    LBL, GAP = 28, 6
    H = sum(r[1].height + LBL + GAP for r in rows)
    sheet = Image.new('RGB', (W * 2 + GAP, H), (24, 24, 28)); d = ImageDraw.Draw(sheet); y = 0
    for n, a, b, la, lb, r, mad in rows:
        d.text((6, y + 4), f'{n}  baseline  L {la:.1f}', fill=(230, 230, 230), font=font)
        d.text((W + GAP + 6, y + 4), f'{n}  new  L {lb:.1f}  ratio {r:.3f}  mad {mad:.1f}', fill=(255, 214, 120) if abs(r - 1) > 0.1 else (170, 230, 170), font=font)
        sheet.paste(a, (0, y + LBL)); sheet.paste(b, (W + GAP, y + LBL)); y += a.height + LBL + GAP
    sheet.save(out, quality=88)
    print(f'graphics_compare: {len(rows)} pairs to {out}')

if __name__ == '__main__':
    main()
