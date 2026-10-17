# Weather session screenshots: one fixed set of scenes, iPhone landscape 844x390 at 2x, for a
# before/after sheet of any build. Uses only hooks the preweather build already has (setTOD,
# setClouds, pick, pickBase, start, state, snapCam, cycleCam, haboobJump, stepFrame), so it runs on
# both sides of the weather session.
#   .venv/bin/python tests/weather_shots.py <root> <outdir> [scene,scene,...]
# Scenes: for each cloud preset (clear, scattered, monsoon) crossed with time of day (day, sunset,
# night) the Cessna on 3 mile final to KGEU (chase and cockpit), and among the clouds at 5,500 ft
# looking north west (chase and cockpit); the haboob preset on final and at the wall (chase and
# cockpit); monsoon seen from altitude; and a fly-through of a scattered cloud base that shows the
# old build cutting polygons through the camera. <outdir>/metrics.json: page errors.
import asyncio, json, os, sys, time
from playwright.async_api import async_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import graphics_shots as GS
from graphics_shots import serve, launch, open_page, fly, air, hbj, CAM0, UNMAP, K

def cl(preset):
    return f"if({K}.setClouds){K}.setClouds('{preset}');"

CYCLE = f"{K}.cycleCam();"

SCENES = {}
PRESETS = ['clear', 'scattered', 'monsoon']
TODS = ['day', 'sunset', 'night']

# setClouds must be called AFTER start() (fly() calls start(), and setTOD inside start may
# re-pick the preset): put it as its own step after fly(), not folded into fly().
for preset in PRESETS:
    for tod in TODS:
        base = f'{preset}_{tod}'
        SCENES[f'{base}_final_chase'] = [fly('cessna', tod, 'final'), cl(preset)]
        SCENES[f'{base}_final_cockpit'] = [fly('cessna', tod, 'final'), cl(preset), CYCLE]
        SCENES[f'{base}_air_chase'] = [fly('cessna', tod, 'runway'), cl(preset), air(2000, 2000, 5500, 320, 95)]
        SCENES[f'{base}_air_cockpit'] = [fly('cessna', tod, 'runway'), cl(preset), air(2000, 2000, 5500, 320, 95), CYCLE]

# Haboob: the preset uses the haboob tod itself, no setClouds call needed
SCENES['haboob_final_chase'] = [fly('cessna', 'haboob', 'final')]
SCENES['haboob_final_cockpit'] = [fly('cessna', 'haboob', 'final'), CYCLE]
SCENES['haboob_wall_chase'] = [fly('cessna', 'haboob', 'runway'), air(3000, 3000, 3071, 150, 95), hbj(4000)]
SCENES['haboob_wall_cockpit'] = [fly('cessna', 'haboob', 'runway'), air(3000, 3000, 3071, 150, 95), hbj(4000), CYCLE]

# Monsoon seen from altitude
SCENES['monsoon_day_high_chase'] = [fly('cessna', 'day', 'runway'), cl('monsoon'), air(-2000, -2000, 9000, 140, 100)]

# Fly-through: place at the cloud base height heading into the field, step 8 s of sim (240 ticks
# at 1/30), then shoot (on the old build this shows polygons cutting the camera; that is the point)
SCENES['scattered_day_through'] = [fly('cessna', 'day', 'runway'), cl('scattered'), air(0, 0, 6200, 0, 100),
    f"for(let i=0;i<240;i++){K}.stepFrame(1/30,false,true);{K}.stepFrame(0,true);"]

# Hand our scenes to graphics_shots' own setup()/SETTLE (2500 ms), which it reads from its module
# globals at call time, and reuse its setClouds(null) reset convention between scenes.
GS.SCENES = SCENES
setup = GS.setup

async def main():
    root, out = os.path.abspath(sys.argv[1]), sys.argv[2]
    os.makedirs(out, exist_ok=True)
    T0 = time.time()
    async with async_playwright() as p:
        b = await launch(p)
        ctx, pg = await open_page(b, serve(root))
        only = sys.argv[3].split(',') if len(sys.argv) > 3 else None
        for name in SCENES:
            if only and name not in only: continue
            t = time.time()
            try:
                await setup(pg, name)
                await pg.screenshot(path=os.path.join(out, name + '.png'))
                await pg.evaluate(f"()=>{{if({K}.setClouds){K}.setClouds(null);}}")
                info = await pg.evaluate(f"()=>({{scr:{K}.curScr(),run:{K}.running(),cam:{K}.camMode()}})")
                print(f'{name}.png  {time.time()-t:.1f}s  {json.dumps(info)}')
            except Exception as e:
                print(f'{name}.png  FAILED  {str(e).splitlines()[0]}'); pg.errs.append(f'{name}: {e}')
        heap = await pg.evaluate("()=>performance.memory?Math.round(performance.memory.usedJSHeapSize/1048576*10)/10:null")
        errs = list(pg.errs)
        await ctx.close(); await b.close()
    n = len(only) if only else len(SCENES)
    json.dump({'heapMB': heap, 'errors': errs}, open(os.path.join(out, 'metrics.json'), 'w'), indent=1)
    print(f'weather_shots: {n} shots to {out} in {time.time()-T0:.0f}s, heapMB {heap}, {len(errs)} page errors')
    for e in errs: print('  error:', e)

if __name__ == "__main__":
    asyncio.run(main())
