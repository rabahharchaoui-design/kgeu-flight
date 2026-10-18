# Runways review sheets: for every airport (region + runway code), one combined
# PNG per up-to-16 "keys" (an end x pos x cam x tod combination), each key shown
# as a row with the BEFORE picture on top and the AFTER picture below it, so an
# owner can scroll a handful of images per airport instead of 272 side by side.
#
# Input: a 'before' folder and an 'after' folder of tests/runway_shots.py output
# (same naming: <region>_<CODE>_<NUM>_<pos>_<cam>_<tod>.png, pos runway|final,
# cam cockpit|chase, tod day|night) and an output folder.
#
# Output: <out>/<airport>.png (or <airport>_1.png, _2.png, ... when an airport
# has more than 16 keys) laid out as up to 4 columns x 4 rows of before/after
# pairs, each picture scaled to 422x195 (half of 844x390) with a labelled dark
# strip ('BEFORE  Glendale 1  runway  chase  day' / 'AFTER ...'); a missing
# before or after picture becomes a grey 'missing' placeholder. Also writes
# <out>/index.txt listing every sheet.
#
# Usage:
#   .venv/bin/python tools/compare_sheets.py <before_dir> <after_dir> <out_dir>
import os, re, sys
from PIL import Image, ImageDraw, ImageFont

IMG_W, IMG_H = 422, 195
LABEL_H = 16
COLS, ROWS = 4, 4          # pairs per sheet grid
PER_SHEET = COLS * ROWS

NAME_RE = re.compile(r'^([a-z0-9]+)_([A-Za-z0-9]+)_([0-9A-Za-z]+)_(runway|final)_(cockpit|chase)_(day|night)\.png$')
POS_ORDER = {'runway': 0, 'final': 1}
CAM_ORDER = {'cockpit': 0, 'chase': 1}
TOD_ORDER = {'day': 0, 'night': 1}

AIRPORT_NAME = {
    'az_KGEU': 'Glendale', 'az_KLUF': 'Luke', 'az_KPHX': 'Sky Harbor', 'az_LZ': 'the assault strip',
    'rjtt_RJTT': 'Haneda', 'lfpg_LFPG': 'de Gaulle', 'sbrj_SBRJ': 'Santos Dumont',
}


def font(sz):
    try:
        return ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', sz)
    except Exception:
        return ImageFont.load_default()


def scan(d):
    """-> {airport_key: [(sort_key, region, code, num, pos, cam, tod, fname), ...]}"""
    out = {}
    if not os.path.isdir(d):
        return out
    for fn in sorted(os.listdir(d)):
        m = NAME_RE.match(fn)
        if not m:
            continue
        region, code, num, pos, cam, tod = m.groups()
        airport = f'{region}_{code}'
        sort_key = (num, POS_ORDER.get(pos, 9), CAM_ORDER.get(cam, 9), TOD_ORDER.get(tod, 9))
        out.setdefault(airport, []).append((sort_key, region, code, num, pos, cam, tod, fn))
    for airport in out:
        out[airport].sort(key=lambda t: t[0])
    return out


def cell(path, label):
    """One labelled picture: a dark strip with white text above a 422x195 image
    (or a grey 'missing' placeholder when path is None or absent)."""
    im = Image.new('RGB', (IMG_W, LABEL_H + IMG_H), (20, 18, 16))
    d = ImageDraw.Draw(im)
    if path and os.path.exists(path):
        try:
            pic = Image.open(path).convert('RGB').resize((IMG_W, IMG_H), Image.LANCZOS)
            im.paste(pic, (0, LABEL_H))
        except Exception:
            d.rectangle([0, LABEL_H, IMG_W, LABEL_H + IMG_H], fill=(90, 90, 90))
            d.text((10, LABEL_H + IMG_H // 2), 'missing (unreadable)', fill=(230, 230, 230), font=font(14))
    else:
        d.rectangle([0, LABEL_H, IMG_W, LABEL_H + IMG_H], fill=(90, 90, 90))
        d.text((10, LABEL_H + IMG_H // 2 - 7), 'missing', fill=(230, 230, 230), font=font(14))
    d.text((4, 1), label, fill=(255, 255, 255), font=font(11))
    return im


def pair_label(prefix, airport, num, pos, cam, tod):
    name = AIRPORT_NAME.get(airport, airport)
    return f'{prefix}  {name} {num}  {pos}  {cam}  {tod}'


def build_sheets(before_map, after_map, out_dir):
    airports = sorted(set(before_map) | set(after_map))
    sheet_paths = []
    for airport in airports:
        before_rows = {(r[3], r[4], r[5], r[6]): r for r in before_map.get(airport, [])}
        after_rows = {(r[3], r[4], r[5], r[6]): r for r in after_map.get(airport, [])}
        keys = sorted(set(before_rows) | set(after_rows),
                       key=lambda k: (k[0], POS_ORDER.get(k[1], 9), CAM_ORDER.get(k[2], 9), TOD_ORDER.get(k[3], 9)))
        chunks = [keys[i:i + PER_SHEET] for i in range(0, len(keys), PER_SHEET)] or [[]]
        multi = len(chunks) > 1
        for ci, chunk in enumerate(chunks):
            n = len(chunk)
            cols = min(COLS, n) if n else 1
            rows = -(-n // cols) if n else 1
            cols = max(cols, 1)
            sheet_w = IMG_W * cols
            sheet_h = (LABEL_H + IMG_H) * 2 * rows
            S = Image.new('RGB', (sheet_w, sheet_h), (12, 10, 8))
            for i, k in enumerate(chunk):
                num, pos, cam, tod = k
                r, c = divmod(i, cols)
                before_fn = before_rows.get(k, (None,) * 8)[7]
                after_fn = after_rows.get(k, (None,) * 8)[7]
                before_path = os.path.join(sys.argv[1], before_fn) if before_fn else None
                after_path = os.path.join(sys.argv[2], after_fn) if after_fn else None
                top = cell(before_path, pair_label('BEFORE', airport, num, pos, cam, tod))
                bot = cell(after_path, pair_label('AFTER', airport, num, pos, cam, tod))
                x = c * IMG_W
                y = r * (LABEL_H + IMG_H) * 2
                S.paste(top, (x, y))
                S.paste(bot, (x, y + LABEL_H + IMG_H))
            name = f'{airport}_{ci + 1}.png' if multi else f'{airport}.png'
            path = os.path.join(out_dir, name)
            S.save(path)
            sheet_paths.append((path, S.size, n))
            print(' ', path, S.size, f'{n} keys')
    return sheet_paths


def main():
    if len(sys.argv) != 4:
        print('usage: compare_sheets.py <before_dir> <after_dir> <out_dir>'); sys.exit(1)
    before_dir, after_dir, out_dir = sys.argv[1:4]
    os.makedirs(out_dir, exist_ok=True)
    before_map = scan(before_dir)
    after_map = scan(after_dir)
    sheets = build_sheets(before_map, after_map, out_dir)
    with open(os.path.join(out_dir, 'index.txt'), 'w') as f:
        for path, size, n in sheets:
            f.write(f'{os.path.basename(path)}  {size[0]}x{size[1]}  {n} keys\n')
    print('wrote', len(sheets), 'sheets to', out_dir)


if __name__ == '__main__':
    main()
