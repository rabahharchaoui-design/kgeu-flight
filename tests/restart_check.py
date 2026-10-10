# Phone3 item 1: every start comes back exactly. Each start type (runway, ramp, 3 mi and 1 mi final at
# both Arizona bases, the missions, every arcade game, every lesson, the dogfight, and a world region's
# free flight, finals and airport challenge) is started, then restarted through the pause sheet's
# Restart button (a real tap), then retried through the crash card's RETRY after a forced crash, then
# through the results card's Try again path (runRestart). Each time the position, the distance to the
# runway threshold, the height and the label (the run's start record, spawn, arcade kind, lesson, the
# HUD mission line) must match the first start. iPhone 844x390, Hard and Easy.
# Run: .venv/bin/python tests/restart_check.py
import asyncio, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, IPHONE_15
ok = Checks()
K = 'window.__kgeu'

SNAP = """()=>{const K=window.__kgeu,s=K.state(),B=K.BASES[s.base],h=B.hdg*Math.PI/180,f=B.fin(0),dx=s.pos.x-f[0],dz=s.pos.z-f[1];
  const R=K.RUNSTART(),m=document.getElementById('miss');
  return {x:Math.round(s.pos.x),z:Math.round(s.pos.z),ft:Math.round(s.agl*3.28084),
    dist:Math.round(Math.hypot(dx,dz)),type:s.type,mode:s.mode,spawn:s.spawn||'',base:s.base,
    label:JSON.stringify(R)+'|'+(K.ARC.on?K.ARC.kind:'')+'|'+(K.LES.on||'')+'|'+(K.DF.live?'df':'')+'|'+(m&&m.classList.contains('on')?m.textContent.replace(/[0-9:]/g,'').trim().slice(0,40):'')}}"""

def same(a, b):
    return all(abs(a[k] - b[k]) <= 2 for k in ('x', 'z', 'ft', 'dist')) and all(a[k] == b[k] for k in ('type', 'mode', 'spawn', 'base', 'label'))

STEP = f"()=>{K}.stepFrame(1/30,false,true)"

async def snap(pg):
    await pg.evaluate(STEP)
    return await pg.evaluate(SNAP)

async def run_one(pg, name, js):
    await pg.evaluate(f"()=>{{{js}}}"); await pg.wait_for_timeout(250)
    a = await snap(pg)
    # Restart from the pause sheet, a real tap
    await pg.evaluate(f"()=>{{if(!{K}.paused()){K}.togglePause()}}"); await pg.wait_for_timeout(350)
    await pg.evaluate("()=>{const b=document.getElementById('pApply');b.textContent}")
    r = await pg.evaluate("()=>{const e=document.getElementById('pApply'),r=e.getBoundingClientRect();return [r.x+r.width/2,r.y+r.height/2,e.textContent]}")
    await pg.touchscreen.tap(r[0], r[1]); await pg.wait_for_timeout(350)
    b = await snap(pg)
    ok(f'{name}: pause Restart ({r[2]}) gives the same start', r[2] == 'Restart' and same(a, b), {'first': a, 'restart': b})
    # RETRY on the crash card
    await pg.evaluate(f"()=>{K}.crashNow('Test crash.')")
    for _ in range(4): await pg.evaluate(STEP)
    await pg.evaluate(f"()=>{K}.crashRetry()"); await pg.wait_for_timeout(250)
    c = await snap(pg)
    ok(f'{name}: crash RETRY gives the same start', same(a, c), {'first': a, 'retry': c})
    # the results cards' Try again
    await pg.evaluate(f"()=>{K}.runRestart()"); await pg.wait_for_timeout(250)
    d = await snap(pg)
    ok(f'{name}: results Try again gives the same start', same(a, d), {'first': a, 'again': d})
    return a

AZ = [
    ('runway kgeu', f"{K}.pick('cessna');{K}.pickBase('kgeu');{K}.start('runway')"),
    ('ramp kgeu', f"{K}.pick('cessna');{K}.pickBase('kgeu');{K}.start('ramp')"),
    ('3 mi final kgeu', f"{K}.pick('cessna');{K}.pickBase('kgeu');{K}.start('final')"),
    ('1 mi final kgeu', f"{K}.pick('f16');{K}.pickBase('kgeu');{K}.start('final1')"),
    ('1 mi final luke', f"{K}.pick('c130');{K}.pickBase('luke');{K}.start('final1')"),
    ('3 mi final luke', f"{K}.pick('reaper');{K}.pickBase('luke');{K}.start('final')"),
    ('runway luke', f"{K}.pick('mq9b');{K}.pickBase('luke');{K}.start('runway')"),
    ('mission short field', f"{K}.pick('c130');{K}.start('short')"),
    ('mission dash', f"{K}.pick('f16');{K}.start('runway','luke')"),
    ('arcade airdrop', f"{K}.pick('c130');{K}.start('drop')"),
    ('arcade strike', f"{K}.pick('reaper');{K}.start('range')"),
    ('arcade landing', f"{K}.pick('alpha');{K}.arcStart('landing')"),
    ('arcade 1 mile', f"{K}.pick('f16');{K}.arcStart('landing1')"),
    ('arcade daily', f"{K}.dailyRegion('az');{K}.arcStart('daily')"),
    ('dogfight', f"{K}.dfStart()"),
] + [(f'lesson {l}', f"{K}.startLesson('{l}',true)") for l in ('first', 'steep', 'slow', 'stall', 'engine', 'pattern')]

WORLD = [
    ('rjtt runway', f"{K}.pick('cessna');{K}.start('runway')"),
    ('rjtt 3 mi final', f"{K}.pick('c130');{K}.start('final')"),
    ('rjtt 1 mi final', f"{K}.pick('f16');{K}.start('final1')"),
    ('rjtt airport challenge', f"{K}.pick('alpha');{K}.arcStart('apt')"),
]

async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        for skill in ('pilot', 'rookie'):
            M = 'Hard' if skill == 'pilot' else 'Easy'
            pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': skill, 'kgeuTut': '1', 'kgeuCoach': '3'})
            await pg.wait_for_function(f"()=>{K}&&{K}.WORLD.ready", timeout=30000)
            for name, js in AZ:
                a = await run_one(pg, f'{M} {name}', js)
                if name.startswith('1 mi final') or name == 'arcade 1 mile':
                    ok(f'{M} {name}: really 1 mile out (about 1,852 m, about 300 ft)', 1600 < a['dist'] < 2100 and 250 < a['ft'] < 400, a)
                if name.startswith('3 mi final'):
                    ok(f'{M} {name}: really 3 miles out', 5300 < a['dist'] < 5900, a)
            ok(f'{M}: no page errors', not pg.errs, pg.errs[:3])
            await pg.context.close()
        pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3', 'kgeuRegion': 'rjtt'})
        await pg.wait_for_function(f"()=>{K}&&{K}.WORLD.ready", timeout=30000)
        for name, js in WORLD:
            a = await run_one(pg, name, js)
            if '1 mi' in name: ok(f'{name}: really 1 mile out', 1700 < a['dist'] < 2100, a)
        ok('rjtt: no page errors', not pg.errs, pg.errs[:3])
        await pg.context.close()
        await b.close()
    srv.shutdown()
    sys.exit(ok.done('restart_check'))

asyncio.run(main())
