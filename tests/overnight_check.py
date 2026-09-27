# Overnight build check: iPhone landscape, every aircraft, fps floor and console errors.
# Usage: .venv/bin/python tests/overnight_check.py <label> [type ...]
import asyncio, os, sys, json
from playwright.async_api import async_playwright

THREE = open('node_modules/three/build/three.min.js').read()
URL = 'file://' + os.path.abspath('index.html')
SHOTS = os.path.abspath('overnight-screenshots')
LABEL = sys.argv[1] if len(sys.argv) > 1 else 'run'
TYPES = sys.argv[2:] or ['cessna', 'f16', 'reaper', 'c130']
IPHONE = {'width': 844, 'height': 390}      # iPhone 14 / 15, landscape
BASE_F = os.path.join('tests', 'overnight_fps.json')
FPS_KEEP = 0.80          # a feature may cost at most 20% of the baseline frame rate
BASE = json.load(open(BASE_F)) if os.path.exists(BASE_F) else {}

fails = []
def chk(n, c, d=''):
    print(('  ok   ' if c else '  FAIL ') + n + (('  ' + d) if d else ''))
    if not c: fails.append(n)

async def fps(pg, seconds=8.0, warm=2.5):
    """Measure rAF frame rate. Headless Chromium rasterises in software, so the
    absolute number is far below a real phone; only the ratio to the stored
    baseline on this same harness is meaningful. Warm up first: the first window
    after a spawn includes shader compile and the terrain rebuild."""
    await pg.wait_for_timeout(int(warm * 1000))
    # Stop any chain from a previous call before starting this one, or every
    # measurement counts the frames of all the measurements before it too.
    await pg.evaluate("""()=>{window.__stop=1;window.__f=0;
      setTimeout(()=>{window.__stop=0;const t=()=>{if(window.__stop)return;window.__f++;requestAnimationFrame(t);};requestAnimationFrame(t);},60);}""")
    await pg.wait_for_timeout(int(seconds * 1000) + 60)
    n = await pg.evaluate("()=>{window.__stop=1;return window.__f;}")
    return n / seconds

async def main():
    os.makedirs(SHOTS, exist_ok=True)
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=swiftshader', '--enable-unsafe-swiftshader'])
        ctx = await b.new_context(viewport=IPHONE, is_mobile=True, has_touch=True,
                                  device_scale_factor=2)
        pg = await ctx.new_page()
        errs, warns = [], []
        # Requests this harness aborts on purpose (fonts) surface as console errors.
        IGNORE = ('ERR_FAILED', 'fonts.googleapis', 'ERR_ABORTED')
        def onmsg(m):
            if m.type not in ('error', 'warning'): return
            if any(k in m.text for k in IGNORE): return
            (errs if m.type == 'error' else warns).append(m.text)
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.on('console', onmsg)
        await pg.route('**/three.min.js', lambda r: r.fulfill(body=THREE, content_type='application/javascript'))
        await pg.route('**/fonts.googleapis.com/**', lambda r: r.abort())

        await pg.goto(URL)
        await pg.wait_for_timeout(2500)
        chk('page loads with no console errors', not errs, ' | '.join(errs[:3]))
        chk('menu is up', await pg.is_visible('#menu'))

        # Warm up once before measuring anything. Terrain build, shader compile and
        # texture upload all land on the first few seconds of the first flight, and
        # without this the frame rate simply tracks position in the list.
        await pg.evaluate("()=>window.__kgeu.start('runway')")
        await pg.wait_for_timeout(9000)
        await pg.evaluate("()=>window.__kgeu.openMenu&&window.__kgeu.openMenu()")
        await pg.wait_for_timeout(400)

        results = {}
        for t in TYPES:
            print(f'-- {t} --')
            ok = await pg.evaluate(f"()=>!!(window.TYPES_TEST&&window.TYPES_TEST['{t}'])")
            if not ok:
                # fall back: the picker button is the public contract
                ok = await pg.is_visible(f'.pick[data-t="{t}"]')
            chk(f'{t}: type exists', ok)
            if not ok:
                continue
            n0 = len(errs)
            await pg.evaluate(f"()=>{{window.__kgeu.pick&&window.__kgeu.pick('{t}');}}")
            await pg.wait_for_timeout(200)
            await pg.evaluate("()=>window.__kgeu.start('runway')")
            await pg.wait_for_timeout(2500)
            s = await pg.evaluate("()=>{const s=window.__kgeu.state();return {t:s.type,crashed:s.crashed,y:s.pos.y,x:s.pos.x,z:s.pos.z};}")
            chk(f'{t}: spawns as {t}', s['t'] == t, json.dumps(s))
            chk(f'{t}: not crashed on spawn', not s['crashed'])
            f = await fps(pg)
            results[t] = f
            if t in BASE:
                floor = BASE[t] * FPS_KEEP
                chk(f'{t}: {f:.1f} fps (baseline {BASE[t]:.1f}, floor {floor:.1f})',
                    f >= floor, f'{100*f/BASE[t]:.0f}% of baseline')
            else:
                print(f'  --   {t}: {f:.1f} fps, no baseline yet')
            chk(f'{t}: no new console errors', len(errs) == n0, ' | '.join(errs[n0:n0+2]))
            await pg.screenshot(path=f'{SHOTS}/{LABEL}_{t}.png')
            await pg.evaluate("()=>window.__kgeu.openMenu&&window.__kgeu.openMenu()")
            await pg.wait_for_timeout(300)

        await pg.screenshot(path=f'{SHOTS}/{LABEL}_menu.png')
        await b.close()

    print()
    print('fps:', ', '.join(f'{k} {v:.1f}' for k, v in results.items()))
    if LABEL == 'baseline':
        json.dump(results, open(BASE_F, 'w'), indent=1)
        print('wrote', BASE_F)
    if warns:
        print(f'({len(warns)} warnings, not fatal)')
    print(f'FAILS {len(fails)}' + (': ' + '; '.join(fails) if fails else ''))
    sys.exit(1 if fails else 0)

asyncio.run(main())
