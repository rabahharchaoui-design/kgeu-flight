# Build the Arizona airport layouts: Glendale (KGEU), Luke AFB (KLUF) and Sky Harbor (KPHX).
#
#   .venv/bin/python tools/build_az_airports.py
#
# Writes assets/world/az_apt.json: {kgeu:{...}, kluf:{...}, kphx:{...}}, each with
#   runways            [{ref, a:[x,z], b:[x,z], width}]   pavement ends (every OSM piece of a runway merged)
#   thresholds         [{ref, p:[x,z]}]
#   taxiways           [{ref, pts:[[x,z],...]}]            centre line polylines
#   taxilanes          [{ref, pts}]
#   aprons             [{ref, ring}]                       outer rings (multipolygons stitched)
#   terminals          [{name, ring}]
#   hangars            [{name, ring}]
#   gates              [{ref, p}]
#   parking_positions  [{ref, p}]   p is the stand's stop point (the last node of a stand line)
#   holding_positions  [{ref, p} or {ref, pts}]
#   stopways           [{ref, pts}]
#   windsocks          [[x,z],...]
#   tower              [x,z] or null (the airport control tower's footprint centroid)
#   aerodrome          ring (the largest outer ring of the aerodrome boundary)
#
# Build time only, like tools/build_region.py: the game does not load this file yet.
# Source: the cached Overpass answers tools/.osm-cache/q-<icao>-airport.json (OpenStreetMap, ODbL),
# every "aeroway" feature within a few km of each ARP, with geometry.
#
# World frame: the game's geoW (index.html): metres, +X east, -Z north,
#   x = GEO0.x + (lon + 112.29517) * 111320 * cos(33.52683 deg)
#   z = GEO0.z - (lat - 33.52683) * 110950
# GEO0 is the KGEU runway midpoint, wX(RWY_LEN/2, 0) and wZ(RWY_LEN/2, 0) in the game.
# Coordinates rounded to 0.1 m.
import json, math, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, 'tools', '.osm-cache')
OUT = os.path.join(ROOT, 'assets', 'world', 'az_apt.json')

GEO0 = (477.60536442669985, -979.2361134429425)
LAT0, LON0 = 33.52683, -112.29517
KX = 111320 * math.cos(math.radians(LAT0))
KZ = 110950


# runway width where OSM has no width tag: the FAA 5010 width (KGEU 1/19 is 100 ft)
WIDTH = {'kgeu': 30.5}


def geo(lat, lon):
    return [round(GEO0[0] + (lon - LON0) * KX, 1), round(GEO0[1] - (lat - LAT0) * KZ, 1)]


def pts_of(g):
    return [geo(p['lat'], p['lon']) for p in g]


def centroid(pts):
    n = len(pts) - 1 if len(pts) > 2 and pts[0] == pts[-1] else len(pts)
    a = cx = cz = 0.0
    for i in range(n):
        x0, z0 = pts[i]; x1, z1 = pts[(i + 1) % n]
        c = x0 * z1 - x1 * z0
        a += c; cx += (x0 + x1) * c; cz += (z0 + z1) * c
    if abs(a) < 1e-6:
        return [round(sum(p[0] for p in pts[:n]) / n, 1), round(sum(p[1] for p in pts[:n]) / n, 1)]
    return [round(cx / (3 * a), 1), round(cz / (3 * a), 1)]


def stitch(ways):
    """join open ways into closed rings by their end points"""
    ways = [list(w) for w in ways if len(w) > 1]
    rings = []
    while ways:
        cur = ways.pop(0)
        changed = True
        while cur[0] != cur[-1] and changed:
            changed = False
            for i, w in enumerate(ways):
                if w[0] == cur[-1]: cur += w[1:]
                elif w[-1] == cur[-1]: cur += w[::-1][1:]
                elif w[-1] == cur[0]: cur = w[:-1] + cur
                elif w[0] == cur[0]: cur = w[::-1][:-1] + cur
                else: continue
                ways.pop(i); changed = True; break
        rings.append(cur)
    return rings


def area(r):
    return abs(sum(r[i][0] * r[(i + 1) % len(r)][1] - r[(i + 1) % len(r)][0] * r[i][1] for i in range(len(r)))) / 2


def norm_ref(r):
    # '7L / 25R' -> '07L/25R'
    parts = [p.strip() for p in (r or '').replace(' ', '').split('/')]
    out = []
    for p in parts:
        d = ''.join(c for c in p if c.isdigit()); s = p[len(d):]
        out.append((d.zfill(2) if d else '') + s)
    return '/'.join(out)


def build(icao):
    d = json.load(open(os.path.join(CACHE, 'q-%s-airport.json' % icao)))
    o = {k: [] for k in ('runways', 'thresholds', 'taxiways', 'taxilanes', 'aprons', 'terminals', 'hangars', 'gates',
                         'parking_positions', 'holding_positions', 'stopways', 'windsocks')}
    o['tower'] = None; o['aerodrome'] = None
    rw = {}
    for e in d['elements']:
        t = e.get('tags', {}); aw = t.get('aeroway'); ref = t.get('ref') or t.get('name') or ''
        if e['type'] == 'node':
            p = geo(e['lat'], e['lon'])
            if aw == 'gate': o['gates'].append({'ref': ref, 'p': p})
            elif aw == 'parking_position': o['parking_positions'].append({'ref': ref, 'p': p})
            elif aw == 'holding_position': o['holding_positions'].append({'ref': ref, 'p': p})
            elif aw == 'windsock': o['windsocks'].append(p)
            elif aw == 'threshold': o['thresholds'].append({'ref': norm_ref(ref), 'p': p})
            elif aw == 'control_tower' or t.get('tower:type') == 'airport_control': o['tower'] = p
            continue
        if e['type'] == 'way':
            g = pts_of(e.get('geometry') or [])
            if not g: continue
            if aw == 'runway':
                k = norm_ref(ref)
                R = rw.setdefault(k, {'ref': k, 'pts': [], 'width': None})
                R['pts'] += g
                if t.get('width'):
                    try: R['width'] = float(t['width'])
                    except ValueError: pass
            elif aw == 'taxiway': o['taxiways'].append({'ref': ref, 'pts': g})
            elif aw == 'taxilane': o['taxilanes'].append({'ref': ref, 'pts': g})
            elif aw == 'apron': o['aprons'].append({'ref': ref, 'ring': g})
            elif aw == 'terminal': o['terminals'].append({'name': t.get('name', ''), 'ring': g})
            elif aw == 'hangar' or t.get('building') == 'hangar': o['hangars'].append({'name': t.get('name', t.get('operator', '')), 'ring': g})
            elif aw == 'parking_position': o['parking_positions'].append({'ref': ref, 'p': g[-1]})
            elif aw == 'holding_position': o['holding_positions'].append({'ref': ref, 'pts': g})
            elif aw == 'stopway': o['stopways'].append({'ref': norm_ref(ref), 'pts': g})
            elif aw == 'windsock': o['windsocks'].append(centroid(g))
            elif aw == 'aerodrome': o['aerodrome'] = g
            elif aw == 'control_tower' or t.get('tower:type') == 'airport_control': o['tower'] = centroid(g)
            continue
        if e['type'] == 'relation':
            outer = [pts_of(m['geometry']) for m in e.get('members', []) if m.get('role') == 'outer' and m.get('geometry')]
            rings = stitch(outer)
            if aw == 'apron':
                for r in rings: o['aprons'].append({'ref': ref, 'ring': r})
            elif aw == 'aerodrome' and rings:
                o['aerodrome'] = max(rings, key=area)
    # a runway's pavement ends: the two extreme points along its principal axis
    for k, R in sorted(rw.items()):
        P = R['pts']; mx = sum(p[0] for p in P) / len(P); mz = sum(p[1] for p in P) / len(P)
        a = max(P, key=lambda p: (p[0] - mx) ** 2 + (p[1] - mz) ** 2)
        b = max(P, key=lambda p: (p[0] - a[0]) ** 2 + (p[1] - a[1]) ** 2)
        lo = k.split('/')[0]; hdg = int(''.join(c for c in lo if c.isdigit()) or 0) * 10
        # a is the low numbered end: the one you land from on heading lo (bearing a->b about lo*10)
        brg = math.degrees(math.atan2(b[0] - a[0], -(b[1] - a[1]))) % 360
        if abs(((brg - hdg + 180) % 360) - 180) > 90: a, b = b, a
        o['runways'].append({'ref': k, 'a': a, 'b': b, 'width': R['width'] or WIDTH.get(icao, 45)})
    return o


def main():
    out = {}
    for icao in ('kgeu', 'kluf', 'kphx'):
        o = build(icao); out[icao] = o
        print('%s: ' % icao.upper() + ', '.join('%s %d' % (k, len(v)) for k, v in o.items() if isinstance(v, list) and k not in ('aerodrome', 'tower'))
              + ', tower %s, aerodrome %s' % ('yes' if o['tower'] else 'no', len(o['aerodrome']) if o['aerodrome'] else 'none'))
        for r in o['runways']:
            L = math.hypot(r['b'][0] - r['a'][0], r['b'][1] - r['a'][1])
            print('   runway %-8s %6.0f m x %2.0f  %s -> %s' % (r['ref'], L, r['width'], r['a'], r['b']))
    with open(OUT, 'w') as f:
        json.dump(out, f, separators=(',', ':'))
    print('wrote', os.path.relpath(OUT, ROOT), os.path.getsize(OUT), 'bytes')


if __name__ == '__main__':
    main()
