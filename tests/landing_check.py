# Feature 2: a landing never stops the flight. The grade is a small badge that
# slides in, fades on its own, and only pauses when tapped. Touch and goes work.
# Run: .venv/bin/python tests/landing_check.py
import asyncio, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, finger
ok = Checks()

S = "()=>{const s=window.__kgeu.state();return {g:s.onGround,v:Math.hypot(s.vel.x,s.vel.z),x:s.pos.x,z:s.pos.z,air:s.airTime,crash:s.crashed,ap:s.ap&&s.ap.mode}}"
UI = """()=>({paused:window.__kgeu.paused(),card:document.getElementById('landOv').classList.contains('on'),
  badge:document.getElementById('gBadge').classList.contains('on'),text:document.getElementById('gBadge').textContent})"""

async def land(pg, typ='cessna'):
    await pg.evaluate(f"()=>{{window.__kgeu.pick('{typ}');window.__kgeu.pickBase('kgeu');window.__kgeu.start('final');}}")
    await pg.wait_for_timeout(300)
    await pg.evaluate("()=>window.__kgeu.auto()")
    for _ in range(80):
        await pg.evaluate("()=>window.__kgeu.ff(3)")
        await pg.wait_for_timeout(120)
        st = await pg.evaluate(S)
        if st['g'] or st['crash']: return st
    return st

async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, storage={'kgeuOnboard': 'rookie', 'kgeuTut': '1', 'kgeuCoach': '3'})
        st = await land(pg)
        ok('autoland reaches the runway', st['g'] and not st['crash'], st)
        await pg.wait_for_timeout(400)
        ui = await pg.evaluate(UI)
        ok('touchdown does not pause the game', not ui['paused'], ui)
        ok('touchdown does not open the grade card', not ui['card'], ui)
        ok('grade badge slides in with letter and one line', ui['badge'] and len(ui['text']) > 4, ui['text'])
        a = await pg.evaluate(S)
        await pg.evaluate("()=>window.__kgeu.ff(2)"); await pg.wait_for_timeout(300)
        c = await pg.evaluate(S)
        moved = ((c['x']-a['x'])**2 + (c['z']-a['z'])**2) ** 0.5
        ok('the aircraft keeps rolling out after touchdown', c['g'] and moved > 5 and c['v'] < a['v'] + 0.5,
           f"moved {moved:.0f} m, {a['v']:.1f} -> {c['v']:.1f} m/s")
        await pg.evaluate("()=>window.__kgeu.ff(40)"); await pg.wait_for_timeout(400)
        d = await pg.evaluate(S)
        ok('rollout brakes to taxi speed', d['v'] < 12 and not d['crash'], f"{d['v']:.1f} m/s")
        await pg.wait_for_timeout(5200)
        ui = await pg.evaluate(UI)
        ok('badge fades out on its own after about 4 s', not ui['badge'], ui)
        rec = await pg.evaluate("()=>(window.__kgeu.SCORE.recent||[]).length")
        ok('full breakdown saved to Records', rec >= 1, rec)

        # tapping the badge is the only thing that pauses
        st = await land(pg); await pg.wait_for_timeout(300)
        pre = await pg.evaluate(UI)
        ok('second landing shows the badge', pre['badge'], (st, pre))
        await finger(pg, '#gBadge'); await pg.wait_for_timeout(300)
        ui = await pg.evaluate(UI)
        ok('tapping the badge opens the details and pauses', ui['card'] and ui['paused'], ui)
        await finger(pg, '#lKeep'); await pg.wait_for_timeout(300)
        ui = await pg.evaluate(UI)
        ok('Keep flying closes the card and resumes', not ui['card'] and not ui['paused'], ui)

        # touch and go: land, take the airplane, full power, fly away
        st = await land(pg)
        await pg.evaluate("()=>{const s=window.__kgeu.state();s.ap=null;s.apW=null;s.throttle=1;}")
        flew = False
        for _ in range(20):
            await pg.evaluate("()=>window.__kgeu.ff(2)"); await pg.wait_for_timeout(120)
            e = await pg.evaluate(S)
            if not e['g'] and e['air'] > 1: flew = True; break
        ui = await pg.evaluate(UI)
        ok('touch and go lifts off again with no pause', flew and not ui['paused'] and not e['crash'], e)
        ok('no page errors', not pg.errs, pg.errs[:3])
        await b.close()
    sys.exit(ok.done('landing_check'))

asyncio.run(main())
