# Runways item 2: every runway in the game against the published data. For every region (az, rjtt, lfpg, sbrj) the
# page is loaded and window.__kgeu.RWY_ENDS read (the game's own RUNWAYS table, after every projection the game does);
# each runway is matched by airport and end to tools/.osm-cache/ourairports-runways.csv (OurAirports runways.csv,
# public domain; its lengths, widths and displaced thresholds are the FAA 5010 / AIP numbers) and must agree:
#   length within 1.5 percent, width within 2 m, each end's displaced threshold within 10 m, each end's landing heading
#   within 1.5 degrees of heading_degT. Where OurAirports' two headings of a runway are not reciprocal (RJTT 05/23 says
#   57 and 223) the bearing between its le and he coordinates is used instead, marked * in the table.
#   In Arizona (geoW is known: index.html) each end's pavement end must also sit within 100 m of OurAirports' le/he point.
# The assault strip (LZ) is the game's own and is skipped.
# Usage: .venv/bin/python tests/runway_data_check.py [az rjtt lfpg sbrj]
import asyncio, csv, math, os, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, IPHONE_15, Checks

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
CSV = os.path.join(ROOT, 'tools', '.osm-cache', 'ourairports-runways.csv')
FT = 0.3048
REGIONS = ['az', 'rjtt', 'lfpg', 'sbrj']
STORAGE = {'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'}
ok = Checks()

# geoW (index.html): GEO0 is the KGEU runway midpoint
GEO0 = (477.60536442669985, -979.2361134429425)
def geo(lat, lon):
    return (GEO0[0] + (lon + 112.29517) * 111320 * math.cos(math.radians(33.52683)), GEO0[1] - (lat - 33.52683) * 110950)

def norm(n):
    d = ''.join(c for c in n if c.isdigit())
    return d.zfill(2) + n[len(d):] if d else n

def fnum(v):
    try: return float(v)
    except (TypeError, ValueError): return None

def published():
    out = {}
    for r in csv.DictReader(open(CSV)):
        if r['closed'] == '1': continue
        out.setdefault(r['airport_ident'], []).append(r)
    return out

def bearing(lat0, lon0, lat1, lon1):
    dx = (lon1 - lon0) * 111320 * math.cos(math.radians((lat0 + lat1) / 2)); dn = (lat1 - lat0) * 110950
    return math.degrees(math.atan2(dx, dn)) % 360

def adiff(a, b):
    return abs((a - b + 180) % 360 - 180)

ENDS_JS = """()=>{const K=window.__kgeu,seen=new Map();
  for(const e of K.RWY_ENDS){const r=e.rwy;if(!seen.has(r))seen.set(r,{code:r.code,apt:r.apt,num:r.num,len:r.len,wid:r.wid,ends:[]});
    const px=e.x-e.dx*e.thr,pz=e.z-e.dz*e.thr;
    seen.get(r).ends.push({num:e.num,thr:e.thr,h:((e.h*180/Math.PI)%360+360)%360,x:e.x,z:e.z,px:px,pz:pz});}
  return [...seen.values()];}"""

ROWS = []
# where OurAirports is behind the FAA 5010 (airnav.com): KGEU 19 has a 1,001 ft displaced threshold, OurAirports none
OVERRIDE = {('KGEU', '19'): {'disp_ft': 1001}}

async def check_region(b, url, region, pub):
    storage = dict(STORAGE)
    if region != 'az': storage['kgeuRegion'] = region
    pg = await page(b, url, vp=IPHONE_15, storage=storage)
    if region != 'az':
        await pg.wait_for_function("()=>window.__kgeu.WORLD.ready||window.__kgeu.WORLD.err", timeout=60000)
    rws = await pg.evaluate(ENDS_JS)
    await pg.context.close()
    n = 0
    for r in rws:
        if r['code'] == 'LZ': continue
        P = pub.get(r['code'], [])
        ids = {norm(e['num']) for e in r['ends']}
        row = next((p for p in P if {norm(p['le_ident']), norm(p['he_ident'])} == ids), None)
        if not ok(f"{region} {r['code']} {r['num']}: in OurAirports", row is not None, sorted(ids)):
            continue
        n += 1
        L = float(row['length_ft']) * FT; W = float(row['width_ft']) * FT
        lerr = abs(r['len'] - L) / L * 100
        ok(f"{region} {r['code']} {r['num']}: length {r['len']:.0f} m vs {L:.0f} m", lerr <= 1.5, f"{lerr:.2f} %")
        ok(f"{region} {r['code']} {r['num']}: width {r['wid']:.1f} m vs {W:.1f} m", abs(r['wid'] - W) <= 2)
        le = (fnum(row['le_latitude_deg']), fnum(row['le_longitude_deg'])); he = (fnum(row['he_latitude_deg']), fnum(row['he_longitude_deg']))
        hl, hh = fnum(row['le_heading_degT']), fnum(row['he_heading_degT'])
        star = hl is None or hh is None or adiff(hl + 180, hh) > 2
        if star and None not in le + he:
            hl = bearing(le[0], le[1], he[0], he[1]); hh = (hl + 180) % 360
        cells = []
        for e in r['ends']:
            isle = norm(e['num']) == norm(row['le_ident'])
            p = 'le' if isle else 'he'
            disp = (OVERRIDE.get((r['code'], norm(e['num'])), {}).get('disp_ft') or fnum(row[p + '_displaced_threshold_ft']) or 0) * FT
            hp = hl if isle else hh
            ok(f"{region} {r['code']} {e['num']}: displaced threshold {e['thr']:.0f} m vs {disp:.0f} m", abs(e['thr'] - disp) <= 10)
            ok(f"{region} {r['code']} {e['num']}: heading {e['h']:.1f} vs {hp:.1f}{'*' if star else ''} true", adiff(e['h'], hp) <= 1.5)
            pos = ''
            if region == 'az' and None not in (le if isle else he):
                gx, gz = geo(*(le if isle else he)); d = math.hypot(e['px'] - gx, e['pz'] - gz)
                ok(f"{region} {r['code']} {e['num']}: pavement end within 100 m of OurAirports' point", d <= 100, f"{d:.0f} m")
                pos = f"{d:.0f}"
            cells.append((e['num'], e['thr'], disp, e['h'], hp, star, pos))
        ROWS.append((region, r['code'], r['num'], r['len'], L, r['wid'], W, cells))
    ok(f"{region}: runways checked", n > 0, n)

async def main():
    regions = [a for a in sys.argv[1:] if not a.startswith('-')] or REGIONS
    pub = published()
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        for region in regions:
            print(f"\n== {region} ==")
            await check_region(b, url, region, pub)
        await b.close()
    print("\n%-5s %-5s %-8s %13s %11s | %-4s %-15s %-17s %s" % ('reg', 'apt', 'runway', 'len game/pub', 'wid g/p', 'end', 'disp game/pub', 'hdg game/pub', 'pos err m'))
    for reg, code, num, lg, lp, wg, wp, cells in ROWS:
        for i, (en, tg, tp, hg, hp, star, pos) in enumerate(cells):
            head = "%-5s %-5s %-8s %6.0f/%-6.0f %5.1f/%-5.1f" % (reg, code, num, lg, lp, wg, wp) if i == 0 else ' ' * 39
            print("%s | %-4s %6.0f/%-8.0f %7.1f/%-6.1f%s %s" % (head, en, tg, tp, hg, hp, '*' if star else ' ', pos))
    sys.exit(ok.done('runway_data_check'))

asyncio.run(main())
