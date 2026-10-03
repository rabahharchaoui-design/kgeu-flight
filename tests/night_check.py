# Item 3.2 part 1: airport lighting layer, night clouds.
# Sets night at Luke and Glendale on a 3 mile final and checks the AirportLights
# layers (one THREE.Points per field), that the old lightGlow dome layer is gone,
# that uLights follows the time of day, and that clouds are not the day grey at night.
# Part 2: aircraft exterior lights (one Points per airframe, child of the model group),
# the automatic landing lights (AGL < 1000 ft or on the ground) and the ground light pool.
# Usage: .venv/bin/python tests/night_check.py
import asyncio, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, IPHONE_15, Checks

DAY_CLOUD = (0xffffff, 0x6f7780)
AC_COUNT = {'cessna': 10, 'alpha': 8, 'f16': 13, 'reaper': 9, 'mq9b': 9, 'c130': 20}   # incl. the 2 wingtip glows (3.11)
# put the aircraft `agl` metres above the ground where it is, then run one frame
AT_AGL = """(agl)=>{const K=window.__kgeu,s=K.state();s.pos.y=K.groundHeight(s.pos.x,s.pos.z)+1.5+agl;
  K.snapCam();K.stepFrame(1/60);return window.__kgeu.acLights();}"""


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
        # --- aircraft lights ---
        c('acLights hook', await pg.evaluate("()=>typeof window.__kgeu.acLights==='function'"))
        for typ, n in AC_COUNT.items():
            await pg.evaluate("(t)=>{const K=window.__kgeu;K.setTOD('night');K.pick(t);K.pickBase('kgeu');K.start('runway');}", typ)
            await pg.wait_for_timeout(300)
            await pg.evaluate("()=>{const K=window.__kgeu;K.snapCam();K.stepFrame(1/60);}")
            A = await pg.evaluate("()=>window.__kgeu.acLights()")
            c(f'{typ}: light layer in the aircraft group, {n} lights', A['inGroup'] and A['count'] == n, A)
            c(f'{typ}: on the runway at rest, landing lights on', A['landingOn'], A)
            c(f'{typ}: light pool at night', A['poolOpacity'] > 0, A)
            await pg.evaluate("()=>{const K=window.__kgeu;K.setTOD('day');K.stepFrame(1/60);}")
            A = await pg.evaluate("()=>window.__kgeu.acLights()")
            c(f'{typ}: no light pool by day', A['poolOpacity'] == 0, A)
            await pg.evaluate("()=>window.__kgeu.stepFrame(0,true)")
        c('traffic: nav/strobe lights on the banner tow and every AI aircraft (6 to 10 of them)',
          7 <= len(A['traffic']) <= 11 and all(x > 0 for x in A['traffic']), A['traffic'])
        for base, typ in [('kgeu', 'cessna'), ('luke', 'c130')]:
            await pg.evaluate("([t,b])=>{const K=window.__kgeu;K.setTOD('night');K.pick(t);K.pickBase(b);K.start('final');}", [typ, base])
            await pg.wait_for_timeout(300)
            A = await pg.evaluate(AT_AGL, 2000 / 3.28084)
            c(f'{base} {typ}: 2000 ft AGL on final, landing lights off', not A['landingOn'] and A['poolOpacity'] == 0, A)
            A = await pg.evaluate(AT_AGL, 300 / 3.28084)
            c(f'{base} {typ}: 300 ft AGL on final, landing lights on', A['landingOn'], A)
            A = await pg.evaluate(AT_AGL, 20)
            c(f'{base} {typ}: 65 ft AGL, light pool on the ground', A['poolOpacity'] > 0, A)
            await pg.evaluate("()=>window.__kgeu.stepFrame(0,true)")
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
