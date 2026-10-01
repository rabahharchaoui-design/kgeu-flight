# Screenshots of every menu and sheet, for the before / after record of a UI pass.
#   .venv/bin/python tests/menu_shots.py <tag>      -> overnight-screenshots/phone2/menus/<tag>_<screen>_<WxH>.png
# iPhone landscape 844x390 and 568x320, portrait 390x844. Prints nothing but the paths.
import asyncio, os, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, IPHONE_15
K = 'window.__kgeu'
TAG = sys.argv[1] if len(sys.argv) > 1 else 'shot'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'overnight-screenshots', 'phone2', 'menus')
SIZES = [IPHONE_15, {'width': 568, 'height': 320}, {'width': 390, 'height': 844}]
if '--size' in sys.argv: w, h = sys.argv[sys.argv.index('--size') + 1].split('x'); SIZES = [{'width': int(w), 'height': int(h)}]

async def shot(pg, name, vp):
    await pg.wait_for_timeout(350)
    await pg.screenshot(path=os.path.join(OUT, f'{TAG}_{name}_{vp["width"]}x{vp["height"]}.png'))

async def main():
    os.makedirs(OUT, exist_ok=True)
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        for vp in SIZES:
            # first launch: the Easy / Hard funnel
            pg = await page(b, url, vp=vp, storage={'kgeuTut': '1', 'kgeuCoach': '3'})
            await pg.evaluate("()=>{const r=document.getElementById('rotOk');if(r&&r.offsetParent)r.click();}")
            await shot(pg, 'funnel', vp)
            await pg.context.close()
            pg = await page(b, url, vp=vp, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'})
            await pg.evaluate("()=>{const r=document.getElementById('rotOk');if(r&&r.offsetParent)r.click();}")
            for scr in ('sHome', 'sFly', 'sMis', 'sSchool', 'sArc', 'sSet', 'sHelp', 'sCredits', 'sLb'):
                await pg.evaluate(f"(s)=>{{const K={K};K.openMenu();K.nav(s)}}", scr)
                await shot(pg, scr, vp)
            await pg.evaluate(f"()=>{K}.recOpen()"); await shot(pg, 'records', vp)
            await pg.evaluate("()=>document.getElementById('recOv').classList.remove('on')")
            # the callsign card
            await pg.evaluate(f"()=>{{try{{{K}.LB.csOpen('pick','settings')}}catch(e){{}}}}"); await shot(pg, 'callsign', vp)
            await pg.evaluate("()=>document.getElementById('csOv').classList.remove('on')")
            # in flight: the pause sheet, the results cards, the crash card
            await pg.evaluate(f"()=>{{const K={K};K.pick('cessna');K.pickBase('kgeu');K.start('runway')}}"); await pg.wait_for_timeout(600)
            await pg.evaluate(f"()=>{K}.togglePause()"); await shot(pg, 'pause', vp)
            await pg.evaluate(f"()=>{K}.togglePause()")
            CARDS = [('results_landing', 'landOv', True, {'letter': 'A', 'title': 'Free flight landing, Glendale runway 1', 'score': '93 pts', 'sub': 'Butter, on centerline', 'board': '',
                        'lines': '<div class=gl><span>Sink rate</span><b>101 fpm<i class="pt good">100</i></b></div><div class=gl><span>Off centreline</span><b>1.9 m<i class="pt good">100</i></b></div><div class=gl><span>From the aim point</span><b>59 m long<i class="pt good">98</i></b></div><div class=gl><span>Airspeed</span><b>55 kt vs 65<i class=pt>67</i></b></div><div class=gl><span>Flight time</span><b>2:08</b></div><div class="gl lbLine"><span>Leaderboard</span><b>#4 of 120<em>PERSONAL BEST</em></b></div>'}),
                     ('results_challenge', 'arcOv', False, {'letter': 'B', 'title': '1 mile landing challenge: 912 points', 'score': '912 pts', 'sub': 'Cessna 172', 'stars': 2, 'board': '',
                        'stats': [['Time', '1:02  (par 1:10)'], ['Landing', 'B  Smooth, on centerline'], ['Touchdown', '180 fpm, 61 kt'], ['Aim point', '40 m long'], ['Centreline', '1.2 m'], ['Best', '912 pts, 1:02']]}),
                     ('results_lesson', 'gradeOv', False, {'letter': 'A', 'title': 'Flight school: Steep turns', 'score': '94 of 100', 'board': '',
                        'lines': '<div class=ok>Bank held within 5 degrees</div><div class=ok>Altitude within 100 ft</div><div class=no>Rolled out 12 degrees late</div>'})]
            for name, ov, brief, spec in CARDS:
                await pg.evaluate(f"(o)=>{K}.resOpen(document.getElementById(o.ov),o.spec,o.brief)", {'ov': ov, 'spec': spec, 'brief': brief})
                await shot(pg, name, vp)
                await pg.evaluate(f"(ov)=>{K}.resClose(document.getElementById(ov))", ov)
            await pg.evaluate(f"()=>{K}.crashNow('Hit the ground at 140 kt')")
            for _ in range(40):
                await pg.evaluate(f"()=>{K}.stepFrame(0.1,false,true)")
                if await pg.evaluate("()=>document.getElementById('crash').classList.contains('on')"): break
            await pg.evaluate(f"()=>{K}.stepFrame(0,true)"); await pg.wait_for_timeout(1500)
            await shot(pg, 'crash', vp)
            await pg.context.close()
        await b.close()
    print(OUT)
asyncio.run(main())
