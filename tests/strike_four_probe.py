# Fix2 item 5 round 2: strike_check's four shot sequence without its 9 minutes. Same page set up as strike_check
# (file:// URL, 932x430, no seeded storage), real time frames: two shots (a hit, then the laser walked off and the
# track broken), then two more with __kgeu.fire() waiting in 250 ms steps, then FIRE with empty rails. A crash handler
# and a console watcher print the last lines if the page dies.
# Run: .venv/bin/python tests/strike_four_probe.py
import asyncio, os, sys, time
from playwright.async_api import async_playwright
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
THREE = open(os.path.join(ROOT, 'node_modules/three/build/three.min.js')).read()
URL = 'file://' + os.path.join(ROOT, 'index.html')
K = 'window.__kgeu'
fails = []
def chk(n, c, d=''):
    print(('  ok   ' if c else '  FAIL ') + n + (('  ' + str(d)) if d else ''))
    if not c: fails.append(n)

async def main():
    async with async_playwright() as p:
        logs = []
        b = await p.chromium.launch(args=['--use-gl=swiftshader', '--enable-unsafe-swiftshader'])
        T0 = time.time()
        b.on('disconnected', lambda _: print(f'  BROWSER DISCONNECTED at {time.time()-T0:.1f} s. last console lines:\n    ' + '\n    '.join(logs[-12:])))
        ctx = await b.new_context(viewport={'width': 932, 'height': 430}, has_touch=True, is_mobile=True)
        logs = []
        pg = await ctx.new_page(); errs = []
        pg.on('close', lambda _: print(f'  page closed at {time.time()-T0:.1f} s'))
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.on('console', lambda m: logs.append(f'{time.time():.1f} {m.type}: {m.text[:200]}'))
        pg.on('crash', lambda _: print('  PAGE CRASHED. last console lines:\n    ' + '\n    '.join(logs[-12:])))
        await pg.route('**/three.min.js', lambda r: r.fulfill(body=THREE, content_type='application/javascript'))
        await pg.route('**/fonts.googleapis.com/**', lambda r: r.abort())
        await pg.goto(URL); await pg.wait_for_timeout(2200)
        await pg.wait_for_function("()=>{const s=document.getElementById('splash');return !s||s.classList.contains('gone')}", timeout=30000)
        await pg.evaluate(f"()=>{K}.mission('range')"); await pg.wait_for_timeout(1500)
        async def down(tag, fast=False):
            t0 = time.time()
            if fast:   # sim time: stepFrame bursts, then let the real loop run again
                await pg.evaluate("()=>{const K=window.__kgeu;let n=0;while(K.STRIKE.missiles.length&&n++<2400)K.stepFrame(1/30,false,true);K.stepFrame(0,true);}")
            for _ in range(140):
                if await pg.evaluate(f"()=>{K}.STRIKE.missiles.length") == 0: break
                await pg.wait_for_timeout(250)
            s = await pg.evaluate(f"()=>{K}.strike()")
            print(f'  {tag}: {time.time()-t0:.0f} s', s)
            return s
        # 1: the bunker, held
        i = await pg.evaluate(f"()=>{K}.STRIKE.targets.findIndex(t=>t.kind==='bunker')")
        a = await pg.evaluate(f"(i)=>{K}.strikeAim(i,0)", i); chk('bunker aimed', a['ok'], a)
        await pg.evaluate(f"()=>{K}.fire()"); s = await down('shot 1', True); chk('shot 1 hits', s['hits'] == 1, s)
        # 2: a hull, laser walked 300 m off, then the track dropped
        i2 = await pg.evaluate(f"()=>{K}.STRIKE.targets.findIndex(t=>t.kind==='hull'&&!t.dead)")
        await pg.evaluate(f"(i)=>{K}.strikeAim(i,0)", i2)
        tp = await pg.evaluate(f"(i)=>{{const t={K}.STRIKE.targets[i];return [t.x,t.z];}}", i2)
        await pg.evaluate(f"()=>{K}.fire()"); await pg.wait_for_timeout(1500)
        await pg.evaluate("([x,z])=>{const S=window.__kgeu.SENSOR;const V=S.spot.constructor;S.tgt=null;S.track=new V(x+300,S.spot.y,z+180);}", tp)
        await pg.wait_for_timeout(1200)
        await pg.evaluate(f"()=>{{const S={K}.SENSOR;S.tgt=null;S.track=null;}}")
        s = await down('shot 2', True); chk('shot 2 misses', s['hits'] == 1 and s['shots'] == 2, s)
        # 3 and 4: exactly as strike_check lines 153 to 170
        for k in range(2):
            await pg.evaluate("""()=>{const K=window.__kgeu,S=K.SENSOR;
              const i=K.STRIKE.targets.findIndex(t=>!t.dead);K.pointAt(i);}""")
            await pg.wait_for_timeout(120)
            await pg.evaluate(f"()=>{K}.trackHere()")
            await pg.evaluate(f"()=>{K}.fire()")
            s = await down(f'shot {3+k}')
        chk('four shots, graded', s['shots'] == 4 and s['cleared'], s)
        t0 = time.time()
        for _ in range(160):
            if await pg.evaluate("()=>document.getElementById('arcOv').classList.contains('on')"): break
            await pg.wait_for_timeout(250)
        print(f'  card after {time.time()-t0:.0f} s real')
        for _ in range(20): await pg.wait_for_timeout(250)
        card = await pg.evaluate("()=>document.getElementById('arcOv').classList.contains('on')")
        chk('the card is up', card)
        chk('empty rails refused', await pg.evaluate(f"()=>{{{K}.fire();return {K}.STRIKE.shots;}}") == 4)
        for _ in range(8): await pg.wait_for_timeout(250)
        chk('no page errors', not errs, errs[:2])
        await b.close()
    print('\nstrike_four_probe: ' + ('FAILED ' + ', '.join(fails) if fails else 'all passed'))
    sys.exit(1 if fails else 0)
asyncio.run(main())
