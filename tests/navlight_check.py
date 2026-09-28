# Item 3.11: aircraft nav lights readable at night from the chase camera.
# Cessna and F-16 on the 3 mile final at Glendale, real chase camera, light clock frozen
# (__kgeu.lightClock) between strobe and beacon flashes so the frame is deterministic.
# __kgeu.acLightScreen() gives each light's screen position; the rendered frame is sampled
# around the left tip (red dominant), the right tip (green dominant) and the tail (bright
# white). By day the same spots must not be lit: with the lights shown vs hidden the frame
# changes there by well under the night change (only the low daylight floor).
# Usage: .venv/bin/python tests/navlight_check.py
import asyncio, io, sys
from PIL import Image
from playwright.async_api import async_playwright
from harness import serve, launch, page, IPHONE_15, Checks

R = 7            # sample half-window, CSS px
DPR = 2          # harness device scale factor


def window(img, x, y):
    X, Y = round(x * DPR), round(y * DPR)
    w = R * DPR
    return [img.getpixel((i, j))[:3] for i in range(max(0, X - w), min(img.width, X + w + 1))
            for j in range(max(0, Y - w), min(img.height, Y + w + 1))]


def dominant(px, ch, lo=70):
    # pixels where channel ch is clearly lit and clearly above the other two
    o = [k for k in range(3) if k != ch]
    return sum(1 for p in px if p[ch] > lo and p[ch] > 1.3 * p[o[0]] + 15 and p[ch] > 1.3 * p[o[1]] + 15)


def change(a, b, l, _=False):
    # how much light the aircraft lights add around a spot: summed channel increase, lights on - off
    return sum(max(0, p[k] - q[k]) for p, q in zip(window(a, l['x'], l['y']), window(b, l['x'], l['y'])) for k in range(3))


def white(px):
    return sum(1 for p in px if min(p) > 200)


async def main():
    c = Checks()
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'})
        c('hooks', await pg.evaluate("()=>['lightClock','acLightScreen'].every(h=>typeof window.__kgeu[h]==='function')"))

        async def frame(hide=False):
            # a zero length step: re-render the same instant, so shown / hidden frames differ only by the lights
            await pg.evaluate("(h)=>{const K=window.__kgeu;K.plane().lights.pts.visible=!h;K.stepFrame(0);}", hide)
            return Image.open(io.BytesIO(await pg.screenshot(timeout=120000))).convert('RGB')

        for typ in ['cessna', 'f16']:
            await pg.evaluate("(t)=>{const K=window.__kgeu;K.lightClock(0.6);K.setTOD('night');K.pick(t);K.pickBase('kgeu');K.start('final');}", typ)
            await pg.wait_for_timeout(200)
            await pg.evaluate("()=>{const K=window.__kgeu;while(K.camMode()!==0)K.cycleCam();K.snapCam();for(let i=0;i<60;i++)K.stepFrame(1/60);}")
            img = await frame()
            dark = await frame(hide=True)
            S = await pg.evaluate("()=>window.__kgeu.acLightScreen()")
            left = next(l for l in S if l['kind'] == 'glow' and l['lx'] < 0)
            right = next(l for l in S if l['kind'] == 'glow' and l['lx'] > 0)
            tail = next(l for l in S if l['kind'] == 'tail')
            spots = (('left', left), ('right', right), ('tail', tail))
            c(f'{typ}: wingtips and tail in front of the chase camera, on screen',
              all(l['front'] and 0 < l['x'] < 844 and 0 < l['y'] < 390 for l in (left, right, tail)),
              [(round(l['x']), round(l['y'])) for l in (left, right, tail)])
            nl, nr, nt = dominant(window(img, left['x'], left['y']), 0), dominant(window(img, right['x'], right['y']), 1), white(window(img, tail['x'], tail['y']))
            c(f'{typ} night chase: red cluster on the left tip', nl >= 4, nl)
            c(f'{typ} night chase: green cluster on the right tip', nr >= 4, nr)
            c(f'{typ} night chase: bright white cluster at the tail', nt >= 4, nt)
            c(f'{typ} night chase: no green on the left tip, no red on the right',
              dominant(window(img, left['x'], left['y']), 1) == 0 and dominant(window(img, right['x'], right['y']), 0) == 0)
            night = {nm: change(img, dark, l) for nm, l in spots}
            # day: the steady lights keep only their low daylight floor. Compare the frame with the
            # aircraft lights shown against the one with them hidden at each spot: the change must
            # be well under the night change, and the tips must not read as a red / green light
            await pg.evaluate("()=>{const K=window.__kgeu;K.setTOD('day');K.stepFrame(1/60);}")
            on = await frame()
            off = await frame(hide=True)
            await pg.evaluate("()=>{window.__kgeu.plane().lights.pts.visible=true;}")
            for nm, l in spots:
                d = change(on, off, l, True)
                c(f'{typ} day: {nm} light not lit (summed change {d} vs night {night[nm]})', d < 0.35 * night[nm], (d, night[nm]))
            # (the airframe's own painted lenses may be red / green: count only what the lights add)
            dl = dominant(window(on, left['x'], left['y']), 0, 150) - dominant(window(off, left['x'], left['y']), 0, 150)
            dr = dominant(window(on, right['x'], right['y']), 1, 150) - dominant(window(off, right['x'], right['y']), 1, 150)
            c(f'{typ} day: the lights add no strong red or green cluster at the tips', dl < 4 and dr < 4, (dl, dr))
        await pg.evaluate("()=>{const K=window.__kgeu;K.lightClock(null);K.stepFrame(0,true);}")
        c('no page errors', not pg.errs, pg.errs[:5])
        await pg.context.close()
        await b.close()
    srv.shutdown()
    return c.done('navlight_check')


sys.exit(asyncio.run(main()))
