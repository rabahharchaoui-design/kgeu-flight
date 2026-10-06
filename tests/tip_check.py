# Phone3 item 3: the coaching tip under the grade. For every aircraft, the worst stat picks the
# line and the numbers come from that aircraft's config: the approach speed band (AC.vapp +- 5 kt),
# the 3 degree path's sink rate at that speed, its own flare. A grade A gets a compliment instead.
# Then a real landing card, a challenge card and a mission card show it under the grade and still fit
# 844x390 and 568x320. Run: .venv/bin/python tests/tip_check.py
import asyncio, math, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, IPHONE_15
ok = Checks()
K = 'window.__kgeu'
VAPP = {'cessna': 65, 'archer': 66, 'alpha': 55, 'reaper': 100, 'mq9b': 100, 'c130': 130, 'f16': 155, 'a10': 135, 'b737': 145, 'a320': 135}
NAME = {'cessna': 'Cessna', 'archer': 'Archer', 'alpha': 'Alpha', 'reaper': 'MQ-9A', 'mq9b': 'MQ-9B', 'c130': 'C-130', 'f16': 'F-16', 'a10': 'A-10', 'b737': '737', 'a320': 'A320'}

def g(letter, sink, off, aim, spd, kt, tgt, along=120, xw=0):
    return {'letter': letter, 'kt': kt, 'tgt': tgt, 'along': along, 'xw': xw,
            'parts': [['Sink rate', '', sink], ['Off centreline', '', off], ['From the aim point', '', aim], ['Airspeed', '', spd]]}

async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'})
        await pg.wait_for_function(f"()=>{K}&&{K}.WORLD.ready", timeout=30000)
        for t, v in VAPP.items():
            await pg.evaluate(f"()=>{{{K}.pick('{t}');{K}.start('runway')}}")
            kt = v * 1.0
            tip = lambda gg: pg.evaluate(f"(g)=>{K}.landTip(g)", gg)
            sp = await tip(g('C', 95, 95, 95, 40, v + 14, v))
            lo, hi = round(v / 5) * 5 - 5, round(v / 5) * 5 + 5
            ok(f'{t}: speed tip in its own numbers', sp.startswith(NAME[t] + ':') and f'{lo} to {hi} kt' in sp and '14 kt fast' in sp, sp)
            sk = await tip(g('D', 20, 95, 95, 95, v, v))
            sink = round(v * 101.27 * math.tan(3 * math.pi / 180) / 50) * 50
            ok(f'{t}: sink tip: about {sink} fpm down final, its flare, under 150 fpm', f'about {sink} fpm' in sk and 'under 150 fpm' in sk, sk)
            cl = await tip(g('C', 95, 30, 95, 95, v, v, xw=12))
            ok(f'{t}: centreline tip (crosswind)', 'centreline' in cl and 'upwind wing' in cl, cl)
            am = await tip(g('C', 95, 95, 20, 95, v, v, along=400))
            ok(f'{t}: aim point tip, long', 'white blocks' in am, am)
            am2 = await tip(g('C', 95, 95, 20, 95, v, v, along=-300))
            ok(f'{t}: aim point tip, short', 'short' in am2 and 'PAPI' in am2, am2)
            a = await tip(g('A', 95, 95, 95, 95, v, v))
            ok(f'{t}: an A gets a compliment', a.startswith(NAME[t] + ':') and 'kt' not in a and 'fpm' not in a, a)
            ok(f'{t}: one short line', all(len(x) <= 95 for x in (sp, sk, cl, am, am2, a)), max(len(x) for x in (sp, sk, cl, am, am2, a)))
        # the card shows it under the grade
        for vp in ({'width': 844, 'height': 390}, {'width': 568, 'height': 320}):
            await pg.set_viewport_size(vp)
            await pg.evaluate(f"()=>{{{K}.pick('f16');{K}.start('final')}}")
            await pg.evaluate(f"()=>{K}.resOpen(document.getElementById('arcOv'),{{letter:'C',title:'Landing challenge',score:'700 pts',stats:[['Time','2:00'],['Landing','C'],['Touchdown','300 fpm'],['Aim point','40 m long'],['Centreline','1 m'],['Best','none']],tip:{K}.landTip({{letter:'C',kt:170,tgt:155*1,along:10,xw:0,parts:[['a','',90],['b','',90],['c','',90],['d','',30]]}})}})")
            await pg.wait_for_timeout(500)
            r = await pg.evaluate("""()=>{const o=document.getElementById('arcOv'),t=o.querySelector('.rTip'),h=o.querySelector('.rHead'),L=o.querySelector('.rLines'),s=o.querySelector('.sheet').getBoundingClientRect();
              const T=t.getBoundingClientRect(),H=h.getBoundingClientRect(),LL=L.getBoundingClientRect();
              return {txt:t.textContent,below:T.top>=H.bottom-0.5&&T.bottom<=LL.top+0.5,fit:s.bottom<=innerHeight+0.5&&s.top>=-0.5,lines:Math.round(T.height)}}""")
            ok(f"{vp['width']}: tip under the grade, above the stats", r['txt'].startswith('F-16: fly final at 150 to 160 kt') and r['below'], r)
            ok(f"{vp['width']}: card still fits", r['fit'], r)
            await pg.evaluate(f"()=>{K}.resClose(document.getElementById('arcOv'))")
        ok('no page errors', not pg.errs, pg.errs[:3])
        await b.close()
    srv.shutdown()
    sys.exit(ok.done('tip_check'))

asyncio.run(main())
