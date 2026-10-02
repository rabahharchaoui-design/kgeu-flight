#!/usr/bin/env python3
# Writes the REGIONS table into index.html, between "// REGIONS-START" and "// REGIONS-END"
# in the physics block, from assets/world/<id>.json (tools/build_region.py makes those).
#
#   python3 tools/gen_region_table.py           rewrite the table in index.html
#   python3 tools/gen_region_table.py --print   print it, change nothing
#
# Per region: names, the ARP origin, field elevation (m), the home runway (main), every
# runway with both ends (pavement end x,z in the JSON frame, displaced threshold m), the
# tower and ground frequencies and their radio clip ids, the tower height, the player's ramp
# spot (on the apron nearest a terminal, 60 m off the terminal edge, nose to the terminal)
# and six parking spots for the AI airliners, and the traffic flows by wind. Arizona keeps
# its hand built KGEU frame; its entry only carries names.
# All x,z here are in the JSON frame (ARP at 0,0); the game moves them by WOFF.
import json, math, os, re, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

EXTRA = {
    'rjtt': {'base': 'Tokyo Haneda', 'short': 'Haneda', 'twr': 'Tokyo Tower 118.1', 'gnd': 'Haneda Ground 121.7',
             'twrClip': 'tokyo_tower', 'gndClip': 'tokyo_ground', 'twrH': 70, 'pal': 0,
             # north flow: wind from 270 through 090 via north
             'tfc': {'from': 270, 'to': 90, 'a': [['34L', '34R'], ['05', '34R']], 'b': [['22', '23'], ['16L', '16R']]}},
    'lfpg': {'base': 'Paris CDG', 'short': 'de Gaulle', 'twr': 'de Gaulle Tower 119.25', 'gnd': 'de Gaulle Ground 121.6',
             'twrClip': 'degaulle_tower', 'gndClip': 'degaulle_ground', 'twrH': 80, 'pal': 1,
             # west flow: wind from 180 through 360 via west
             'tfc': {'from': 180, 'to': 360, 'a': [['27R', '26L'], ['27L', '26R']], 'b': [['09L', '08R'], ['09R', '08L']]}},
    'sbrj': {'base': 'Rio Santos Dumont', 'short': 'Santos Dumont', 'twr': 'Santos Dumont Tower 118.7', 'gnd': 'Santos Dumont Ground 121.9',
             'twrClip': 'santosdumont_tower', 'gndClip': 'santosdumont_ground', 'twrH': 35, 'pal': 2,
             # any wind from the south half
             'tfc': {'from': 90, 'to': 270, 'a': [['20L', '20R'], ['20L', '20R']], 'b': [['02R', '02L'], ['02R', '02L']]}},
}

def pip(poly, x, z):
    c = False; n = len(poly)
    for i in range(n):
        x1, z1 = poly[i]; x2, z2 = poly[i - 1]
        if (z1 > z) != (z2 > z) and x < (x2 - x1) * (z - z1) / (z2 - z1) + x1:
            c = not c
    return c

def near_edge(poly, x, z):
    best = (1e18, 0, 0)
    for i in range(len(poly)):
        ax, az = poly[i - 1]; bx, bz = poly[i]
        ex, ez = bx - ax, bz - az; L = ex * ex + ez * ez
        t = 0 if L == 0 else max(0, min(1, ((x - ax) * ex + (z - az) * ez) / L))
        px, pz = ax + ex * t, az + ez * t; d = math.hypot(x - px, z - pz)
        if d < best[0]: best = (d, px, pz)
    return best

def centroid(poly):
    a = cx = cz = 0
    for i in range(len(poly)):
        x1, z1 = poly[i - 1]; x2, z2 = poly[i]; f = x1 * z2 - x2 * z1
        a += f; cx += (x1 + x2) * f; cz += (z1 + z2) * f
    if abs(a) < 1e-6:
        return sum(p[0] for p in poly) / len(poly), sum(p[1] for p in poly) / len(poly)
    return cx / (3 * a), cz / (3 * a)

def bearing(x0, z0, x1, z1):
    return math.degrees(math.atan2(x1 - x0, -(z1 - z0))) % 360

def build(rid):
    d = json.load(open(os.path.join(ROOT, 'assets', 'world', rid + '.json')))
    X = EXTRA[rid]
    terms, aprons, hangars = d['terminals'], d['aprons'], d['hangars']
    blds = terms + hangars
    rw = []; home = None
    for r in d['runways']:
        le, he = r['le'], r['he']
        rw.append([le['num'], he['num'], r['len'], r['wid'], le['x'], le['z'], le['disp'], he['x'], he['z'], he['disp']])
        if d['main'] in (le['num'], he['num']):
            home = r
    hx = (home['le']['x'] + home['he']['x']) / 2; hz = (home['le']['z'] + home['he']['z']) / 2

    def clear(x, z, m):
        """on an apron, outside every building, at least m from any building edge"""
        if not any(pip(a, x, z) for a in aprons): return False
        for b in blds:
            if pip(b, x, z) or near_edge(b, x, z)[0] < m: return False
        return True

    # ramp: the apron whose centroid is nearest a terminal (weighted a little toward the home runway)
    cands = []
    for a in aprons:
        cx, cz = centroid(a)
        best = min(((near_edge(t, cx, cz), t) for t in terms), key=lambda q: q[0][0])
        cands.append((best[0][0] + 0.25 * math.hypot(cx - hx, cz - hz), a, cx, cz, best))
    cands.sort(key=lambda q: q[0])
    ramp = None
    for _, a, cx, cz, ((dd, ex, ez), t) in cands:
        ux, uz = cx - ex, cz - ez; L = math.hypot(ux, uz)
        tries = []
        if L > 1: tries += [(ex + ux / L * k, ez + uz / L * k) for k in (60, 70, 80, 90, 100, 120, 140)]
        tries.append((cx, cz))
        for x, z in tries:
            if clear(x, z, 40):
                tc = centroid(t); ramp = (x, z, bearing(x, z, tc[0], tc[1])); break
        if ramp: break
    assert ramp, rid + ': no ramp spot'

    # six airliner parking spots: gates near a terminal, pulled 50 m off its edge, nose in
    spots = []
    gates = sorted(d['gates'], key=lambda g: math.hypot(g[0] - hx, g[1] - hz))
    for g in gates:
        (dd, ex, ez), t = min(((near_edge(t, g[0], g[1]), t) for t in terms), key=lambda q: q[0][0])
        if dd > 90: continue
        ux, uz = g[0] - ex, g[1] - ez; L = math.hypot(ux, uz)
        if L < 1:
            tc = centroid(t); ux, uz = ex - tc[0], ez - tc[1]; L = math.hypot(ux, uz) or 1
        x, z = ex + ux / L * 50, ez + uz / L * 50
        if not clear(x, z, 30): continue
        if math.hypot(x - ramp[0], z - ramp[1]) < 150: continue
        if any(math.hypot(x - s[0], z - s[1]) < 90 for s in spots): continue
        spots.append((x, z, bearing(x, z, ex, ez)))
        if len(spots) == 6: break
    # too few gates near the terminals: apron centroids
    for _, a, cx, cz, _b in cands:
        if len(spots) >= 6: break
        if clear(cx, cz, 30) and math.hypot(cx - ramp[0], cz - ramp[1]) > 150 and all(math.hypot(cx - s[0], cz - s[1]) > 90 for s in spots):
            spots.append((cx, cz, ramp[2]))
    r1 = lambda v: round(v, 1)
    return {'id': rid, 'icao': d['icao'], 'name': d['name'], 'base': X['base'], 'short': X['short'], 'city': d['city'], 'country': d['country'],
            'lat': d['origin']['lat'], 'lon': d['origin']['lon'], 'elev': d['elev'], 'half': d['half'], 'main': d['main'],
            'twr': X['twr'], 'gnd': X['gnd'], 'twrClip': X['twrClip'], 'gndClip': X['gndClip'], 'rwyClip': 'rwy_' + d['main'].lower(),
            'twrH': X['twrH'], 'pal': X['pal'], 'rw': rw,
            'ramp': [r1(ramp[0]), r1(ramp[1]), round(ramp[2])], 'park': [[r1(s[0]), r1(s[1]), round(s[2])] for s in spots], 'tfc': X['tfc']}

def js(v):
    if isinstance(v, dict):
        return '{' + ','.join(k + ':' + js(x) for k, x in v.items()) + '}'
    if isinstance(v, (list, tuple)):
        return '[' + ','.join(js(x) for x in v) + ']'
    if isinstance(v, str):
        return "'" + v.replace("\\", "\\\\").replace("'", "\\'") + "'"
    if isinstance(v, bool):
        return 'true' if v else 'false'
    if isinstance(v, float) and v == int(v):
        return str(int(v))
    return str(v)

def table():
    az = {'id': 'az', 'icao': 'KGEU', 'name': 'Phoenix', 'base': 'Glendale KGEU', 'short': 'Glendale', 'city': 'Phoenix', 'country': 'USA',
          'lat': 33.52683, 'lon': -112.29517, 'elev': 326.4, 'main': '1'}
    lines = ['// generated by tools/gen_region_table.py from assets/world/*.json: do not edit by hand',
             '// rw: [lo, hi, length, width, lo x, lo z, lo displaced threshold, hi x, hi z, hi displaced threshold] (pavement ends,',
             '// JSON frame: ARP at 0,0); ramp/park: [x, z, heading deg]; tfc: flow a when the wind is from..to (clockwise), [land ends, departure ends]',
             'const REGIONS={', 'az:' + js(az) + ',']
    for rid in ('rjtt', 'lfpg', 'sbrj'):
        lines.append(rid + ':' + js(build(rid)) + ',')
    lines[-1] = lines[-1].rstrip(',')
    lines.append('};')
    return '\n'.join(lines)

if __name__ == '__main__':
    t = table()
    if '--print' in sys.argv:
        print(t); print(f'// {len(t)} bytes', file=sys.stderr); sys.exit(0)
    p = os.path.join(ROOT, 'index.html'); src = open(p).read()
    a, b = src.index('// REGIONS-START\n') + len('// REGIONS-START\n'), src.index('// REGIONS-END')
    open(p, 'w').write(src[:a] + t + '\n' + src[b:])
    print(f'REGIONS table: {len(t)} bytes written to index.html')
