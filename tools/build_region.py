# Build the preprocessed world data for one of the new regions.
#
#   .venv/bin/python tools/build_region.py --region rjtt|lfpg|sbrj|all [--refetch]
#
# Writes assets/world/<id>.json (airport layout, water, parks, main roads, bridges,
# places, peaks, landmarks, urban density and a terrain height grid with a water
# mask) and then assets/map/<id>.bin through tools/build_map_data.py.
#
# Build time only. The live game never calls Overpass, OurAirports or the terrain
# tile server: it loads the files this writes. Every download is cached under
# tools/.osm-cache/ (gitignored), so a rerun is offline; --refetch asks again.
#
# Sources:
#   runways   OurAirports runways.csv / airports.csv (public domain)
#   features  OpenStreetMap through Overpass (ODbL), POST data=..., mirrors in turn
#   terrain   Mapzen Terrarium tiles on AWS, z12, height = R*256 + G + B/256 - 32768 m
#
# World frame: metres, +X east, -Z north, origin at the ARP (tools/regions.py).
# Grids ("urban", "terrain") are row major, row 0 the northern edge; x0/z0 are the
# world position of the north west corner of cell 0, cell i spans x0+i*cell..+cell.
import base64, csv, hashlib, io, json, math, os, re, sys, time, urllib.request, zlib
from collections import deque

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import regions
import build_map_data as bmd

ROOT = bmd.ROOT
CACHE = bmd.CACHE
FT = 0.3048
CREDITS = ['Map data © OpenStreetMap contributors (ODbL)', 'Runways: OurAirports (public domain)',
           'Elevation: Mapzen Terrarium tiles (SRTM, NASA; Copernicus DEM)']

def r1(v):
    v = round(float(v), 1)
    return int(v) if v == int(v) else v

def pts1(pts):
    return [[r1(x), r1(z)] for x, z in pts]

def ptsi(pts):
    # the big world layers are simplified to 15 m, so whole metres lose nothing and keep
    # the file under its size budget
    return [[round(x), round(z)] for x, z in pts]

# size budgets (KB of JSON text) for the layers that grow with the city
BUDGET = {'water': 20, 'parks': 14, 'roads': 52}

def budget(items, kb):
    """items: (importance, value) pairs; the most important first until the budget is spent."""
    out, n = [], 0
    for _, v in sorted(items, key=lambda c: c[0], reverse=True):
        n += len(json.dumps(v, separators=(',', ':'))) + 1
        if n > kb * 1024:
            break
        out.append(v)
    return out

def download(url, path, refetch):
    if os.path.exists(path) and not refetch:
        return open(path, 'rb').read()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    for attempt in range(4):
        try:
            raw = urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': bmd.UA}), timeout=120).read()
            open(path, 'wb').write(raw)
            return raw
        except Exception as e:
            print(f'  {url}: {e}, retrying')
            time.sleep(5 * (attempt + 1))
    sys.exit('download failed: ' + url)

def query(body, label, refetch):
    """One Overpass query, cached by a hash of its text."""
    h = hashlib.sha1(body.encode()).hexdigest()[:12]
    return bmd.overpass(body, os.path.join(CACHE, f'q-{label}-{h}.json'), label, refetch)

# ---------- OurAirports ----------
def ourairports(name, refetch):
    raw = download(f'https://davidmegginson.github.io/ourairports-data/{name}.csv',
                   os.path.join(CACHE, 'ourairports', name + '.csv'), refetch)
    return list(csv.DictReader(io.StringIO(raw.decode('utf8'))))

def fnum(v, d=None):
    try:
        return float(v)
    except (TypeError, ValueError):
        return d

def runways(icao, field_elev, refetch):
    out = []
    for row in ourairports('runways', refetch):
        if row['airport_ident'] != icao or row['closed'] == '1':
            continue
        if row['le_ident'].endswith('H') or row['surface'].upper().startswith('GRASS') and fnum(row['length_ft'], 0) < 2000:
            continue   # helicopter strips (LFPG 08H/26H)
        L = fnum(row['length_ft'], 0) * FT
        ends = {}
        for e in ('le', 'he'):
            lat, lon = fnum(row[e + '_latitude_deg']), fnum(row[e + '_longitude_deg'])
            ends[e] = bmd.world(lat, lon) if lat is not None and lon is not None else None
        # a missing threshold: from the other end, the length and the published heading
        for e, o in (('le', 'he'), ('he', 'le')):
            if ends[e] is None and ends[o] is not None:
                hd = fnum(row[o + '_heading_degT'])
                if hd is None:
                    hd = (fnum(row[e + '_heading_degT'], 0)) + 180
                a = hd * math.pi / 180
                ends[e] = (ends[o][0] + math.sin(a) * L, ends[o][1] - math.cos(a) * L)
        if ends['le'] is None:
            print(f'  {icao} {row["le_ident"]}: no threshold positions, skipped')
            continue
        (lx, lz), (hx, hz) = ends['le'], ends['he']
        hle = math.degrees(math.atan2(hx - lx, -(hz - lz))) % 360
        rec = {'id': row['le_ident'] + '/' + row['he_ident'], 'len': r1(L), 'wid': r1(fnum(row['width_ft'], 0) * FT),
               'surf': row['surface'], 'lit': int(row['lighted'] or 0), 'closed': 0}
        for e, x, z, hd in (('le', lx, lz, hle), ('he', hx, hz, (hle + 180) % 360)):
            rec[e] = {'num': row[e + '_ident'], 'x': r1(x), 'z': r1(z), 'hdgT': r1(hd),
                      'disp': r1(fnum(row[e + '_displaced_threshold_ft'], 0) * FT),
                      'elev': r1(fnum(row[e + '_elevation_ft'], field_elev / FT) * FT)}
        out.append(rec)
    return out

# ---------- geometry ----------
def area(r):
    return abs(sum(r[i][0] * r[i - 1][1] - r[i - 1][0] * r[i][1] for i in range(len(r)))) / 2

def clip_rect(poly, h):
    """Sutherland-Hodgman against the square bbox +-h."""
    def clip(pts, inside, cut):
        out = []
        for i in range(len(pts)):
            a, b = pts[i - 1], pts[i]
            if inside(b):
                if not inside(a):
                    out.append(cut(a, b))
                out.append(b)
            elif inside(a):
                out.append(cut(a, b))
        return out
    def cx(v):
        return lambda a, b: (v, a[1] + (b[1] - a[1]) * (v - a[0]) / (b[0] - a[0]))
    def cz(v):
        return lambda a, b: (a[0] + (b[0] - a[0]) * (v - a[1]) / (b[1] - a[1]), v)
    for inside, cut in ((lambda p: p[0] >= -h, cx(-h)), (lambda p: p[0] <= h, cx(h)),
                        (lambda p: p[1] >= -h, cz(-h)), (lambda p: p[1] <= h, cz(h))):
        poly = clip(poly, inside, cut)
        if not poly:
            return []
    return poly

def el_pts(el):
    if el['type'] == 'node':
        return [bmd.world(el['lat'], el['lon'])]
    return bmd.geom(el)

def el_rings(el, role='outer'):
    """Closed rings of a way, or a multipolygon's outer (or inner) members joined end to end."""
    if el['type'] == 'way':
        g = bmd.geom(el)
        return [g] if len(g) >= 4 else []
    if el['type'] != 'relation':
        return []
    lines = [[bmd.world(g['lat'], g['lon']) for g in m.get('geometry', []) if g]
             for m in el.get('members', []) if m.get('type') == 'way' and m.get('role', 'outer') in ((role,) if role != 'outer' else ('outer', ''))]
    lines = [l for l in lines if len(l) >= 2]
    return [r for r in bmd.merge_lines(lines) if len(r) >= 4]

def centroid(pts):
    return sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)

def seg_dist(px, pz, ax, az, bx, bz):
    dx, dz = bx - ax, bz - az; L2 = dx * dx + dz * dz or 1e-9
    t = max(0, min(1, ((px - ax) * dx + (pz - az) * dz) / L2))
    return math.hypot(px - ax - t * dx, pz - az - t * dz)

def fill_rings(mask, rings, W, H, x0, z0, cell, val=1):
    """Even-odd scanline fill of cell centres inside the rings (outers plus holes)."""
    if not rings:
        return
    zs = [p[1] for r in rings for p in r]
    j0 = max(0, int((min(zs) - z0) / cell - 0.5)); j1 = min(H - 1, int((max(zs) - z0) / cell + 0.5))
    edges = []
    for r in rings:
        for i in range(len(r)):
            a, b = r[i - 1], r[i]
            if a[1] != b[1]:
                edges.append((a, b) if a[1] < b[1] else (b, a))
    for j in range(j0, j1 + 1):
        zc = z0 + (j + 0.5) * cell
        xs = sorted(a[0] + (b[0] - a[0]) * (zc - a[1]) / (b[1] - a[1]) for a, b in edges if a[1] <= zc < b[1])
        for k in range(0, len(xs) - 1, 2):
            i0 = max(0, math.ceil((xs[k] - x0) / cell - 0.5)); i1 = min(W - 1, math.floor((xs[k + 1] - x0) / cell - 0.5))
            for i in range(i0, i1 + 1):
                mask[j * W + i] = val

# ---------- terrain ----------
def tile_xy(lat, lon, z):
    n = 2 ** z
    x = (lon + 180) / 360 * n
    y = (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n
    return x, y

def terrain(R, refetch):
    from PIL import Image
    half, cell = R['half'], R['cell']
    W = H = int(2 * half / cell); x0 = z0 = -half
    lat0, lon0 = R['origin']
    lat_n, lat_s = lat0 + half / bmd.MPD_LAT, lat0 - half / bmd.MPD_LAT
    lon_w, lon_e = lon0 - half / bmd.MPD_LON, lon0 + half / bmd.MPD_LON
    Z = 12; n = 2 ** Z
    tx0, ty0 = tile_xy(lat_n, lon_w, Z); tx1, ty1 = tile_xy(lat_s, lon_e, Z)
    s = [0.0] * (W * H); c = [0] * (W * H)
    count = 0
    for ty in range(int(ty0), int(ty1) + 1):
        # each pixel row's latitude, then its cell row
        rows = []
        for py in range(256):
            yy = (ty + (py + 0.5) / 256) / n
            lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * yy))))
            zw = -(lat - lat0) * bmd.MPD_LAT
            rows.append(int((zw - z0) // cell))
        for tx in range(int(tx0), int(tx1) + 1):
            raw = download(f'https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{Z}/{tx}/{ty}.png',
                           os.path.join(CACHE, 'terrarium', str(Z), str(tx), f'{ty}.png'), refetch)
            count += 1
            px = Image.open(io.BytesIO(raw)).convert('RGB').tobytes()
            cols = []
            for qx in range(256):
                lon = (tx + (qx + 0.5) / 256) / n * 360 - 180
                cols.append(int(((lon - lon0) * bmd.MPD_LON - x0) // cell))
            for py in range(256):
                j = rows[py]
                if not 0 <= j < H:
                    continue
                base = py * 256 * 3; rowo = j * W
                for qx in range(256):
                    i = cols[qx]
                    if 0 <= i < W:
                        o = base + qx * 3
                        s[rowo + i] += px[o] * 256 + px[o + 1] + px[o + 2] / 256 - 32768
                        c[rowo + i] += 1
    raw = [s[k] / c[k] if c[k] else 0.0 for k in range(W * H)]
    print(f'  terrain: {count} z{Z} tiles, grid {W}x{H} at {cell} m')
    return W, H, x0, z0, raw

def water_mask(raw, W, H, polys):
    """Sea: low cells (<= 0.5 m) joined to a low edge cell. Plus OSM water polygons (rivers, lakes)."""
    sea = bytearray(W * H); low = [v <= 0.5 for v in raw]
    dq = deque()
    for k in [i for i in range(W)] + [(H - 1) * W + i for i in range(W)] + [j * W for j in range(H)] + [j * W + W - 1 for j in range(H)]:
        if low[k] and not sea[k]:
            sea[k] = 1; dq.append(k)
    while dq:
        k = dq.popleft(); j, i = divmod(k, W)
        for kk, ok in ((k - 1, i > 0), (k + 1, i < W - 1), (k - W, j > 0), (k + W, j < H - 1)):
            if ok and low[kk] and not sea[kk]:
                sea[kk] = 1; dq.append(kk)
    river = bytearray(W * H)
    return sea, river

# ---------- one region ----------
def build(rid, refetch):
    R = regions.get(rid)
    bmd.setup(rid)
    lat0, lon0 = R['origin']; half = R['half']; icao = R['icao']
    print(f'== {rid} {R["name"]}: origin {lat0}, {lon0}, half {half} m, bbox {bmd.bbox()}')
    ap = next(a for a in ourairports('airports', refetch) if a['ident'] == icao)
    if abs(float(ap['latitude_deg']) - lat0) > 1e-5 or abs(float(ap['longitude_deg']) - lon0) > 1e-5:
        print(f'  note: regions.py origin differs from OurAirports ARP {ap["latitude_deg"]}, {ap["longitude_deg"]}')
    elev = fnum(ap['elevation_ft'], 0) * FT
    rws = runways(icao, elev, refetch)
    main = R['main']
    if rid == 'sbrj':
        longest = max(rws, key=lambda r: r['len'])
        south = [e for e in (longest['le'], longest['he']) if 90 < e['hdgT'] < 270][0]
        main = south['num']
    js = {'id': rid, 'icao': icao, 'name': R['name'], 'city': R['city'], 'country': R['country'],
          'origin': {'lat': lat0, 'lon': lon0}, 'elev': r1(elev), 'half': half, 'main': main, 'runways': rws}

    # ----- airport features within 4 km of the ARP -----
    a = f'(around:4000,{lat0},{lon0})'
    body = (f'[out:json][timeout:180];(nwr{a}["aeroway"];nwr{a}["building"="hangar"];'
            f'nwr{a}["man_made"="tower"];);out body geom qt;')
    els = query(body, rid + '-airport', refetch)['elements']
    osm_rwy = [bmd.geom(e) for e in els if e['type'] == 'way' and e['tags'].get('aeroway') == 'runway' and len(e.get('geometry', [])) >= 2]
    fit = bmd.osm_fit(osm_rwy, [[r['le']['x'], r['le']['z'], r['he']['x'], r['he']['z']] for r in rws]) if osm_rwy else None
    ox, oz = fit or (0.0, 0.0)
    print(f'  OSM runways {len(osm_rwy)}, offset to OurAirports {math.hypot(ox, oz):.0f} m, applied to airport features')
    mv = lambda pts: [(x + ox, z + oz) for x, z in pts]
    taxi, aprons, terms, hangars, gates, towers, aero = [], [], [], [], [], [], []
    for e in els:
        t = e.get('tags', {}); aw = t.get('aeroway')
        if aw == 'taxiway' and e['type'] == 'way':
            g = bmd.geom(e)
            if len(g) >= 2:
                taxi.append(mv(g))
        elif aw in ('apron', 'terminal', 'hangar') or t.get('building') == 'hangar':
            dst = {'apron': aprons, 'terminal': terms}.get(aw, hangars)
            dst += [bmd.dp_ring(mv(r), 2 if dst is not aprons else 3) for r in el_rings(e)]
        elif aw == 'gate' and e['type'] == 'node':
            gates.append(mv(el_pts(e))[0])
        elif aw == 'aerodrome':
            for r in el_rings(e):
                aero.append((t.get('icao') == icao, area(r), r))
        if aw == 'control_tower' or (t.get('man_made') == 'tower' and (
                t.get('tower:type') == 'airport_control' or t.get('service') == 'aircraft_control'
                or re.search(r'管制塔|control tower|tour de contr[oô]le|torre de controle', t.get('name', ''), re.I))):
            p = el_pts(e) if e['type'] == 'node' else bmd.geom(e) or [g for r in el_rings(e) for g in r]
            if p:
                towers.append(mv([centroid(p)])[0])
    taxi = [bmd.dp(l, 3) for l in bmd.merge_lines(taxi)]
    js['taxiways'] = [ptsi(l) for l in taxi]
    js['aprons'] = [ptsi(r) for r in aprons if len(r) >= 3]
    js['terminals'] = [ptsi(r) for r in terms if len(r) >= 3]
    js['hangars'] = [ptsi(r) for r in hangars if len(r) >= 3]
    js['gates'] = ptsi(gates)
    tw = min(towers, key=lambda p: math.hypot(*p)) if towers else None
    js['tower'] = {'x': r1(tw[0]), 'z': r1(tw[1])} if tw else None
    aero.sort(key=lambda a: (a[0], a[1]), reverse=True)
    aerodrome = bmd.dp_ring(mv(aero[0][2]), 5) if aero else None
    js['aerodrome'] = pts1(aerodrome) if aerodrome else None

    # ----- bbox layers -----
    W, H, x0, z0, raw = terrain(R, refetch)
    cell = R['cell']
    # water polygons: ways, and multipolygons with their holes (islands) for the mask
    groups = []
    for e in bmd.fetch('water', refetch)['elements']:
        t = e.get('tags', {})
        if e['type'] == 'way' and t.get('waterway') in ('river', 'canal'):
            continue   # centre lines, not areas
        outs = el_rings(e)
        if outs:
            groups.append((outs, el_rings(e, 'inner') if e['type'] == 'relation' else []))
    sea, river = water_mask(raw, W, H, groups)
    for outs, ins in groups:
        cl = [clip_rect(r, half) for r in outs]
        fill_rings(river, [r for r in cl if len(r) >= 3] + [clip_rect(r, half) for r in ins], W, H, x0, z0, cell)
    water_polys = []
    for outs, _ in groups:
        for r in outs:
            r = clip_rect(r, half)
            if len(r) >= 3 and area(r) >= 20000:   # drop ponds under 2 ha
                r = bmd.dp_ring(r, 15)
                if len(r) >= 3:
                    water_polys.append(r)
    js['water'] = budget([(area(r), ptsi(r)) for r in water_polys], BUDGET['water'])
    # the airfield is land at field elevation (Haneda sits on reclaimed land and piers)
    field = bytearray(W * H)
    if aerodrome:
        fill_rings(field, [aerodrome], W, H, x0, z0, cell)
    else:
        for j in range(H):
            for i in range(W):
                xc, zc = x0 + (i + 0.5) * cell, z0 + (j + 0.5) * cell
                if any(seg_dist(xc, zc, r['le']['x'], r['le']['z'], r['he']['x'], r['he']['z']) < 1200 for r in rws):
                    field[j * W + i] = 1
    hts = []; mask = bytearray(W * H)
    for k in range(W * H):
        if field[k]:
            hts.append(round(elev))
        elif sea[k]:
            hts.append(0); mask[k] = 1
        elif river[k]:
            hts.append(max(0, round(raw[k]))); mask[k] = 1
        else:
            hts.append(max(0, round(raw[k])))
    wfrac = sum(mask) / (W * H)

    # parks over 4 ha
    parks = []
    for e in bmd.fetch('green', refetch)['elements']:
        if e.get('tags', {}).get('leisure') != 'park':
            continue
        for r in el_rings(e):
            r = clip_rect(r, half)
            if len(r) >= 3 and area(r) > 40000:
                r = bmd.dp_ring(r, 15)
                if len(r) >= 3:
                    parks.append(r)
    js['parks'] = budget([(area(r), ptsi(r)) for r in parks], BUDGET['parks'])

    # main roads for the 3D world
    rd = {'motorway': [], 'trunk': [], 'primary': []}
    for layer in ('fwy', 'major'):
        for e in bmd.fetch(layer, refetch)['elements']:
            hw = e.get('tags', {}).get('highway')
            if e['type'] == 'way' and hw in rd:
                g = bmd.geom(e)
                if len(g) >= 2 and bmd.clip_ok(g):
                    rd[hw].append(g)
    # every motorway first, then trunk and primary roads longest first, up to the budget
    items = [((2 - ki) * 1e9 + bmd.length(l), (k, ptsi(bmd.dp(l, 15))))
             for ki, (k, v) in enumerate(rd.items()) for l in bmd.merge_lines(v) if bmd.length(l) >= 60]
    js['roads'] = {k: [] for k in rd}
    for k, l in budget(items, BUDGET['roads']):
        js['roads'][k].append(l)

    # bridges: long road and rail bridges, the ones over water first
    body = (f'[out:json][timeout:180][bbox:{bmd.bbox()}];(way["bridge"]["bridge"!="no"]["highway"~"^(motorway|trunk|primary)$"];'
            f'way["bridge"]["bridge"!="no"]["railway"="rail"];);out tags geom qt;')
    bys = {}; named = set()
    for e in query(body, rid + '-bridges', refetch)['elements']:
        t = e.get('tags', {}); nm = t.get('bridge:name:en') or t.get('bridge:name') or t.get('name:en') or t.get('name') or ''
        g = bmd.geom(e)
        if len(g) >= 2:
            bys.setdefault(nm or f'#{e["id"]}', []).append(g)
            # a real named bridge (not a long viaduct): ranked ahead of viaducts
            if t.get('bridge:name') or t.get('bridge:structure') or re.search(
                    r'bridge|橋|ponte|pont ', (t.get('name', '') + ' ' + t.get('name:en', '')), re.I):
                named.add(nm or f'#{e["id"]}')
    def wet(l):
        n = 0
        for x, z in l[::max(1, len(l) // 20)] + [l[-1]]:
            i, j = int((x - x0) // cell), int((z - z0) // cell)
            n += 0 <= i < W and 0 <= j < H and mask[j * W + i]
        return n
    cands = []
    for nm, ls in bys.items():
        kept = []
        # two carriageways or decks of one bridge: keep the longest, drop parallels near it
        for L, l in sorted(((bmd.length(l), l) for l in bmd.merge_lines(ls)), key=lambda c: c[0], reverse=True):
            if L <= 300 or not bmd.clip_ok(l):
                continue
            m = l[len(l) // 2]
            if all(min(math.hypot(m[0] - p[0], m[1] - p[1]) for p in k[1]) > 150 for k in kept):
                kept.append((L, l))
        for L, l in kept:
            cands.append((wet(l) > 0, nm in named, L, '' if nm.startswith('#') else nm, l))
    cands.sort(key=lambda c: (c[0], c[1], c[2]), reverse=True)
    js['bridges'] = [{'name': nm, 'pts': ptsi(bmd.dp(l, 15))} for w, b, L, nm, l in cands[:40] if w or L > 1000]

    # places and peaks
    body = f'[out:json][timeout:180][bbox:{bmd.bbox()}];node["place"~"^(city|town|suburb|quarter)$"];out body qt;'
    rank = {'city': 0, 'town': 1, 'suburb': 2, 'quarter': 3}
    pl = []
    for e in query(body, rid + '-places', refetch)['elements']:
        t = e.get('tags', {}); nm = t.get('name:en') or t.get('name')
        if not nm:
            continue
        m = re.match(r'\d+', (t.get('population') or '').replace(',', '').replace(' ', '').replace('.', ''))
        x, z = bmd.world(e['lat'], e['lon'])
        if abs(x) <= half and abs(z) <= half:
            pl.append((int(m.group()) if m else 0, -rank[t['place']], nm, x, z, t['place']))
    pl.sort(key=lambda p: (p[1], p[0]), reverse=True)    # cities first, then by population
    pl = sorted(pl[:60], key=lambda p: (p[0], p[1]), reverse=True)
    js['places'] = [{'name': nm, 'x': r1(x), 'z': r1(z), 'kind': k, 'pop': pop} for pop, _, nm, x, z, k in pl]
    body = f'[out:json][timeout:180][bbox:{bmd.bbox()}];node["natural"="peak"]["name"]["ele"];out body qt;'
    pk = []
    for e in query(body, rid + '-peaks', refetch)['elements']:
        t = e['tags']; m = re.match(r'-?\d+(\.\d+)?', t['ele'].strip())
        if m:
            x, z = bmd.world(e['lat'], e['lon'])
            pk.append((float(m.group()), t.get('name:en') or t['name'], x, z))
    pk.sort(reverse=True)
    js['peaks'] = [{'name': nm, 'x': r1(x), 'z': r1(z), 'ele': r1(ele)} for ele, nm, x, z in pk[:30]]

    js['landmarks'] = []
    for l in R['landmarks']:
        x, z = bmd.world(l['lat'], l['lon'])
        js['landmarks'].append({'id': l['id'], 'name': l['name'], 'x': r1(x), 'z': r1(z), 'kind': l['kind'],
                                'h': l.get('h'), 'src': l['src']})

    # urban density: the map builder's grid (residential streets counted tile by tile)
    cls = bmd.roads(refetch)
    uw, uh, ug = bmd.urban_grid(cls)
    js['urban'] = {'w': uw, 'h': uh, 'cell': bmd.GRID, 'x0': bmd.X0, 'z0': bmd.Z0,
                   'b64': base64.b64encode(zlib.compress(ug, 9)).decode()}
    import struct
    js['terrain'] = {'w': W, 'h': H, 'cell': cell, 'x0': x0, 'z0': z0,
                     'b64': base64.b64encode(zlib.compress(struct.pack(f'<{W*H}h', *hts), 9)).decode(),
                     'sea': 0, 'waterB64': base64.b64encode(zlib.compress(bytes(mask), 9)).decode()}
    js['credits'] = CREDITS
    out = os.path.join(ROOT, 'assets', 'world', rid + '.json')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    txt = json.dumps(js, ensure_ascii=False, separators=(',', ':'))
    open(out, 'w', encoding='utf8').write(txt)
    sizes = {k: len(json.dumps(v, ensure_ascii=False, separators=(',', ':'))) // 1024 for k, v in js.items() if isinstance(v, (list, dict))}
    print(f'  runways: ' + ', '.join(f"{r['id']} {r['len']:.0f} m ({r['le']['hdgT']:.1f}/{r['he']['hdgT']:.1f} T)" for r in rws))
    print(f'  main {main}; tower {"found" if tw else "MISSING"}; aerodrome {"found" if aerodrome else "MISSING"}; '
          f'taxiways {len(taxi)}, aprons {len(aprons)}, terminals {len(terms)}, hangars {len(hangars)}, gates {len(gates)}')
    print(f'  water fraction {wfrac:.3f} (sea {sum(sea)/(W*H):.3f}); water polys {len(water_polys)}, parks {len(parks)}, '
          f'bridges {[b["name"] for b in js["bridges"][:8]]}, places {len(pl)}, peaks {len(pk)}')
    print(f'  wrote {out}: {len(txt.encode())/1024:.0f} KB  sections KB {sizes}')
    # the 2D map file, same KGM2 format as Phoenix, runways from the JSON just written
    bmd.main(['--region', rid], cls=cls)
    return wfrac

def main():
    a = sys.argv[1:]
    rid = a[a.index('--region') + 1] if '--region' in a else 'all'
    ids = list(regions.REGIONS) if rid == 'all' else [rid]
    for r in ids:
        build(r, '--refetch' in a)
    if bmd.LAST_MIRROR:
        print('Overpass mirror used last:', bmd.LAST_MIRROR)

if __name__ == '__main__':
    main()
