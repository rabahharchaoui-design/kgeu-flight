# Weather item 3 screenshots: how each weather type looks, iPhone landscape 844x390 at 2x.
#   .venv/bin/python tests/weather_type_shots.py <root> <outdir> [scene,scene,...]
# Scenes <type>_<tod>_<view>: the eight WX types (clear, scattered, overcast, rain, storm, fog, gusty, haboob) by day,
# sunset and night, the Cessna on 3 mile final to KGEU in the chase and the cockpit views; plus rain_day_runway_chase
# (parked on the runway in the rain), rain_night_final_chase (the wet runway's lights), fog_night_final_chase,
# fog_day_above (2,000 ft over the fog), storm_day_flash_chase (a held lightning flash), storm_sunset_air_chase (the
# cells over the approach), overcast_day_above (about 5,000 ft above the field, over the deck), gusty_day_runway_chase.
# Uses the setWX, setClouds, wxFlash hooks; graphics_shots' page helpers and setup(). <outdir>/metrics.json: errors.
import asyncio, json, os, sys, time
from playwright.async_api import async_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import graphics_shots as GS
from graphics_shots import serve, launch, open_page, fly, air, K

CYCLE = f"{K}.cycleCam();"
TYPES = ['clear', 'scattered', 'overcast', 'rain', 'storm', 'fog', 'gusty', 'haboob']
TODS = ['day', 'sunset', 'night']

# the weather after start() (fly() sets the time and holds scattered by day: setClouds(null) hands the clouds back
# to the weather); a step of 1.2 s lets the rain, the deck and the fog settle round the camera
def wx(t):
    return f"{K}.setWX('{t}');{K}.setClouds(null);"

SCENES = {}
for t in TYPES:
    for tod in TODS:
        SCENES[f'{t}_{tod}_final_chase'] = [fly('cessna', tod, 'final'), wx(t), 1200]
        SCENES[f'{t}_{tod}_final_cockpit'] = [fly('cessna', tod, 'final'), wx(t), CYCLE, 1200]
SCENES['rain_day_runway_chase'] = [fly('cessna', 'day', 'runway'), wx('rain'), 1200]
SCENES['rain_day_runway_cockpit'] = [fly('cessna', 'day', 'runway'), wx('rain'), CYCLE, 1200]
SCENES['rain_night_final_chase'] = [fly('cessna', 'night', 'final1'), wx('rain'), 1200]
SCENES['fog_night_final_chase'] = [fly('cessna', 'night', 'final1'), wx('fog'), 1200]
SCENES['fog_day_above'] = [fly('cessna', 'day', 'runway'), wx('fog'), air(-3000, 5000, 3071, 30, 95), 1200]
SCENES['storm_day_flash_chase'] = [fly('cessna', 'day', 'final'), wx('storm'), 1200, f"{K}.wxFlash(true);", 600]
SCENES['storm_sunset_air_chase'] = [fly('cessna', 'sunset', 'runway'), wx('storm'), air(2000, -6000, 4500, 190, 100), 1200]
SCENES['overcast_day_above'] = [fly('cessna', 'day', 'runway'), wx('overcast'), air(2000, 2000, 6071, 140, 100), 1200]
SCENES['gusty_day_runway_chase'] = [fly('cessna', 'day', 'runway'), wx('gusty'), 1200]

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
                info = await pg.evaluate(f"()=>{{const w={K}.wx();{K}.wxFlash(false);{K}.setWX('scattered');{K}.setClouds(null);return {{cam:{K}.camMode(),id:w.id,preset:w.preset,vis:Math.round(w.vis),rain:w.rain.n,wet:w.wet,flash:w.flash.n}};}}")
                print(f'{name}.png  {time.time()-t:.1f}s  {json.dumps(info)}')
            except Exception as e:
                print(f'{name}.png  FAILED  {str(e).splitlines()[0]}'); pg.errs.append(f'{name}: {e}')
        errs = list(pg.errs)
        await ctx.close(); await b.close()
    n = len(only) if only else len(SCENES)
    json.dump({'errors': errs}, open(os.path.join(out, 'metrics.json'), 'w'), indent=1)
    print(f'weather_type_shots: {n} shots to {out} in {time.time()-T0:.0f}s, {len(errs)} page errors')
    for e in errs: print('  error:', e)

if __name__ == "__main__":
    asyncio.run(main())
