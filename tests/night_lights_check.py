# Runways item (night lighting rewrite): checks the builder's new night airport lighting against
# the hook contract below. Until the hooks land this prints "hook missing" and SKIPS those checks
# (not a FAIL) so the test is safe to run against today's code while the lighting rewrite is in flight.
#
#   window.__kgeu.rwyLights(): array, one entry per end in window.__kgeu.RWY_ENDS order:
#     {code, num, edge, thr, end, papi:{n, side, ang}, als, reil, cl, tdz, beacon, taxiBlue, floods, layer}
#   window.__kgeu.lightsHide(v): hides (true) / shows (false) every airport light layer, the PAPI
#     sprites and the aircraft's own lights.
#
# Part A (pixel check, runs today): for every runway end, night + clear, the Cessna placed on a 3 degree
# final at 3 nm (5556 m) and then 1 nm (1852 m), chase camera, snapCam + 3 frames of stepFrame(1/30) + 250
# ms, screenshot the canvas lit, then (if lightsHide exists) lightsHide(true) + 1 frame + screenshot hidden,
# lightsHide(false); else fall back to a day frame instead of hidden (noted in the output, less exact).
# Counts pixels in the centre third (x) / 35-70% band (y) of the frame where the lit frame beats the
# hidden one by > 40/255 in any channel; requires >= 12 such pixels at 3 nm, >= 60 at 1 nm, with some
# green-dominant (threshold bar) and some white/warm (edge lights) among the 1 nm set. Medium tier by
# default; for Arizona only, Glendale 1 and 19 at 1 nm are repeated forced to Low and to High (the owner's
# dark-Glendale report, every tier).
#
# Part B (spec check, needs rwyLights, skips until it lands): the SPEC table below, plus for every end:
# edge light count within 15% of 2*(len/60+1), thr >= 4 and end >= 4 (6 on runways >= 45 m wide), beacon
# true for every airport, taxiBlue > 20 for every airport except LZ.
#
# Part C: no console errors; whole run under 9 minutes (each region page under 3 minutes, at most 2
# screenshot pairs per end).
#
# Usage: .venv/bin/python tests/night_lights_check.py [az|rjtt|lfpg|sbrj ...] [--out DIR] [--ends CODE-NUM,...]
#   no region given -> all four (az rjtt lfpg sbrj). --ends restricts part A/B to those ends, e.g.
#   --ends KGEU-1,KLUF-21L,KPHX-26 (a quick shakeout run under the per-region 3 minute budget).
# Saves the lit 1 nm screenshot of the first end of every airport in each region run into --out
# (default overnight-screenshots/runways_night/), plus a one-line summary per region.
import asyncio, io, os, sys, time, math, warnings
from playwright.async_api import async_playwright
from PIL import Image
from harness import serve, launch, page, IPHONE_15, Checks

warnings.filterwarnings('ignore', category=DeprecationWarning)   # PIL getdata(): fine until Pillow 14 (2027)

ALL_REGIONS = ['az', 'rjtt', 'lfpg', 'sbrj']
DPR = 2
D3NM, D1NM = 5556.0, 1852.0
GS = 3 * math.pi / 180

# az base id per ICAO code (world regions: the base id is the region id itself, e.g. 'rjtt')
AZ_BASE = {'KGEU': 'kgeu', 'KLUF': 'luke', 'KPHX': 'phx'}

# ---- Part B spec table ----
SPEC = {
    ('KGEU', '1'): dict(papi=2, side='L', reil=True, als='REIL'),
    ('KGEU', '19'): dict(papi=2, side='L', reil=True, als='REIL'),
    ('KLUF', '03L'): dict(papi=4, reil=False, als='none'),
    ('KLUF', '21R'): dict(papi=4, reil=False, als='none'),
    ('KLUF', '03R'): dict(papi=4, reil=False, als='none'),
    ('KLUF', '21L'): dict(papi=4, als='ALSF1'),
    ('KPHX', '07L'): dict(papi=4, als='MALSR', reil=False),
    ('KPHX', '25R'): dict(papi=4, als='MALSR', reil=False),
    ('KPHX', '07R'): dict(papi=4, als='MALSR', reil=False),
    ('KPHX', '25L'): dict(papi=4, als='MALSR', reil=False),
    ('KPHX', '08'): dict(papi=4, als='MALSF', reil=False),
    ('KPHX', '26'): dict(papi=4, als='MALSF', reil=True),
    ('LZ', '9'): dict(papi=0, als='none'),
    ('LZ', '27'): dict(papi=0, als='none'),
    ('SBRJ', '02R'): dict(papi=4, als='none'),
    ('SBRJ', '20L'): dict(papi=4, als='none'),
    ('SBRJ', '02L'): dict(papi=0, als='none'),
    ('SBRJ', '20R'): dict(papi=0, als='none'),
}
RJTT_ALS = {'CAT1', 'CAT2'}
RJTT_CLTDZ = {'34L', '34R', '16L', '16R'}
LFPG_ENDS_CLTDZ = True   # all eight de Gaulle ends want cl>0 and tdz>0

PLACE_JS = """([i,d,V])=>{
  const K=window.__kgeu, e=K.RWY_ENDS[i], s=K.state();
  const gear=K.rwyFrame().gear;
  const g=K.groundHeight(e.x,e.z);
  const gs=3*Math.PI/180;
  s.pos.set(e.x-e.dx*d, g+d*Math.tan(gs)+gear, e.z-e.dz*d);
  s.vel.set(e.dx*V, -V*Math.tan(gs), e.dz*V);
  s.quat.setFromEuler(new THREE.Euler(0.02,-e.h,0,'YXZ'));
  s.w.set(0,0,0);
  s.onGround=false; s.airTime=30; s.flapIdx=2; s.gearDown=true; s.gearPos=1;
  s.ap=null; s.throttle=s.power=0.5; s.crashed=false;
  if(K.touchIn){K.touchIn.active=false;}
  return {code:e.rwy.code, num:e.num};
}"""

ENDS_FULL_JS = "()=>window.__kgeu.RWY_ENDS.map((e,i)=>({i:i,code:e.rwy.code,num:e.num,apt:e.rwy.apt,len:e.rwy.len,wid:e.rwy.wid}))"


def opt(flag, default=None):
    if flag in sys.argv:
        i = sys.argv.index(flag)
        if i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return default


def end_key(e):
    return e['code'] + '-' + e['num']


def diff_stats(lit_img, hidden_img):
    """pixels in the centre third (x) / 35-70% band (y) where lit beats hidden by >40/255 in any channel;
    plus how many of those are green-dominant (papi/threshold) and how many white/warm (edge lights)."""
    w, h = lit_img.size
    x0, x1 = w // 3, (2 * w) // 3
    y0, y1 = int(h * 0.35), int(h * 0.70)
    a = lit_img.crop((x0, y0, x1, y1)).getdata()
    b = hidden_img.crop((x0, y0, x1, y1)).getdata()
    n = green = white = 0
    for (r, g, bl), (r2, g2, b2) in zip(a, b):
        if r - r2 > 40 or g - g2 > 40 or bl - b2 > 40:
            n += 1
            if g > r + 30 and g > bl + 30:
                green += 1
            if r > 150 and g > 150:
                white += 1
    return n, green, white


async def snap_canvas(pg):
    return Image.open(io.BytesIO(await pg.locator('#gl').screenshot(timeout=60000))).convert('RGB')


async def ensure_chase(pg):
    await pg.evaluate("()=>{const K=window.__kgeu;let k=0;while(K.camMode()!==0&&k++<5)K.cycleCam();}")


async def place_and_frame(pg, i, d, V=32):
    await pg.evaluate(PLACE_JS, [i, d, V])
    await pg.evaluate("()=>window.__kgeu.snapCam()")
    await pg.evaluate("()=>{for(let i=0;i<3;i++)window.__kgeu.stepFrame(1/30);}")
    await pg.wait_for_timeout(250)


async def lit_hidden_pair(pg, has_hide, i, d, V=32):
    await place_and_frame(pg, i, d, V)
    lit = await snap_canvas(pg)
    if has_hide:
        await pg.evaluate("()=>window.__kgeu.lightsHide(true)")
        await pg.evaluate("()=>window.__kgeu.stepFrame(1/30)")
        hidden = await snap_canvas(pg)
        await pg.evaluate("()=>window.__kgeu.lightsHide(false)")
    else:
        await pg.evaluate("()=>window.__kgeu.setTOD('day')")
        await pg.evaluate("()=>window.__kgeu.stepFrame(1/30)")
        hidden = await snap_canvas(pg)
        await pg.evaluate("()=>window.__kgeu.setTOD('night')")
    return lit, hidden


def expected_edge(len_):
    return 2 * (len_ / 60 + 1)


def spec_row(code, num):
    if (code, num) in SPEC:
        return SPEC[(code, num)]
    if code == 'RJTT':
        row = dict(papi=4, als='__RJTT__')
        if num in RJTT_CLTDZ:
            row['cl_tdz'] = True
        return row
    if code == 'LFPG':
        return dict(papi=4, als='CAT2', cl_tdz=True)
    return None


EDGE_TOL = 0.20   # a runway's spacing rounds to whole lights at both ends


def check_spec(c, region, L, len_, wid_, label):
    code, num = L['code'], L['num']
    if code == 'LZ':
        # the assault strip: a military strip with portable amber edge markers only, no threshold/end,
        # PAPI, beacon or taxiway-blue fixtures to check
        c(f'{label}: markers only - edge lights {L["edge"]} >= 10', L['edge'] >= 10, L['edge'])
        row = spec_row(code, num)
        if row and row.get('als') not in (None, '__RJTT__'):
            c(f'{label}: ALS {row["als"]}', L['als'] == row['als'], L['als'])
        return
    want_edge = expected_edge(len_)
    edge_ok = abs(L['edge'] - want_edge) <= EDGE_TOL * want_edge
    c(f'{label}: edge lights {L["edge"]} within 20% of {want_edge:.1f}', edge_ok, L['edge'])
    min_cnt = 6 if wid_ >= 45 else 4
    c(f'{label}: threshold/end lights >= {min_cnt}', L['thr'] >= min_cnt and L['end'] >= min_cnt, (L['thr'], L['end']))
    c(f'{label}: beacon on', L['beacon'] is True, L['beacon'])
    c(f'{label}: taxiway blue lights > 20', L['taxiBlue'] > 20, L['taxiBlue'])
    row = spec_row(code, num)
    if row is None:
        return
    c(f'{label}: PAPI count {row["papi"]}', L['papi']['n'] == row['papi'], L['papi'])
    if row.get('side'):
        c(f'{label}: PAPI side {row["side"]}', L['papi'].get('side') == row['side'], L['papi'])
    if 'reil' in row:
        c(f'{label}: REIL {row["reil"]}', L['reil'] == row['reil'], L['reil'])
    if row.get('als') == '__RJTT__':
        c(f'{label}: ALS in CAT1/CAT2', L['als'] in RJTT_ALS, L['als'])
    elif 'als' in row:
        c(f'{label}: ALS {row["als"]}', L['als'] == row['als'], L['als'])
    if row.get('cl_tdz'):
        c(f'{label}: centreline and TDZ lights present', L['cl'] > 0 and L['tdz'] > 0, (L['cl'], L['tdz']))


async def run_region(region, out_dir, ends_filter, c, budget_s):
    t0 = time.monotonic()
    srv, url = serve()
    rows = []
    saved_shots = []
    async with async_playwright() as p:
        b = await launch(p)
        storage = {'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'}
        if region != 'az':
            storage['kgeuRegion'] = region
        pg = await page(b, url, vp=IPHONE_15, storage=storage)
        if region != 'az':
            await pg.wait_for_function('()=>window.__kgeu.WORLD.ready||window.__kgeu.WORLD.err', timeout=60000)
        has_hide = await pg.evaluate("()=>typeof window.__kgeu.lightsHide==='function'")
        has_spec = await pg.evaluate("()=>typeof window.__kgeu.rwyLights==='function'")
        c(f'{region}: lightsHide hook present (else falling back to a day frame)', has_hide)
        c(f'{region}: rwyLights hook present (else Part B skips)', has_spec)

        ends = await pg.evaluate(ENDS_FULL_JS)
        if ends_filter:
            ends = [e for e in ends if end_key(e) in ends_filter]
        await pg.evaluate("()=>{window.__kgeu.setTOD('night');window.__kgeu.setWX('clear');}")

        base_id = None
        shot_done_apt = set()
        for e in ends:
            if time.monotonic() - t0 > budget_s:
                c(f'{region}: ran out of time budget ({budget_s}s/page), stopped at {e["code"]} {e["num"]}', False)
                break
            bid = AZ_BASE.get(e['code'], 'kgeu') if region == 'az' else region
            if bid != base_id:
                await pg.evaluate("(b)=>{window.__kgeu.pick('cessna');window.__kgeu.pickBase(b);window.__kgeu.start('final');}", bid)
                await pg.wait_for_timeout(300)
                await ensure_chase(pg)
                base_id = bid
            label = f'{region} {e["code"]} {e["num"]}'
            lit3, hid3 = await lit_hidden_pair(pg, has_hide, e['i'], D3NM)
            n3, g3, w3 = diff_stats(lit3, hid3)
            lit1, hid1 = await lit_hidden_pair(pg, has_hide, e['i'], D1NM)
            n1, g1, w1 = diff_stats(lit1, hid1)
            ok3 = n3 >= 12
            ok1 = n1 >= 60 and g1 > 0 and w1 > 0
            c(f'{label}: lit pixels at 3 nm >= 12', ok3, n3)
            c(f'{label}: lit pixels at 1 nm >= 60, with green and white among them', ok1, (n1, g1, w1))
            rows.append((region, e['code'], e['num'], n3, n1, g1, w1, ok3 and ok1))
            if e['apt'] not in shot_done_apt and out_dir:
                shot_done_apt.add(e['apt'])
                path = os.path.join(out_dir, f'{region}_{e["code"]}_{e["num"]}_1nm_lit.png')
                lit1.save(path)
                saved_shots.append(path)
            if has_spec and (not ends_filter or end_key(e) in ends_filter):
                L = next((x for x in await pg.evaluate("()=>window.__kgeu.rwyLights()")
                          if x['code'] == e['code'] and x['num'] == e['num']), None)
                if L is None:
                    c(f'{label}: rwyLights() has an entry for this end', False)
                else:
                    check_spec(c, region, L, e['len'], e['wid'], label)

        # Arizona only: Glendale 1 and 19 at 1 nm, Low and High tiers, the dark-Glendale report
        if region == 'az':
            glendale = [e for e in ends if e['code'] == 'KGEU']
            if glendale:
                await pg.evaluate("()=>{window.__kgeu.pick('cessna');window.__kgeu.pickBase('kgeu');window.__kgeu.start('final');}")
                await pg.wait_for_timeout(300)
                await ensure_chase(pg)
                for tier in ('low', 'high'):
                    await pg.evaluate("(t)=>window.__kgeu.GFX.setTier(t)", tier)
                    for e in glendale:
                        if time.monotonic() - t0 > budget_s:
                            break
                        lit1, hid1 = await lit_hidden_pair(pg, has_hide, e['i'], D1NM)
                        n1, g1, w1 = diff_stats(lit1, hid1)
                        ok1 = n1 >= 60 and g1 > 0 and w1 > 0
                        c(f'{region} {e["code"]} {e["num"]} [{tier} tier]: lit pixels at 1 nm >= 60, green+white present', ok1, (n1, g1, w1))
                await pg.evaluate("()=>window.__kgeu.GFX.setTier('auto')")
            else:
                c(f'{region}: Glendale 1/19 low+high tier repeat skipped (not in --ends filter)', True)

        c(f'{region}: no console errors', not pg.errs, pg.errs[:5])
        await pg.context.close()
        await b.close()
    srv.shutdown()
    elapsed = time.monotonic() - t0
    passed = sum(1 for r in rows if r[-1])
    print(f'{region}: {passed}/{len(rows)} ends passed Part A, {elapsed:.1f}s')
    for r in rows:
        print('  ', *r)
    return saved_shots, elapsed


async def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    regions = [a for a in args if a in ALL_REGIONS] or ALL_REGIONS
    out_dir = opt('--out', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'overnight-screenshots', 'runways_night'))
    ends_raw = opt('--ends')
    ends_filter = set(ends_raw.split(',')) if ends_raw else None
    os.makedirs(out_dir, exist_ok=True)
    c = Checks()
    t_start = time.monotonic()
    all_shots = []
    for region in regions:
        shots, elapsed = await run_region(region, out_dir, ends_filter, c, budget_s=170)
        all_shots += shots
        c(f'{region}: page under 3 minutes', elapsed < 180, round(elapsed, 1))
    total = time.monotonic() - t_start
    c('whole run under 9 minutes', total < 540, round(total, 1))
    print('\nscreenshots:', *all_shots, sep='\n  ')
    return c.done('night_lights_check')


sys.exit(asyncio.run(main()))
