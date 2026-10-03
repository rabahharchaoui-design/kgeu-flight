# World region data check (item 4.5). Pure Python, no browser.
#
#   .venv/bin/python tests/world_data_check.py
#
# Validates assets/world/{rjtt,lfpg,sbrj}.json and assets/map/{rjtt,lfpg,sbrj}.bin
# written by tools/build_region.py, and that assets/map/phx.bin is byte identical
# to the committed one (git show HEAD:assets/map/phx.bin).
import base64, json, math, os, struct, subprocess, sys, zlib

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
fails = []

def check(ok, msg):
    print(('  ok   ' if ok else '  FAIL ') + msg)
    if not ok:
        fails.append(msg)

# runway lengths (m) expected per airport, +-30 m
RUNWAYS = {
    'rjtt': {'16R/34L': 3000, '16L/34R': 3360, '04/22': 2500, '05/23': 2500},
    'lfpg': None,   # two about 4,200 m and two about 2,700 m
    'sbrj': None,   # about 1,323 m and 1,260 m
}
# true heading window for the player's runway end. Note: the spec's windows assumed
# east variation everywhere. OurAirports' thresholds give RJTT 34R ~330 T (7.5 W),
# LFPG 26L ~265 T (1 E) and SBRJ 20L ~177 T (23 W: magnetic 200 minus 23), so the
# windows here bracket the real true headings.
HDG = {'rjtt': ('34R', 325, 340), 'lfpg': ('26L', 255, 270), 'sbrj': ('20L', 170, 185)}
WATER = {'rjtt': (0.15, 0.6), 'lfpg': (0.0, 0.05), 'sbrj': (0.2, 0.7)}

def inflate(b64):
    return zlib.decompress(base64.b64decode(b64))

# ---------- KGM2 reader, mirroring tools/build_map_data.py's writer ----------
def read_kgm2(b):
    o = [0]
    def u8():
        v = b[o[0]]; o[0] += 1; return v
    def un(fmt, n):
        v = struct.unpack_from(fmt, b, o[0])[0]; o[0] += n; return v
    def var():
        r = s = 0
        while True:
            c = u8(); r |= (c & 127) << s; s += 7
            if not c & 128:
                break
        return (r >> 1) ^ -(r & 1)
    def line():
        n = var(); x = z = 0; out = []
        for _ in range(n):
            x += var(); z += var(); out.append((x * Q, z * Q))
        return out
    def lst():
        return [line() for _ in range(un('<I', 4))]
    assert b[:4] == b'KGM2', 'magic'
    o[0] = 4
    Q = un('<H', 2) / 100; u8()
    d = {'roads': {}, 'shields': [], 'polys': {}, 'wlines': {}}
    for _ in range(u8()):
        c = u8(); d['roads'][c] = lst()
    for _ in range(un('<H', 2)):
        x, z = un('<h', 2) * Q, un('<h', 2) * Q; L = u8()
        d['shields'].append((x, z, bytes(b[o[0]:o[0] + L]).decode())); o[0] += L
    for _ in range(u8()):
        k = u8(); d['polys'][k] = lst()
    for _ in range(u8()):
        k = u8(); d['wlines'][k] = lst()
    d['taxi'] = lst(); d['apron'] = lst()
    W, H, G = un('<H', 2), un('<H', 2), un('<H', 2)
    gx, gz = un('<h', 2) * Q, un('<h', 2) * Q; L = un('<I', 4)
    d['urban'] = (W, H, G, gx, gz, zlib.decompress(bytes(b[o[0]:o[0] + L])))
    o[0] += L
    d['end'] = o[0] == len(b)
    return d

# ---------- phx.bin unchanged ----------
print('phx.bin')
head = subprocess.run(['git', 'show', 'HEAD:assets/map/phx.bin'], cwd=ROOT, capture_output=True).stdout
cur = open(os.path.join(ROOT, 'assets', 'map', 'phx.bin'), 'rb').read()
check(len(head) > 0 and head == cur, f'phx.bin byte identical to HEAD ({len(cur)} bytes)')
check(read_kgm2(cur)['end'], 'phx.bin parses to its end with the test reader')

for rid in ('rjtt', 'lfpg', 'sbrj'):
    print(rid)
    jp = os.path.join(ROOT, 'assets', 'world', rid + '.json')
    bp = os.path.join(ROOT, 'assets', 'map', rid + '.bin')
    if not os.path.exists(jp) or not os.path.exists(bp):
        check(False, f'{rid}: json and bin exist'); continue
    js = json.load(open(jp, encoding='utf8'))
    check(True, f'{rid}.json parses')
    check(os.path.getsize(jp) < 350 * 1024, f'{rid}.json {os.path.getsize(jp)/1024:.0f} KB < 350 KB')
    check(os.path.getsize(bp) < 900 * 1024, f'{rid}.bin {os.path.getsize(bp)/1024:.0f} KB < 900 KB')
    half = js['half']
    rws = js['runways']
    lens = sorted(r['len'] for r in rws)
    if rid == 'rjtt':
        got = {r['id']: r['len'] for r in rws}
        check(len(rws) == 4 and all(k in got and abs(got[k] - v) <= 30 for k, v in RUNWAYS[rid].items()),
              f'RJTT runways {got}')
    elif rid == 'lfpg':
        check(len(rws) == 4 and all(abs(l - 2700) <= 30 for l in lens[:2]) and all(abs(l - 4200) <= 30 for l in lens[2:]),
              f'LFPG runways {lens}')
    else:
        check(len(rws) == 2 and abs(lens[0] - 1260) <= 30 and abs(lens[1] - 1323) <= 30, f'SBRJ runways {lens}')
    for r in rws:
        d = abs((r['le']['hdgT'] - r['he']['hdgT']) % 360 - 180)
        check(d < 0.2, f"{r['id']} ends differ by 180 ({r['le']['hdgT']} / {r['he']['hdgT']})")
    num, lo, hi = HDG[rid]
    end = [e for r in rws for e in (r['le'], r['he']) if e['num'] == num]
    check(len(end) == 1 and lo <= end[0]['hdgT'] <= hi, f'{num} true heading {end[0]["hdgT"] if end else None} in {lo}..{hi}')
    check(js['main'] == num, f'main runway {js["main"]}')
    if rid == 'sbrj':
        longest = max(rws, key=lambda r: r['len'])
        check(num in longest['id'], f'SBRJ main {num} is on the longer runway {longest["id"]}')
    check(len(js['taxiways']) > 20, f'taxiways {len(js["taxiways"])} > 20')
    check(len(js['terminals']) >= 1, f'terminals {len(js["terminals"])}')
    t = js['terrain']
    h = inflate(t['b64']); m = inflate(t['waterB64'])
    check(len(h) == 2 * t['w'] * t['h'] and len(m) == t['w'] * t['h'] and t['w'] * t['cell'] == 2 * half,
          f"terrain {t['w']}x{t['h']} at {t['cell']} m")
    wf = sum(m) / len(m); lo, hi = WATER[rid]
    check(lo <= wf <= hi, f'water fraction {wf:.3f} in {lo}..{hi}')
    hs = struct.unpack(f'<{t["w"]*t["h"]}h', h)
    check(min(hs) >= 0, f'terrain heights >= 0 (max {max(hs)} m)')
    u = js['urban']
    check(len(inflate(u['b64'])) == u['w'] * u['h'], f"urban grid {u['w']}x{u['h']}")
    for l in js['landmarks']:
        inside = abs(l['x']) <= half and abs(l['z']) <= half
        if l['id'] == 'fuji':
            check(not inside, 'Mount Fuji kept at its true position outside the bbox')
        else:
            check(inside, f"landmark {l['name']} inside the bbox ({l['x']:.0f}, {l['z']:.0f})")
    b = open(bp, 'rb').read()
    check(b[:4] == b'KGM2', f'{rid}.bin starts with KGM2')
    try:
        d = read_kgm2(b)
        nroads = sum(len(v) for v in d['roads'].values())
        W, H, G, gx, gz, g = d['urban']
        check(d['end'] and nroads > 0 and len(d['taxi']) > 0 and len(d['apron']) > 0 and len(g) == W * H > 0,
              f'{rid}.bin parses: roads {nroads}, taxiways {len(d["taxi"])}, aprons {len(d["apron"])}, urban {W}x{H}')
    except Exception as e:
        check(False, f'{rid}.bin parses ({e})')

print('\nworld_data_check:', 'PASS' if not fails else f'FAIL ({len(fails)})')
sys.exit(1 if fails else 0)
