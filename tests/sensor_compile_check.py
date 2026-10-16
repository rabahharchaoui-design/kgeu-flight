# sensor item 8: no shader compiles in the sensor view (the gfxfix rule). On the real rAF loop after the warm-up, on
# the given tier: fly the MQ-9A, MQ-9B (day, then night) and the A-10 gun run; in each enter the sensor view, step
# every mode (DTV, NIR, IR WHT, IR BLK; NIR at night goes through the IR pass) at WFOV, NFOV and UNFOV EZ 4X, look aft
# into the airframe and straight down, track, lase, declutter, and leave; the program count (__kgeu.progN().compiles)
# must not move from the first flight frame to the last.
# Usage: .venv/bin/python tests/sensor_compile_check.py [--tier medium|high]
import asyncio, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, IPHONE_15, Checks

K = 'window.__kgeu'
TIER = sys.argv[sys.argv.index('--tier') + 1] if '--tier' in sys.argv else 'medium'
WORK = """async()=>{const K=window.__kgeu,w=ms=>new Promise(r=>setTimeout(r,ms));
  while(K.camMode()!==2)K.cycleCam();await w(700);
  for(const m of ['tv','nir','irw','irb']){K.setSensorMode(m);for(const z of [0,4,7]){K.SENSOR.zoom=z;await w(450);}}
  K.SENSOR.zoom=0;K.setSensorMode('tv');K.SENSOR.az=Math.PI;K.SENSOR.el=0;await w(500);K.SENSOR.az=0;K.SENSOR.el=-1.5;await w(500);
  K.setSensorMode('irw');K.SENSOR.az=Math.PI;K.SENSOR.el=0.2;await w(500);K.setSensorMode('tv');
  K.SENSOR.el=-0.6;K.SENSOR.az=0.5;await w(300);K.trackHere();K.sensorLase();K.sensorDclt();await w(500);K.sensorDclt();K.sensorDclt();await w(300);
  K.cycleCam();await w(600);return true;}"""


async def main():
    c = Checks(); srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3', 'kgeuTier': TIER})
        await pg.wait_for_function(f"()=>{K}.boot().pre&&{K}.warm()", timeout=120000)
        for name, js in (('MQ-9A day', f"()=>{{{K}.setTOD('day');{K}.pick('reaper');{K}.pickBase('luke');{K}.start('final');}}"),
                         ('MQ-9B night', f"()=>{{{K}.setTOD('night');{K}.pick('mq9b');{K}.pickBase('luke');{K}.start('final');}}"),
                         ('A-10 gun run', f"()=>{{{K}.setTOD('day');{K}.mission('gunrun');}}"),
                         ('MQ-9A strike, haboob', f"()=>{{{K}.setTOD('haboob');{K}.pick('reaper');{K}.mission('range');}}")):
            await pg.evaluate(js); await pg.wait_for_timeout(2500)
            n0 = (await pg.evaluate(f"()=>{K}.progN()"))['compiles']
            await pg.evaluate(WORK)
            n1 = (await pg.evaluate(f"()=>{K}.progN()"))['compiles']
            c(f'{TIER} {name}: no program compiled in the sensor view (every mode, zoom, aft, down, track, lase, declutter)', n1 == n0, f'{n0} -> {n1}')
        if pg.errs: c('no console errors', False, pg.errs[:3])
        await b.close()
    srv.shutdown(); c.done('sensor_compile_check')

asyncio.run(main())
