# Weather session review sheets: one combined before/after image per cloud preset and per weather type for the owner.
#   .venv/bin/python tests/weather_sheets.py <before_dir> <after_dir> <types_dir> <out_dir>
# <before_dir>/<after_dir>: tests/weather_shots.py output on the preweather tag and on the branch (same 42 names).
# <types_dir>: tests/weather_type_shots.py output on the branch (<type>_<tod>_<view>.png plus the specials).
# Presets (clear, scattered, monsoon, haboob): rows of matching scenes, columns before | after.
# Types (overcast, rain, storm, fog, gusty, and the four above from the types dir): a grid of day / sunset / night
# from the chase and the cockpit plus the specials, with the nearest preweather scene as the "before" column
# (there was no such weather before: the before column says so).
import os, sys
from PIL import Image, ImageDraw, ImageFont

W = 560   # each cell's width; the shots are 1688x780 (844x390 at 2x)
PRESETS = {
    'clear': ['clear_day_final_chase', 'clear_day_air_chase', 'clear_sunset_air_chase', 'clear_night_air_chase', 'clear_day_final_cockpit'],
    'scattered': ['scattered_day_final_chase', 'scattered_day_air_chase', 'scattered_day_air_cockpit', 'scattered_sunset_air_chase',
                  'scattered_night_air_chase', 'scattered_day_through'],
    'monsoon': ['monsoon_day_final_chase', 'monsoon_day_air_chase', 'monsoon_day_high_chase', 'monsoon_sunset_final_chase',
                'monsoon_night_air_chase', 'monsoon_day_air_cockpit'],
    'haboob': ['haboob_final_chase', 'haboob_final_cockpit', 'haboob_wall_chase', 'haboob_wall_cockpit'],
}
# weather type -> (the preweather scene that stands for "before", the type scenes to show)
TYPES = {
    'clear': ('clear_day_final_chase', ['clear_day_final_chase', 'clear_sunset_final_chase', 'clear_night_final_chase', 'clear_day_final_cockpit']),
    'scattered': ('scattered_day_final_chase', ['scattered_day_final_chase', 'scattered_sunset_final_chase', 'scattered_night_final_chase', 'scattered_day_final_cockpit']),
    'overcast': ('scattered_day_final_chase', ['overcast_day_final_chase', 'overcast_sunset_final_chase', 'overcast_night_final_chase', 'overcast_day_final_cockpit', 'overcast_day_above']),
    'rain': ('scattered_day_final_chase', ['rain_day_final_chase', 'rain_sunset_final_chase', 'rain_night_final_chase', 'rain_day_final_cockpit', 'rain_day_runway_chase', 'rain_night_final_cockpit']),
    'storm': ('monsoon_day_air_chase', ['storm_day_final_chase', 'storm_sunset_final_chase', 'storm_night_final_chase', 'storm_day_final_cockpit', 'storm_sunset_air_chase', 'storm_day_flash_chase']),
    'fog': ('clear_day_final_chase', ['fog_day_final_chase', 'fog_sunset_final_chase', 'fog_night_final_chase', 'fog_day_final_cockpit', 'fog_night_final_cockpit', 'fog_day_above']),
    'gusty': ('scattered_day_final_chase', ['gusty_day_final_chase', 'gusty_sunset_final_chase', 'gusty_night_final_chase', 'gusty_day_final_cockpit', 'gusty_day_runway_chase']),
    'haboob': ('haboob_final_chase', ['haboob_day_final_chase', 'haboob_sunset_final_chase', 'haboob_night_final_chase', 'haboob_day_final_cockpit']),
}

def font(sz):
    try: return ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', sz)
    except Exception: return ImageFont.load_default()

def cell(path, label, note=None):
    h = int(W * 780 / 1688)
    im = Image.new('RGB', (W, h + 22), (24, 20, 16))
    if path and os.path.exists(path):
        im.paste(Image.open(path).convert('RGB').resize((W, h), Image.LANCZOS), (0, 22))
    else:
        d = ImageDraw.Draw(im); d.text((12, h // 2), note or 'no such scene', fill=(170, 160, 150), font=font(16))
    ImageDraw.Draw(im).text((6, 3), label, fill=(240, 230, 210), font=font(14))
    return im

def sheet(rows, title, out):
    cw, ch = rows[0][0].size
    S = Image.new('RGB', (cw * len(rows[0]) + 8 * (len(rows[0]) - 1), 34 + (ch + 6) * len(rows)), (12, 10, 8))
    ImageDraw.Draw(S).text((8, 7), title, fill=(246, 193, 119), font=font(20))
    for r, cells in enumerate(rows):
        for c, im in enumerate(cells): S.paste(im, (c * (cw + 8), 34 + r * (ch + 6)))
    S.save(out, quality=86); print(' ', out, S.size)

def main():
    before, after, types, out = sys.argv[1:5]; os.makedirs(out, exist_ok=True)
    for p, names in PRESETS.items():
        rows = [[cell(os.path.join(before, n + '.png'), 'before: ' + n), cell(os.path.join(after, n + '.png'), 'after: ' + n)] for n in names]
        sheet(rows, f'{p}: preweather (left) against the weather branch (right)', os.path.join(out, f'{p}_before_after.jpg'))
    for t, (b, names) in TYPES.items():
        rows = []
        for i, n in enumerate(names):
            left = cell(os.path.join(before, b + '.png'), 'before: ' + b + ' (nearest preset)') if i == 0 else cell(None, 'before', 'no such weather before')
            rows.append([left, cell(os.path.join(types, n + '.png'), 'after: ' + n)])
        sheet(rows, f'{t}: preweather (left) against the weather branch (right)', os.path.join(out, f'{t}_type.jpg'))

if __name__ == '__main__': main()
