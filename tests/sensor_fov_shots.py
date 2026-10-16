# sensor items 3 and 8: the MQ-9 sensor at every field of view (WFOV to UNFOV EZ 4X) in every mode (DTV, NIR, IR WHT,
# IR BLK), held on a parked target on the strike range (or the Luke runway with --luke), iPhone landscape.
# Usage: [PFS_TIER=medium] .venv/bin/python tests/sensor_fov_shots.py <outdir> [--modes tv,nir,irw,irb] [--zooms 0,1,..]
#        [--type reaper|mq9b] [--tod day|night|haboob] [--size 844x390] [--dclt 0|1|2] [--skill pilot|rookie] [--sheet]
import asyncio, os, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page

def arg(k, d):
    return sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d

OUT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith('--') else 'overnight-screenshots/sensor/fov')
MODES = arg('--modes', 'tv,nir,irw,irb').split(',')
ZOOMS = [int(z) for z in arg('--zooms', '0,1,2,3,4,5,6,7').split(',')]
TYPE = arg('--type', 'reaper'); TOD = arg('--tod', 'day'); W, H = [int(v) for v in arg('--size', '844x390').split('x')]
DCLT = int(arg('--dclt', '0')); SKILL = arg('--skill', 'pilot')
K = 'window.__kgeu'


async def settle(pg, n=30):
    await pg.evaluate("(n)=>{const K=window.__kgeu;for(let i=0;i<n;i++)K.stepFrame(1/60,false,true);K.stepFrame(1/60);}", n)


async def main():
    os.makedirs(OUT, exist_ok=True)
    srv, url = serve()
    st = {'kgeuOnboard': SKILL, 'kgeuTut': '1', 'kgeuCoach': '3'}
    if os.environ.get('PFS_TIER'): st['kgeuTier'] = os.environ['PFS_TIER']
    shots = []
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp={'width': W, 'height': H}, storage=st)
        if H > W: await pg.evaluate("()=>document.body.classList.add('portraitok')")
        await pg.evaluate(f"()=>{{const K={K};K.setTOD('{TOD}');K.pick('{TYPE}');K.mission('range');}}")
        await pg.wait_for_timeout(1500)
        await settle(pg, 60)
        # a parked truck under the crosshair, point tracked
        info = await pg.evaluate(f"""()=>{{const K={K};const i=K.STRIKE.targets.findIndex(t=>t.kind==='truck'&&!t.moving);
          K.pointAt(i);K.trackHere();for(let j=0;j<20;j++)K.stepFrame(1/60,false,true);return K.sensor();}}""")
        print('  sensor:', {k: info.get(k) for k in ('kind', 'az', 'el', 'slant')})
        if DCLT:
            await pg.evaluate(f"(n)=>{{for(let i=0;i<n;i++){K}.sensorDclt&&{K}.sensorDclt();}}", DCLT)
        for m in MODES:
            for z in ZOOMS:
                await pg.evaluate(f"([m,z])=>{{const K={K};K.setSensorMode(m);K.SENSOR.zoom=z;}}", [m, z])
                await settle(pg, 40)
                s = await pg.evaluate(f"()=>{K}.sensor()")
                path = os.path.join(OUT, f'{TYPE}_{TOD}_{m}_z{z}' + (f'_{W}x{H}' if '--size' in sys.argv else '') + (f'_{SKILL}' if SKILL != 'pilot' else '') + (f'_dc{DCLT}' if DCLT else '') + '.png')
                await pg.screenshot(path=path, timeout=120000)
                shots.append(path)
                print(f"  wrote {os.path.basename(path)}  {s['fovName']}  fov {s['fov']}  lock {s['kind']}")
        print('  errors:', pg.errs[:3] if pg.errs else 'none')
        await b.close()
    srv.shutdown()
    if '--sheet' in sys.argv:
        from PIL import Image
        ims = [Image.open(x).resize((W // 2, H // 2)) for x in shots]
        cols = len(ZOOMS); rows = (len(ims) + cols - 1) // cols
        sh = Image.new('RGB', (cols * (W // 2), rows * (H // 2)))
        for i, im in enumerate(ims): sh.paste(im, ((i % cols) * (W // 2), (i // cols) * (H // 2)))
        sp = os.path.join(OUT, f'sheet_{TYPE}_{TOD}.png'); sh.save(sp); print('  sheet', sp)

asyncio.run(main())
