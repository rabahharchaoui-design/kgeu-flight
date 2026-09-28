# Item 3.2 part 1: airport lighting layer, night clouds.
# Sets night at Luke and Glendale on a 3 mile final and checks the AirportLights
# layers (one THREE.Points per field), that the old lightGlow dome layer is gone,
# that uLights follows the time of day, and that clouds are not the day grey at night.
# Usage: .venv/bin/python tests/night_check.py
import asyncio, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, IPHONE_15, Checks

DAY_CLOUD = (0xffffff, 0x6f7780)


async def main():
    c = Checks()
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'})
        c('lights hook', await pg.evaluate("()=>typeof window.__kgeu.lights==='function'"))
        c('cloudMat hook', await pg.evaluate("()=>typeof window.__kgeu.cloudMat==='function'"))
        for base, typ, key, need in [('luke', 'c130', 'KLUF', 200), ('kgeu', 'cessna', 'KGEU', 100)]:
            await pg.evaluate("([t,b])=>{const K=window.__kgeu;K.setTOD('night');K.pick(t);K.pickBase(b);K.start('final');}", [typ, base])
            await pg.wait_for_timeout(1500)
            L = await pg.evaluate("()=>window.__kgeu.lights()")
            c(f'{base}: {key} layer has > {need} points', L[key] > need, L[key])
            c(f'{base}: all light layers in the scene and visible at night',
              all(l['inScene'] and l['visible'] for l in L['layers']), L['layers'])
            c(f'{base}: uLights is 1 at night', abs(L['uLights'] - 1) < 1e-6, L['uLights'])
            c(f'{base}: no old glow dome layer', L['oldGlow'] == 0 and not L['hasGLOWS'], (L['oldGlow'], L['hasGLOWS']))
            cm = await pg.evaluate("()=>window.__kgeu.cloudMat()")
            c(f'{base}: night cloud colour is not the day grey',
              cm['emissive'] != DAY_CLOUD[1] and cm['color'] != DAY_CLOUD[0], {k: hex(v) for k, v in cm.items()})
        await pg.evaluate("()=>window.__kgeu.setTOD('day')")
        L = await pg.evaluate("()=>window.__kgeu.lights()")
        c('day: uLights is 0', L['uLights'] == 0, L['uLights'])
        c('day: light layers hidden', not any(l['visible'] for l in L['layers']))
        cm = await pg.evaluate("()=>window.__kgeu.cloudMat()")
        c('day: clouds back to day colours', (cm['color'], cm['emissive']) == DAY_CLOUD, {k: hex(v) for k, v in cm.items()})
        await pg.evaluate("()=>window.__kgeu.setTOD('sunset')")
        L = await pg.evaluate("()=>window.__kgeu.lights()")
        c('sunset: uLights dim, between 0 and 1', 0 < L['uLights'] < 1, L['uLights'])
        await pg.evaluate("()=>window.__kgeu.setTOD('day')")
        c('no page errors', not pg.errs, pg.errs[:5])
        await pg.context.close()
        await b.close()
    srv.shutdown()
    return c.done('night_check')


sys.exit(asyncio.run(main()))
