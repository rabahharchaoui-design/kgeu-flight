# Weather session: the world regions' local weather, iPhone landscape 844x390 at 2x: Tokyo and Paris overcast and rain,
# Rio showers and scattered, the Cessna on 3 mile final by day, chase and cockpit.
#   .venv/bin/python tests/weather_region_shots.py <root> <outdir>
import asyncio, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from playwright.async_api import async_playwright
from harness import serve, launch, page, IPHONE_15
K = 'window.__kgeu'
BASE = {'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3', 'kgeuPlace': '{"level":"ride","hours":null}'}
SCENES = [('rjtt', 'overcast'), ('rjtt', 'rain'), ('lfpg', 'overcast'), ('lfpg', 'rain'), ('sbrj', 'rain'), ('sbrj', 'scattered')]
async def main():
    root, out = os.path.abspath(sys.argv[1]), sys.argv[2]; os.makedirs(out, exist_ok=True); errs = []
    async with async_playwright() as p:
        b = await launch(p)
        srv, url = serve()   # the harness serves the repo root
        for region, wx in SCENES:
            storage = dict(BASE); storage['kgeuRegion'] = region
            pg = await page(b, url, vp=IPHONE_15, storage=storage)
            await pg.wait_for_function(f"()=>{K}.WORLD.ready||{K}.WORLD.err", timeout=30000)
            await pg.evaluate(f"()=>{{{K}.setTOD('day');{K}.setWX('{wx}');{K}.pick('cessna');{K}.pickPos('final');{K}.start('final');}}")
            await pg.wait_for_timeout(3500)
            await pg.screenshot(path=os.path.join(out, f'{region}_{wx}_final_chase.png'))
            await pg.evaluate(f"()=>{K}.cycleCam()"); await pg.wait_for_timeout(1200)
            await pg.screenshot(path=os.path.join(out, f'{region}_{wx}_final_cockpit.png'))
            info = await pg.evaluate(f"()=>({{wx:{K}.WX().id,atis:{K}.atis()}})")
            print(region, wx, info['atis'][:110]); errs += list(pg.errs)
            await pg.context.close()
        await b.close()
    print('weather_region_shots:', len(SCENES) * 2, 'shots, page errors:', errs)
    sys.exit(1 if errs else 0)
asyncio.run(main())
