# School1 item 2 screenshots: the stage map and the placement intake.
# map_<WxH>: stage 1 selected, a student placement with first and pattern passed; map_s3_<WxH>: stage 3 selected (locked);
# intake_<WxH>: the intake with one option picked. At 844x390, 568x320 and 390x844, the intake also at 667x375.
# brief_card1_<WxH>, brief_quiz_<WxH> (item 3): slow flight's briefing, card 1 and the quiz answered wrong.
# Run: .venv/bin/python tests/school_shots.py
import asyncio, os
from playwright.async_api import async_playwright
from harness import serve, launch, page

SHOTS = os.path.join(os.path.dirname(__file__), '..', 'overnight-screenshots', 'school1')
os.makedirs(SHOTS, exist_ok=True)
K = 'window.__kgeu'
BASE = {'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3', 'kgeuSchool': '{"cessna:first":"A","cessna:pattern":"B"}'}
SIZES = [(844, 390), (568, 320), (390, 844)]

async def shot(pg, name):
    await pg.wait_for_timeout(450)   # past the fades
    p = os.path.abspath(os.path.join(SHOTS, name)); await pg.screenshot(path=p); print(p)

async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        for W, H in SIZES:
            pg = await page(b, url, vp={'width': W, 'height': H}, storage=dict(BASE, kgeuPlace='{"level":"student","hours":12.5}'))
            await pg.evaluate("()=>document.body.classList.add('portraitok')")
            await pg.evaluate(f"()=>{{{K}.openMenu('sSchool');{K}.schSelect('s1')}}")
            await shot(pg, f'map_{W}x{H}.png')
            await pg.evaluate(f"()=>{K}.schSelect('s3')")
            await shot(pg, f'map_s3_{W}x{H}.png')
            await pg.context.close()
        for W, H in SIZES + [(667, 375)]:
            pg = await page(b, url, vp={'width': W, 'height': H}, storage=BASE)
            await pg.evaluate(f"()=>{{document.body.classList.add('portraitok');{K}.openMenu('sSchool')}}"); await pg.wait_for_timeout(300)
            await pg.evaluate("()=>document.querySelector('#plOpts [data-lv=solo]').click()")
            await shot(pg, f'intake_{W}x{H}.png')
            await pg.context.close()
        # school1 item 3: the lesson briefing, card 1 and the quiz with an answer tapped (a wrong one: red, the right one outlined)
        for W, H in SIZES:
            pg = await page(b, url, vp={'width': W, 'height': H}, storage=dict(BASE, kgeuPlace='{"level":"solo","hours":null}'))
            await pg.evaluate(f"()=>{{document.body.classList.add('portraitok');{K}.startLesson('slow')}}")
            await shot(pg, f'brief_card1_{W}x{H}.png')
            for i in range(3): await pg.evaluate(f"()=>{K}.lesBriefNext()"); await pg.wait_for_timeout(400)
            await pg.wait_for_function(f"()=>{{const t=document.getElementById('brTrack');return Math.abs(t.scrollLeft-3*t.clientWidth)<2}}", timeout=8000)
            await pg.evaluate("()=>document.querySelector('#brTrack .brQ .brAns:nth-child(2)').click()")
            await shot(pg, f'brief_quiz_{W}x{H}.png')
            await pg.context.close()
        await b.close()
    srv.shutdown()
asyncio.run(main())
