# Crash explosions (3.9): every crash explodes, scaled by the airframe, through the pooled
# explode() system. For each type: take off from runway 1 at Glendale, climb to ~150 ft,
# force a crash, then check the explosion slot and its scale, the wreck pieces for that
# profile (drone wings, C-130 in three, F-16 trail), secondaries, the airframe gone, the
# card (hidden at 2.5 s, RETRY and MENU at 3.5 s), pieces retiring by 60 s, and RETRY back
# at the start. Then frame time during the C-130 crash against a clean C-130 flight.
# Screenshots to overnight-screenshots/crash/.
# Run: .venv/bin/python tests/crash_check.py [--noshots]
import asyncio, os, sys, math
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, IPHONE_15, finger

ok = Checks()
SHOTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'overnight-screenshots', 'crash')
SHOT = '--noshots' not in sys.argv
K = 'window.__kgeu'
TYPES = ['cessna', 'archer', 'alpha', 'reaper', 'mq9b', 'f16', 'a10', 'c130', 'b737']
SCALE = {'cessna': 0.8, 'archer': 0.8, 'alpha': 0.8, 'reaper': 0.9, 'mq9b': 0.9, 'f16': 1.6, 'a10': 1.7, 'c130': 2.6, 'b737': 2.7}
SEC = {'cessna': 0, 'archer': 0, 'alpha': 0, 'reaper': 1, 'mq9b': 1, 'f16': 2, 'a10': 2, 'c130': 3, 'b737': 3}

async def step(pg, secs, dt=1/30, render=False):
    await pg.evaluate("([n,dt,r])=>{const K=window.__kgeu;for(let i=0;i<n;i++)K.stepFrame(dt,false,true);if(r)K.stepFrame(1/60);}",
                      [max(1, round(secs/dt)), dt, render])

async def shot(pg, name):
    if not SHOT: return
    await pg.evaluate(f"()=>{{{K}.stepFrame(1/60);document.getElementById('toast').classList.remove('on');document.getElementById('bigFlash').style.visibility='hidden';}}")
    await pg.wait_for_timeout(450)   # let the card finish sliding in
    p = os.path.join(SHOTS, name); await pg.screenshot(path=p, timeout=120000); print('  wrote', os.path.relpath(p))
    await pg.evaluate("()=>{document.getElementById('bigFlash').style.visibility='';}")

async def climb(pg, ft=150, limit=150):
    """Auto takeoff from the runway, stepping until the aircraft is ft above the ground."""
    await pg.evaluate(f"()=>{K}.auto()")
    t = 0
    while t < limit:
        await step(pg, 1.0)
        t += 1
        agl = await pg.evaluate(f"()=>{K}.state().agl*3.28084")
        if agl >= ft: return agl
    return agl

async def card(pg):
    return await pg.evaluate("""()=>{const c=document.getElementById('crash'),r=c.getBoundingClientRect(),cs=getComputedStyle(c);
      const b=id=>{const e=document.getElementById(id);if(!e)return null;const q=e.getBoundingClientRect();return {w:q.width,h:q.height,txt:e.textContent.trim(),inView:q.bottom<=innerHeight+0.5&&q.top>=-0.5}};
      return {on:c.classList.contains('on'),pe:cs.pointerEvents,top:document.getElementById('crashTop').classList.contains('on'),
        topTxt:document.getElementById('crashTop').textContent,retry:b('cRetry'),menu:b('cMenu'),old:!!document.getElementById('cRunway'),
        h:r.height,bottom:r.bottom,vh:innerHeight}}""")

async def frame_ms(pg, n=40):
    """Mean wall time of a rendered frame, with a 1 px readback so the GPU work is counted."""
    return await pg.evaluate("""(n)=>{const K=window.__kgeu,c=document.getElementById('gl'),gl=c.getContext('webgl2')||c.getContext('webgl'),px=new Uint8Array(4);
      K.stepFrame(1/60);gl.readPixels(0,0,1,1,gl.RGBA,gl.UNSIGNED_BYTE,px);
      const t0=performance.now();for(let i=0;i<n;i++){K.stepFrame(1/60);gl.readPixels(0,0,1,1,gl.RGBA,gl.UNSIGNED_BYTE,px);}
      return (performance.now()-t0)/n;}""", n)

async def main():
    os.makedirs(SHOTS, exist_ok=True)
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'})
        await pg.evaluate(f"()=>{{{K}.setSkill('pilot');{K}.setTOD('day');{K}.setRadioOn&&{K}.setRadioOn(false);}}")
        await pg.evaluate(f"()=>{{{K}.WST.off=true;}}")   # the explosion in sim time; WASTED (phone3 item 7) has its own wasted_check
        for i, t in enumerate(TYPES):
            if t == 'c130': await pg.evaluate(f"()=>{K}.setSkill('rookie')")   # both skills get the same card
            await pg.evaluate(f"()=>{{{K}.pick('{t}');{K}.pickBase({K}.baseOK('{t}','kgeu')?'kgeu':'phx');{K}.start('runway');}}")
            await step(pg, 0.2)
            s0 = await pg.evaluate(f"()=>{{const s={K}.state();return {{x:s.pos.x,z:s.pos.z,mode:s.mode,base:s.base}}}}")
            agl = await climb(pg)
            ok(f'{t}: climbed to ~150 ft', agl >= 140, f'{agl:.0f} ft')
            await pg.evaluate(f"()=>{K}.crashNow('Test crash: {t}.')")
            await step(pg, 0.05)
            f = await pg.evaluate(f"()=>{K}.crashFx()")
            c0 = await card(pg)
            ok(f'{t}: impact shows the reason at the top, no card', c0['top'] and not c0['on'] and c0['topTxt'].startswith('Test crash'), c0['topTxt'])
            ok(f'{t}: airframe hidden, props and burner off', not f['planeVisible'] and (await pg.evaluate(f"()=>{K}.prop().rate")) == 0
               and (await pg.evaluate(f"()=>{K}.ab().flameLen")) == 0 and not (await pg.evaluate(f"()=>{K}.acLights().landingOn")))
            ok(f'{t}: boom arrives after distance/340', 0 <= f['boomAt'] < 0.5, f"{f['boomAt']:.3f} s")
            await step(pg, 0.95, render=True)
            await shot(pg, f'{t}_crash_1s.png')
            slots = await pg.evaluate(f"()=>{K}.fxSlots()")
            ok(f'{t}: explosion slot running at scale {SCALE[t]}', any(abs(s['scale'] - SCALE[t]) < 1e-6 for s in slots), [s['scale'] for s in slots])
            f = await pg.evaluate(f"()=>{K}.crashFx()")
            ok(f'{t}: crashFx scale and secondaries', f['type'] == t and abs(f['scale'] - SCALE[t]) < 1e-6 and f['secondaries'] == SEC[t], f)
            kinds = f['kinds']
            if t in ('cessna', 'alpha'):
                ok(f'{t}: burning hull and tail', kinds.get('hull') == 1 and kinds.get('tail') == 1 and f['mainFire'] >= 40, kinds)
            if t in ('reaper', 'mq9b'):
                ok(f'{t}: both wings break off', kinds.get('wing') == 2 and kinds.get('hull') == 1, kinds)
            if t == 'f16':
                ok('f16: 6 to 10 trail pieces plus the hull', 6 <= kinds.get('trail', 0) <= 10 and kinds.get('hull') == 1, kinds)
            if t == 'c130':
                ok('c130: fuselage in three (nose, centre, tail) and a debris field', kinds.get('nose') == 1 and kinds.get('centre') == 1
                   and kinds.get('tail') == 1 and kinds.get('chunk', 0) >= 4, kinds)
                ok('c130: wreck burns ~90 s', f['mainFire'] >= 85, f['mainFire'])
            ok(f'{t}: pool cap (<= 12 pieces)', f['pieces'] <= 12, f['pieces'])
            if t == 'c130':
                await step(pg, 1.0, render=True)
                await pg.evaluate(f"()=>{K}.setTOD('night')")
                await step(pg, 0.05, render=True)
                await shot(pg, 'c130_crash_night_2s.png')
                await pg.evaluate(f"()=>{K}.setTOD('day')")
                await step(pg, 0.45)
            else:
                await step(pg, 1.5)
            c = await card(pg)
            ok(f'{t}: card still hidden at 2.5 s', not c['on'] and c['pe'] == 'none', c)
            await step(pg, 1.0)
            await pg.wait_for_timeout(450)   # the slide-in is a real-time CSS transition
            c = await card(pg)
            f = await pg.evaluate(f"()=>{K}.crashFx()")
            if t == 'c130': ok('c130: 4 fuel tank fireballs over 2.5 s', f['fireballs'] == 4, f['fireballs'])
            else: ok(f'{t}: one fireball', f['fireballs'] == 1, f['fireballs'])
            ok(f'{t}: card up at 3.5 s with RETRY and MENU only', c['on'] and c['retry'] and c['menu'] and c['retry']['txt'] == 'RETRY'
               and c['menu']['txt'] == 'MENU' and not c['old'] and not c['top'], c)
            ok(f'{t}: buttons 44 pt and on screen', all(x['w'] >= 44 and x['h'] >= 44 and x['inView'] for x in (c['retry'], c['menu'])), c)
            ok(f'{t}: card is compact (under 30% of the height)', c['h'] < 0.3 * c['vh'], f"{c['h']:.0f} of {c['vh']}")
            await step(pg, 0.5, render=True)
            await shot(pg, f'{t}_crash_4s.png')
            if t == 'f16':
                await step(pg, 3.0, render=True)
                await shot(pg, 'f16_trail_day.png')
                f = await pg.evaluate(f"()=>{K}.crashFx()")
                ok('f16: trail flung along the path, out to ~120 m', 50 < f['trailMax'] < 200, f"{f['trailMax']:.0f} m")
            if t in ('reaper', 'mq9b'):
                await step(pg, 3.0)
                f = await pg.evaluate(f"()=>{K}.crashFx()")
                ok(f'{t}: wings land within ~40 m', f['wingMax'] < 50, f"{f['wingMax']:.0f} m")
            await step(pg, 60, dt=0.1)
            f = await pg.evaluate(f"()=>{K}.crashFx()")
            ok(f'{t}: every piece retired 60 s on', f['pieces'] == 0 and f['flames'] == 0, f)
            await finger(pg, '#cRetry')
            await step(pg, 0.2)
            s1 = await pg.evaluate(f"()=>{{const s={K}.state();return {{x:s.pos.x,z:s.pos.z,mode:s.mode,base:s.base,crashed:s.crashed}}}}")
            c = await card(pg)
            d = math.hypot(s1['x'] - s0['x'], s1['z'] - s0['z'])
            ok(f'{t}: RETRY flies again from the same start', not s1['crashed'] and s1['mode'] == s0['mode'] and s1['base'] == s0['base']
               and d < 3 and not c['on'] and not c['top'], f'{d:.1f} m {s1}')
            ok(f'{t}: airframe back', await pg.evaluate(f"()=>{K}.plane().g.visible"))
        await pg.evaluate(f"()=>{K}.setSkill('pilot')")

        # ---------- frame time: C-130 crash vs a clean C-130 flight ----------
        await pg.evaluate(f"()=>{{{K}.pick('c130');{K}.pickBase('kgeu');{K}.start('runway');}}")
        await climb(pg)
        await step(pg, 2.0)
        clean = await frame_ms(pg)
        await pg.evaluate(f"()=>{K}.crashNow('Frame time crash.')")
        await step(pg, 0.3)
        boom = await frame_ms(pg, 60)   # 0.3 s to 1.3 s: the fireballs at their biggest
        await step(pg, 1.2)
        late = await frame_ms(pg, 40)
        r = clean / max(boom, late)
        ok('C-130 crash frame time within 0.8 of a clean flight', r > 0.8, f'clean {clean:.1f} ms, crash {boom:.1f} ms, 2.5 s on {late:.1f} ms, ratio {r:.2f}')
        await step(pg, 1.5)
        await pg.wait_for_timeout(450)
        await finger(pg, '#cMenu')
        await step(pg, 0.1)
        ok('MENU opens the menu', await pg.evaluate("()=>document.getElementById('menu').classList.contains('on')"))
        await pg.evaluate("()=>window.__kgeu.stepFrame(0,true)")
        ok('no page errors', not pg.errs, pg.errs[:3])
        await b.close()
    srv.shutdown()
    sys.exit(ok.done('crash_check'))

asyncio.run(main())
