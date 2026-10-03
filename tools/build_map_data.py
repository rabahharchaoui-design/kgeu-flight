# Build the full screen map's vector data from OpenStreetMap.
#
# Runs at build time only. The live game never talks to Overpass: it loads the
# compact file this writes, assets/map/<id>.bin, and nothing else.
#
#   python3 tools/build_map_data.py            fetch (cached) and write assets/map/phx.bin
#   python3 tools/build_map_data.py --refetch  ignore the cache and ask Overpass again
#   python3 tools/build_map_data.py --region rjtt|lfpg|sbrj
#       a world region from tools/regions.py; writes assets/map/<id>.bin. Its runways
#       come from assets/world/<id>.json, so run tools/build_region.py (which calls
#       this) rather than this directly for a fresh region.
#
# Map data (c) OpenStreetMap contributors, ODbL. The credit is in Settings.
#
# World frame: metres, +X east, +Z south, from the KGEU ARP (the same flat
# projection tests/luke_check.js and tests/landmark_check.js use to site Luke,
# Sky Harbor and the landmarks), so the roads line up with the game's airports.
import hashlib, json, math, os, struct, sys, time, urllib.parse, urllib.request, zlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import regions

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
CACHE = os.environ.get('KGEU_OSM_CACHE', os.path.join(ROOT, 'tools', '.osm-cache'))
OUT = os.path.join(ROOT, 'assets', 'map', 'phx.bin')
OVERPASS = 'https://overpass-api.de/api/interpreter'
# tried in order; the first one that answers wins (the main one often turns a request down)
MIRRORS = [OVERPASS, 'https://lz4.overpass-api.de/api/interpreter',
           'https://overpass.private.coffee/api/interpreter', 'https://overpass.kumi.systems/api/interpreter']
UA = 'kgeu-map-build/1.0 (build time only)'
# the region being built: Phoenix unless setup() picks a world region
REGION = 'phx'
PREFIX = ''        # cache file prefix ('' for Phoenix, '<id>-' for the others)
AERO_R = 3500      # airport feature radius around the runways' middle
ACC5 = None        # world regions: residential street length per urban cell, summed tile by tile

KGEU = (33.52683, -112.29517)
RH = 26 * math.pi / 180
ARP_X, ARP_Z = math.sin(RH) * 2179 / 2, -math.cos(RH) * 2179 / 2
MPD_LAT, MPD_LON = 110950.0, 111320.0 * math.cos(KGEU[0] * math.pi / 180)
# Map extent in world metres: the White Tanks to past Camelback, Hedgpeth Hills
# to the Estrellas. The 3D terrain is 64 km square around KGEU.
X0, X1, Z0, Z1 = -34000, 38000, -28000, 30000
Q = 2.0   # metres per stored unit: coordinates are 2 m integers, delta and varint coded

def setup(rid):
    """Point the builder at a world region from tools/regions.py: origin at its ARP,
    a square bbox of +-half metres, output assets/map/<id>.bin. Phoenix needs no call."""
    global REGION, PREFIX, KGEU, ARP_X, ARP_Z, MPD_LAT, MPD_LON, X0, X1, Z0, Z1, OUT, AERO_R
    if rid in (None, 'phx'):
        return
    r = regions.get(rid)
    REGION, PREFIX = rid, rid + '-'
    KGEU = r['origin']; ARP_X = ARP_Z = 0.0
    MPD_LAT, MPD_LON = 110950.0, 111320.0 * math.cos(KGEU[0] * math.pi / 180)
    X0, X1, Z0, Z1 = -r['half'], r['half'], -r['half'], r['half']
    OUT = os.path.join(ROOT, 'assets', 'map', rid + '.bin')
    AERO_R = 4500

def world(lat, lon):
    return ARP_X + (lon - KGEU[1]) * MPD_LON, ARP_Z - (lat - KGEU[0]) * MPD_LAT

def bbox():
    lat_n = KGEU[0] + (ARP_Z - Z0) / MPD_LAT
    lat_s = KGEU[0] + (ARP_Z - Z1) / MPD_LAT
    lon_w = KGEU[1] + (X0 - ARP_X) / MPD_LON
    lon_e = KGEU[1] + (X1 - ARP_X) / MPD_LON
    return f'{lat_s:.5f},{lon_w:.5f},{lat_n:.5f},{lon_e:.5f}'

QUERIES = {
    'fwy':   'way["highway"~"^(motorway|motorway_link|trunk_link)$"]',
    'major': 'way["highway"~"^(trunk|primary|secondary)$"]',
    'local': 'way["highway"~"^(tertiary|unclassified|residential)$"]',
    'water': ('(way["natural"="water"];relation["natural"="water"];way["landuse"="reservoir"];'
              'way["waterway"~"^(river|canal)$"];)'),
    'aero':  ('(way["aeroway"~"^(runway|taxiway|apron)$"];)'),
    'green': ('(way["leisure"~"^(park|golf_course)$"];relation["leisure"~"^(park|golf_course)$"];)'),
}

# world regions: rivers mapped as areas the older way, and reservoirs as relations, too
QUERIES_WORLD = dict(QUERIES, water=('(way["natural"="water"];relation["natural"="water"];way["landuse"="reservoir"];'
                                     'relation["landuse"="reservoir"];way["waterway"="riverbank"];'
                                     'relation["waterway"="riverbank"];way["waterway"~"^(river|canal)$"];)'))
LAST_MIRROR = None

def overpass(body, path, label, refetch=False, timeout=180):
    """POST one Overpass query (form body data=..., with a User-Agent), cached raw at path.
    Each attempt walks the mirror list; a failure moves on to the next mirror."""
    global LAST_MIRROR
    if os.path.exists(path) and not refetch:
        return json.load(open(path))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    for attempt in range(3):
        # the mirror that answered last goes first (a hung one costs a full timeout)
        for url in ([LAST_MIRROR] if LAST_MIRROR else []) + [m for m in MIRRORS if m != LAST_MIRROR]:
            try:
                req = urllib.request.Request(url, data=urllib.parse.urlencode({'data': body}).encode(),
                                             headers={'User-Agent': UA, 'Accept': '*/*'})
                raw = urllib.request.urlopen(req, timeout=timeout).read()
                if not raw.lstrip().startswith(b'{'):
                    raise ValueError('not JSON: ' + raw[:120].decode('utf8', 'replace'))
                js = json.loads(raw)
                if 'remark' in js and 'error' in js['remark'].lower():
                    raise ValueError(js['remark'][:200])
                open(path, 'wb').write(raw)
                LAST_MIRROR = url
                print(f'  fetched {label} from {url}: {len(raw)/1e6:.1f} MB')
                return js
            except Exception as e:
                print(f'  {label} @ {url}: {str(e)[:160]}')
        time.sleep(15 * (attempt + 1))
    sys.exit(f'Overpass failed for {label}')

def tiles(n):
    """The bbox cut into n x n Overpass bboxes (big street queries in dense cities)."""
    lat_s, lon_w, lat_n, lon_e = map(float, bbox().split(','))
    for j in range(n):
        for i in range(n):
            yield (j * n + i, f'{lat_s + (lat_n - lat_s) * j / n:.5f},{lon_w + (lon_e - lon_w) * i / n:.5f},'
                              f'{lat_s + (lat_n - lat_s) * (j + 1) / n:.5f},{lon_w + (lon_e - lon_w) * (i + 1) / n:.5f}')

def fetch_tile(name, bb, idx, refetch):
    q = QUERIES_WORLD[name] + ';'
    body = f'[out:json][timeout:180][bbox:{bb}];{q}out tags geom qt;'
    return overpass(body, os.path.join(CACHE, f'{PREFIX}{name}-{idx}.json'), f'{PREFIX}{name} tile {idx}', refetch)

def fetch(name, refetch):
    os.makedirs(CACHE, exist_ok=True)
    if REGION != 'phx':
        # multipolygons need 'out body' to come with their member rings ('out tags' drops
        # them, so Phoenix has no relation water or parks); ways only layers stay lean
        rel = name in ('water', 'green')
        q = QUERIES_WORLD[name] + ';'
        body = f'[out:json][timeout:180][bbox:{bbox()}];{q}out {"body" if rel else "tags"} geom qt;'
        path = os.path.join(CACHE, PREFIX + name + ('-body' if rel else '') + '.json')
        return overpass(body, path, PREFIX + name, refetch)
    path = os.path.join(CACHE, PREFIX + name + '.json')
    if os.path.exists(path) and not refetch:
        return json.load(open(path))
    q = QUERIES[name] + ';'
    body = f'[out:json][timeout:300][bbox:{bbox()}];{q}out tags geom qt;'
    for attempt in range(4):
        try:
            req = urllib.request.Request(OVERPASS, data=urllib.parse.urlencode({'data': body}).encode(),
                                         headers={'User-Agent': 'kgeu-map-build/1.0 (build time only)'})
            raw = urllib.request.urlopen(req, timeout=400).read()
            open(path, 'wb').write(raw)
            print(f'  fetched {name}: {len(raw)/1e6:.1f} MB')
            return json.loads(raw)
        except Exception as e:
            print(f'  {name}: {e}, retrying')
            time.sleep(20 * (attempt + 1))
    sys.exit(f'Overpass failed for {name}')

# ---------- geometry ----------
def dp(pts, tol):
    """Douglas-Peucker, iterative."""
    if len(pts) < 3:
        return pts
    keep = [False] * len(pts); keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        a, b = stack.pop()
        ax, az = pts[a]; bx, bz = pts[b]; dx, dz = bx - ax, bz - az; L = math.hypot(dx, dz) or 1e-9
        best, bi = -1, -1
        for i in range(a + 1, b):
            px, pz = pts[i]
            d = abs(dx * (az - pz) - dz * (ax - px)) / L
            if d > best:
                best, bi = d, i
        if best > tol:
            keep[bi] = True; stack += [(a, bi), (bi, b)]
    return [p for p, k in zip(pts, keep) if k]

def dp_ring(pts, tol):
    """Douglas-Peucker for a closed ring: plain dp() measures from the first point to the
    last, which are the same point on a closed OSM way, so it keeps only those two.
    Split at the vertex farthest from the start and simplify both halves."""
    if len(pts) > 1 and pts[0] == pts[-1]:
        pts = pts[:-1]
    if len(pts) < 4:
        return list(pts)
    x0, z0 = pts[0]
    m = max(range(len(pts)), key=lambda i: (pts[i][0] - x0) ** 2 + (pts[i][1] - z0) ** 2)
    return dp(pts[:m + 1], tol)[:-1] + dp(pts[m:] + [pts[0]], tol)[:-1]

def length(pts):
    return sum(math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]) for i in range(len(pts) - 1))

def clip_ok(pts):
    return any(X0 <= x <= X1 and Z0 <= z <= Z1 for x, z in pts)

def geom(el):
    return [world(g['lat'], g['lon']) for g in el.get('geometry', []) if g]

def merge_lines(lines):
    """Join ways that share end points into longer polylines (fewer draw calls, cleaner strokes)."""
    key = lambda p: (round(p[0]), round(p[1]))
    ends = {}
    for i, l in enumerate(lines):
        ends.setdefault(key(l[0]), []).append(i); ends.setdefault(key(l[-1]), []).append(i)
    used = [False] * len(lines); out = []
    for i in range(len(lines)):
        if used[i]:
            continue
        used[i] = True; cur = list(lines[i])
        for _ in range(2):
            while True:
                nxt = None
                for j in ends.get(key(cur[-1]), []):
                    if not used[j]:
                        nxt = j; break
                if nxt is None:
                    break
                used[nxt] = True; l = lines[nxt]
                cur += (l[1:] if key(l[0]) == key(cur[-1]) else l[::-1][1:])
            cur.reverse()
        out.append(cur)
    return out

# ---------- road classes ----------
SHIELDS = {'I 10': 'I-10', 'I 17': 'I-17', 'SR 101': '101', 'SR 303': '303', 'SR 202': '202'}

def route_of(tags):
    for r in (tags.get('ref') or '').split(';'):
        r = r.strip().replace('I-', 'I ').replace(' Loop', '').replace('AZ ', 'SR ').replace('Loop ', 'SR ')
        if r in SHIELDS:
            return SHIELDS[r]
    return None

GRID = 250   # metres per cell (urban density grid)

def add_density(acc, pts, W, H):
    for i in range(len(pts) - 1):
        (ax, az), (bx, bz) = pts[i], pts[i + 1]
        seg = math.hypot(bx - ax, bz - az); n = max(1, int(seg / 60))
        for k in range(n):
            x = ax + (bx - ax) * (k + 0.5) / n; z = az + (bz - az) * (k + 0.5) / n
            gi, gj = int((x - X0) // GRID), int((z - Z0) // GRID)
            if 0 <= gi < W and 0 <= gj < H:
                acc[gj * W + gi] += seg / n

def world_local(cls, refetch):
    """Dense cities: tertiary lines kept for the map, residential streets only counted
    into the density grid (all of Tokyo's streets would be hundreds of MB and too
    much for the map file), one Overpass tile at a time."""
    global ACC5
    W, H = (X1 - X0) // GRID, (Z1 - Z0) // GRID
    ACC5 = [0.0] * (W * H)
    seen = set()   # a way crossing a tile edge comes back from both tiles
    for idx, bb in tiles(regions.get(REGION).get('tiles', 4)):
        for el in fetch_tile('local', bb, idx, refetch)['elements']:
            if el['type'] != 'way' or el['id'] in seen:
                continue
            seen.add(el['id'])
            hw = el['tags'].get('highway', '')
            pts = geom(el)
            if len(pts) < 2:
                continue
            if hw == 'tertiary':
                if clip_ok(pts):
                    cls.setdefault(4, []).append((pts, None))
            elif hw in ('unclassified', 'residential'):
                add_density(ACC5, pts, W, H)

def roads(refetch):
    cls = {}
    if REGION != 'phx':
        for layer in ('fwy', 'major'):
            for el in fetch(layer, refetch)['elements']:
                if el['type'] != 'way':
                    continue
                c = {'motorway': 0, 'trunk': 1, 'primary': 1, 'secondary': 2, 'motorway_link': 3,
                     'trunk_link': 3}.get(el['tags'].get('highway', ''))
                pts = geom(el)
                if c is not None and len(pts) >= 2 and clip_ok(pts):
                    cls.setdefault(c, []).append((pts, None))
        world_local(cls, refetch)
        return cls
    for layer in ('fwy', 'major', 'local'):
        for el in fetch(layer, refetch)['elements']:
            if el['type'] != 'way':
                continue
            hw = el['tags'].get('highway', '')
            c = {'motorway': 0, 'trunk': 1, 'primary': 1, 'secondary': 2, 'motorway_link': 3, 'trunk_link': 3,
                 'tertiary': 4, 'unclassified': 5, 'residential': 5}.get(hw)
            if c is None:
                continue
            pts = geom(el)
            if len(pts) >= 2 and clip_ok(pts):
                cls.setdefault(c, []).append((pts, route_of(el['tags']) if c == 0 else None))
    return cls

def shields(fwy):
    """Label anchors for the five named freeways: one every ~9 km along each route."""
    out = []
    by = {}
    for pts, ref in fwy:
        if ref:
            by.setdefault(ref, []).append(pts)
    for ref, lines in sorted(by.items()):
        placed = []
        for l in sorted(merge_lines(lines), key=length, reverse=True):
            acc = 4000.0
            for i in range(len(l) - 1):
                (ax, az), (bx, bz) = l[i], l[i + 1]
                seg = math.hypot(bx - ax, bz - az); t = 0
                while acc + seg - t >= 9000:
                    t += 9000 - acc; acc = 0
                    x, z = ax + (bx - ax) * t / seg, az + (bz - az) * t / seg
                    if X0 < x < X1 and Z0 < z < Z1 and all(math.hypot(x - p[0], z - p[1]) > 6000 for p in placed):
                        placed.append((x, z))
                acc += seg - t
        # a route too short for the spacing still gets one shield at its middle
        if not placed:
            l = max(merge_lines(lines), key=length); placed.append(l[len(l) // 2])
        out += [(x, z, ref) for x, z in placed]
    return out

# ---------- land cover grid: urban (road density) ----------
def urban_grid(cls):
    W, H = (X1 - X0) // GRID, (Z1 - Z0) // GRID
    acc = [0.0] * (W * H) if ACC5 is None else list(ACC5)
    for c in (1, 2, 4, 5):
        for pts, _ in cls.get(c, []):
            for i in range(len(pts) - 1):
                (ax, az), (bx, bz) = pts[i], pts[i + 1]
                seg = math.hypot(bx - ax, bz - az); n = max(1, int(seg / 60))
                for k in range(n):
                    x = ax + (bx - ax) * (k + 0.5) / n; z = az + (bz - az) * (k + 0.5) / n
                    gi, gj = int((x - X0) // GRID), int((z - Z0) // GRID)
                    if 0 <= gi < W and 0 <= gj < H:
                        acc[gj * W + gi] += seg / n
    # a 250 m cell of houses carries 1 to 2 km of street; open desert has one road or none
    return W, H, bytes(min(255, int(v / 1400 * 255)) for v in acc)

# ---------- airports: taxiways and aprons, fitted to the game's runways ----------
def game_runways():
    """Runway centre lines as the game builds them, read from index.html's physics section with node."""
    import subprocess
    js = r'''
const THREE=require(process.argv[1]+'/node_modules/three');global.THREE=THREE;
const src=require('fs').readFileSync(process.argv[1]+'/index.html','utf8');
const phys=src.split('// PHYSICS-START')[1].split('// PHYSICS-END')[0];
const a=new Function('THREE',phys+'\nreturn {RWY_LEN,RH,wX,wZ,LUKE,LUKE_RWY,lkX,lkZ,SKY_HARBOR,SH_RWY,shX,shZ};')(THREE);
const out={KGEU:[[a.wX(0,0),a.wZ(0,0),a.wX(a.RWY_LEN,0),a.wZ(a.RWY_LEN,0)]],KLUF:[],KPHX:[]};
for(const r of a.LUKE_RWY)out.KLUF.push([a.lkX(-r.len/2,r.v),a.lkZ(-r.len/2,r.v),a.lkX(r.len/2,r.v),a.lkZ(r.len/2,r.v)]);
for(const r of a.SH_RWY)out.KPHX.push([a.shX(-r.len/2,r.v),a.shZ(-r.len/2,r.v),a.shX(r.len/2,r.v),a.shZ(r.len/2,r.v)]);
console.log(JSON.stringify(out));'''
    return json.loads(subprocess.check_output(['node', '-e', js, ROOT]))

def region_runways():
    """World regions: runway centre lines from assets/world/<id>.json (OurAirports thresholds)."""
    js = json.load(open(os.path.join(ROOT, 'assets', 'world', REGION + '.json')))
    return {js['icao']: [[r['le']['x'], r['le']['z'], r['he']['x'], r['he']['z']] for r in js['runways']]}

def osm_fit(osm_rwy, rws):
    """Average offset from the OSM runway middles to the given runways (None if none match)."""
    osm_rwy = merge_lines(osm_rwy)   # long runways are often mapped in pieces (LFPG)
    offs = []
    for r in rws:
        gx, gz = (r[0] + r[2]) / 2, (r[1] + r[3]) / 2
        best = min(osm_rwy, key=lambda l: math.hypot((l[0][0] + l[-1][0]) / 2 - gx, (l[0][1] + l[-1][1]) / 2 - gz))
        mx, mz = (best[0][0] + best[-1][0]) / 2, (best[0][1] + best[-1][1]) / 2
        if math.hypot(mx - gx, mz - gz) < 600:
            offs.append((gx - mx, gz - mz))
    if not offs:
        return None
    return sum(o[0] for o in offs) / len(offs), sum(o[1] for o in offs) / len(offs)

def airports(refetch):
    """Taxiway lines and apron polygons near each game airport, moved by that airport's
    offset between the OSM runways and the game's own runways (the game sites each
    field from its published reference point, so the two can differ by tens of metres)."""
    game = game_runways() if REGION == 'phx' else region_runways()
    els = fetch('aero', refetch)['elements']
    osm_rwy = [geom(e) for e in els if e['tags'].get('aeroway') == 'runway' and len(e.get('geometry', [])) >= 2]
    if REGION != 'phx':
        osm_rwy = merge_lines(osm_rwy)   # long runways are often mapped in pieces (LFPG)
    taxi, apron = [], []
    for code, rws in game.items():
        gc = [((r[0] + r[2]) / 2, (r[1] + r[3]) / 2) for r in rws]
        cx = sum(p[0] for p in gc) / len(gc); cz = sum(p[1] for p in gc) / len(gc)
        # match every game runway to the nearest OSM runway middle, average the offsets
        offs = []
        for gx, gz in gc:
            best = min(osm_rwy, key=lambda l: math.hypot((l[0][0] + l[-1][0]) / 2 - gx, (l[0][1] + l[-1][1]) / 2 - gz))
            mx, mz = (best[0][0] + best[-1][0]) / 2, (best[0][1] + best[-1][1]) / 2
            if math.hypot(mx - gx, mz - gz) < 600:
                offs.append((gx - mx, gz - mz))
        if not offs:
            continue
        ox = sum(o[0] for o in offs) / len(offs); oz = sum(o[1] for o in offs) / len(offs)
        print(f'  {code}: OSM runways off the game by {math.hypot(ox, oz):.0f} m, fitted')
        for e in els:
            a = e['tags'].get('aeroway')
            if a not in ('taxiway', 'apron'):
                continue
            pts = geom(e)
            if len(pts) < 2 or math.hypot(pts[0][0] - cx, pts[0][1] - cz) > AERO_R:
                continue
            pts = [(x + ox, z + oz) for x, z in pts]
            (taxi if a == 'taxiway' else apron).append(pts)
    return taxi, apron

# ---------- writer ----------
def q(v):
    return max(-32767, min(32767, int(round(v / Q))))

class Out:
    def __init__(self): self.b = bytearray()
    def u8(self, v): self.b += struct.pack('<B', v)
    def u16(self, v): self.b += struct.pack('<H', v)
    def u32(self, v): self.b += struct.pack('<I', v)
    def var(self, v):
        v = (v << 1) ^ (v >> 31)          # zigzag, then LEB128
        while v >= 0x80:
            self.b.append((v & 0x7f) | 0x80); v >>= 7
        self.b.append(v)
    def pts(self, pts):
        # point count, the first point, then each point as a delta from the last
        qs = [(q(x), q(z)) for x, z in pts]
        qs = [p for i, p in enumerate(qs) if i == 0 or p != qs[i - 1]]
        if len(qs) < 2:
            qs = qs * 2
        self.var(len(qs)); px = pz = 0
        for x, z in qs:
            self.var(x - px); self.var(z - pz); px, pz = x, z

TOL = {0: 6, 1: 8, 2: 8, 3: 5, 4: 10, 5: 10}
MINLEN = {0: 0, 1: 0, 2: 0, 3: 60, 4: 60, 5: 120}

def main(argv=None, cls=None):
    argv = sys.argv[1:] if argv is None else argv
    refetch = '--refetch' in argv
    if '--region' in argv:
        setup(argv[argv.index('--region') + 1])
    print('region', REGION, 'bbox', bbox())
    cls = roads(refetch) if cls is None else cls
    # shields are Phoenix's five named freeways; the world regions have none
    shield_pts = shields(cls.get(0, [])) if REGION == 'phx' else []
    o = Out()
    o.b += b'KGM2'
    o.u16(int(Q * 100)); o.u8(0)
    # section 1: road classes
    o.u8(len(cls))
    stats = {}
    for c in sorted(cls):
        lines = merge_lines([p for p, _ in cls[c]])
        lines = [dp(l, TOL[c]) for l in lines if length(l) >= MINLEN[c]]
        lines = [l for l in lines if len(l) >= 2]
        o.u8(c); o.u32(len(lines))
        for l in lines:
            o.pts(l)
        stats[c] = (len(lines), sum(len(l) for l in lines))
    # section 2: freeway shields
    o.u16(len(shield_pts))
    for x, z, ref in shield_pts:
        o.b += struct.pack('<hh', q(x), q(z)); r = ref.encode(); o.u8(len(r)); o.b += r
    # section 3: polygons (water, parks, golf) and water lines (rivers, canals)
    polys = {0: [], 1: [], 2: []}; wlines = {0: [], 1: []}
    for kind, layer in ((0, 'water'), (1, 'green')):
        for el in fetch(layer, refetch)['elements']:
            t = el.get('tags', {})
            if el['type'] == 'way' and 'waterway' in t:
                pts = geom(el)
                if len(pts) >= 2 and clip_ok(pts):
                    wlines[0 if t['waterway'] == 'river' else 1].append(pts)
                continue
            rings = [geom(el)] if el['type'] == 'way' else \
                    [[world(g['lat'], g['lon']) for g in m.get('geometry', [])] for m in el.get('members', []) if m.get('role') == 'outer']
            k = 0 if kind == 0 else (2 if t.get('leisure') == 'golf_course' else 1)
            for r in rings:
                if len(r) >= 4 and clip_ok(r):
                    xs = [p[0] for p in r]; zs = [p[1] for p in r]
                    if (max(xs) - min(xs)) * (max(zs) - min(zs)) < 60 * 60:
                        continue   # drop pools and pocket parks
                    # Phoenix keeps its historical (two point) rings so phx.bin stays byte identical
                    polys[k].append(dp(r, 6) if REGION == 'phx' else dp_ring(r, 6))
    o.u8(len(polys))
    for k in sorted(polys):
        o.u8(k); o.u32(len(polys[k]))
        for r in polys[k]:
            o.pts(r)
    o.u8(len(wlines))
    for k in sorted(wlines):
        lines = [dp(l, 8) for l in merge_lines(wlines[k])]
        o.u8(k); o.u32(len(lines))
        for l in lines:
            o.pts(l)
    # section 4: airport taxiways (lines) and aprons (polygons)
    taxi, apron = airports(refetch)
    taxi = [dp(l, 3) for l in merge_lines(taxi)]
    o.u32(len(taxi))
    for l in taxi:
        o.pts(l)
    o.u32(len(apron))
    for r in apron:
        o.pts(dp(r, 3) if REGION == 'phx' else dp_ring(r, 3))
    print('taxiways', len(taxi), 'aprons', len(apron))
    # section 5: urban density grid, zlib deflated
    W, H, g = urban_grid(cls)
    gz = zlib.compress(g, 9)
    o.u16(W); o.u16(H); o.u16(GRID); o.b += struct.pack('<hh', q(X0), q(Z0)); o.u32(len(gz)); o.b += gz
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, 'wb').write(o.b)
    print('roads', {c: f'{n} lines / {p} pts' for c, (n, p) in stats.items()})
    print('shields', len(shield_pts), sorted(set(s[2] for s in shield_pts)))
    print('polys', {k: len(v) for k, v in polys.items()}, 'water lines', {k: len(v) for k, v in wlines.items()})
    print(f'wrote {OUT}: {len(o.b)/1024:.0f} KB, gzip {len(zlib.compress(bytes(o.b), 9))/1024:.0f} KB')

if __name__ == '__main__':
    main()
