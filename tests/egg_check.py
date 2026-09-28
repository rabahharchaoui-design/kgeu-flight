# @OhRabah easter eggs (3.10): five civilian placements with the YouTube mark and "@OhRabah".
# Checks all five exist, none at Luke, each where it belongs (hangar row, stadium lot,
# downtown rooftop, assault strip, a tow plane circling Glendale with its banner behind),
# that the tow plane moves and stays in its box over 30 s, and that the billboard and
# rooftop sign are dark by day and lit at night.
# Also writes screenshots to overnight-screenshots/eggs/.
# Run: .venv/bin/python tests/egg_check.py [--noshots]
import asyncio, math, os, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, IPHONE_15
ok = Checks()
SHOTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'overnight-screenshots', 'eggs')
K = 'window.__kgeu'
SHOT = '--noshots' not in sys.argv
NAMES = ['egg_hangar', 'egg_billboard', 'egg_rooftop', 'egg_flag', 'egg_tow']
# free camera from world coordinates: freeCam takes offsets in the aircraft frame
CAMW = """([p,t,fov])=>{const K=window.__kgeu,s=K.state(),qi=s.quat.clone().invert();
  const P=new THREE.Vector3(p[0],p[1],p[2]).sub(s.pos).applyQuaternion(qi),T=new THREE.Vector3(t[0],t[1],t[2]).sub(s.pos).applyQuaternion(qi);
  K.freeCam({p:P.toArray(),t:T.toArray(),fov:fov});}"""
# park the aircraft 400 m over a point, level, flying north at cruise, so it stays out of the shot
PARK = """([x,y,z])=>{const K=window.__kgeu,s=K.state();s.pos.set(x,y+400,z);s.vel.set(0,0,-55);s.quat.set(0,0,0,1);s.w.set(0,0,0);
  s.onGround=false;s.airTime=30;s.throttle=s.power=1;s.gearDown=false;s.gearPos=0;K.snapCam();}"""

async def main():
    os.makedirs(SHOTS, exist_ok=True)
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'})
        ev = lambda js: pg.evaluate("()=>{" + js + "}")
        async def frames(n, render=False):
            await pg.evaluate("([n,r])=>{for(let i=0;i<n;i++)window.__kgeu.stepFrame(1/60,false,!(r&&i==n-1));}", [n, render])
        async def eggs(): return {e['name']: e for e in await pg.evaluate(f"()=>{K}.eggs()")}
        async def shot(name, cam, target, fov, settle=2):
            await pg.evaluate(PARK, cam)
            await pg.evaluate(CAMW, [cam, target, fov])
            await frames(settle, True)
            await pg.evaluate(CAMW, [cam, target, fov])   # the aircraft moved a little during settle
            await frames(1, True)
            await pg.screenshot(path=f'{SHOTS}/{name}.png')
            await ev(f"{K}.freeCam(null)")
        await ev(f"{K}.setSkill('pilot')")
        await ev(f"{K}.setTOD('day')")
        await ev(f"{K}.pick('cessna');{K}.pickBase('kgeu');{K}.start('runway')")
        await pg.wait_for_timeout(800); await frames(3)
        E = await eggs()
        ok('all five placements exist', all(n in E for n in NAMES), list(E))
        luke = await pg.evaluate(f"()=>{K}.eggs().map(e=>{{const L={K}.lukeUV(e.x,e.z),B=e.banner?{K}.lukeUV(e.banner.x,e.banner.z):[1e9,1e9];return [e.name,L,B];}})")
        # Luke field: both runways (about 3 km long, 305 m apart) and the ramp out to v=700, with margin
        inside = lambda L: abs(L[0]) < 2200 and -900 < L[1] < 1400
        ok('nothing inside the Luke field bounds', not any(inside(l[1]) or inside(l[2]) for l in luke), luke)
        hx, hz = await pg.evaluate(f"()=>[{K}.wX(770,-415),{K}.wZ(770,-415)]")
        h = E['egg_hangar']
        ok('hangar banner within 100 m of the hangar row', math.hypot(h['x'] - hx, h['z'] - hz) < 100, (h['x'], h['z']))
        bb = E['egg_billboard']
        ok('billboard within 700 m of the stadium', math.hypot(bb['x'] - 3480, bb['z'] + 979) < 700, (bb['x'], bb['z']))
        rt = E['egg_rooftop']
        ok('rooftop sign above 100 m, downtown', rt['y'] > 100 and math.hypot(rt['x'] - 21000, rt['z'] - 7800) < 1200, (rt['x'], rt['y'], rt['z']))
        lz = await pg.evaluate(f"()=>{K}.LZ")
        fl = E['egg_flag']
        fd = math.hypot(fl['x'] - lz['x'], fl['z'] - lz['z'])
        foff = abs((await pg.evaluate(f"([x,z])=>{K}.lzUV(x,z)", [fl['x'], fl['z']]))[1])
        ok('flag within 60 m of the LZ centre, 40 m off the centreline', fd < 60 and foff > 35, (round(fd, 1), round(foff, 1)))
        ok('day: billboard and rooftop not lit', not bb['lit'] and not rt['lit'], (bb['lit'], rt['lit']))
        gx, gz = await pg.evaluate(f"()=>[{K}.wX(1090,0),{K}.wZ(1090,0)]")
        t0 = E['egg_tow']
        worst = {'dist': 0, 'ymin': 1e9, 'ymax': 0, 'behind': 1e9}
        for i in range(30):
            await frames(60)
            t = (await eggs())['egg_tow']
            bn, f = t['banner'], t['fwd']
            worst['dist'] = max(worst['dist'], math.hypot(t['x'] - gx, t['z'] - gz), math.hypot(bn['x'] - gx, bn['z'] - gz))
            worst['ymin'] = min(worst['ymin'], t['y'], bn['y']); worst['ymax'] = max(worst['ymax'], t['y'], bn['y'])
            # distance of the banner behind the plane along its heading
            worst['behind'] = min(worst['behind'], -((bn['x'] - t['x']) * f[0] + (bn['z'] - t['z']) * f[2]))
        moved = math.hypot(t['x'] - t0['x'], t['z'] - t0['z']), math.hypot(t['banner']['x'] - t0['banner']['x'], t['banner']['z'] - t0['banner']['z'])
        ok('tow plane and banner move over 30 s', moved[0] > 400 and moved[1] > 400, moved)
        ok('tow stays within 6 km of Glendale, 300 to 700 m up', worst['dist'] < 6000 and worst['ymin'] > 300 and worst['ymax'] < 700, worst)
        ok('banner stays behind the plane (40 m or more)', worst['behind'] > 40, worst['behind'])
        if SHOT:
            E = await eggs()
            n = (math.cos(math.radians(26)), math.sin(math.radians(26)))       # +v: the hangar door side
            h = E['egg_hangar']
            await shot('hangar_day', [h['x'] + n[0] * 42, 5, h['z'] + n[1] * 42], [h['x'], 7.5, h['z']], 40)
            bb = E['egg_billboard']
            BCAM = [bb['x'] - 60, bb['y'] + 12, bb['z'] + 14]; BT = [bb['x'], bb['y'] + 10.5, bb['z']]
            await shot('billboard_day', BCAM, BT, 36)
            fl = E['egg_flag']
            await shot('flag_day', [fl['x'], fl['y'] + 5, fl['z']], [fl['x'], fl['y'] + 5, fl['z'] + 1], 50, 4)   # settle turns it downwind
            ry = (await eggs())['egg_flag']['ry']
            dw = (math.cos(ry), -math.sin(ry)); nm = (math.sin(ry), math.cos(ry))       # downwind, cloth normal
            c = [fl['x'] + dw[0] * 1.5, fl['y'] + 5.1, fl['z'] + dw[1] * 1.5]
            await shot('flag_day', [c[0] + nm[0] * 15, c[1] + 0.3, c[2] + nm[1] * 15], [c[0], c[1] + 0.9, c[2]], 34)
            t = (await eggs())['egg_tow']; bn, f = t['banner'], t['fwd']
            m = [(t['x'] + bn['x']) / 2, (t['y'] + bn['y']) / 2, (t['z'] + bn['z']) / 2]
            sd = (-f[2], f[0])
            await pg.evaluate(PARK, [m[0], m[1] + 400, m[2]])
            await pg.evaluate(CAMW, [[m[0] + sd[0] * 85, m[1] + 4, m[2] + sd[1] * 85], m, 32])
            await frames(1, True)
            await pg.screenshot(path=f'{SHOTS}/tow_day.png')
            await ev(f"{K}.freeCam(null)")
        await ev(f"{K}.setTOD('night')"); await frames(2)
        E = await eggs()
        ok('night: billboard and rooftop lit', E['egg_billboard']['lit'] and E['egg_rooftop']['lit'])
        L = await pg.evaluate(f"()=>{K}.lights().layers")
        ok('night: the sign floodlights are on', any(l['name'] == 'airportLights_EGG' and l['visible'] for l in L), L)
        if SHOT:
            bb = E['egg_billboard']
            await shot('billboard_night', [bb['x'] - 60, bb['y'] + 12, bb['z'] + 14], [bb['x'], bb['y'] + 10.5, bb['z']], 36)
            rt = E['egg_rooftop']
            await shot('rooftop_night', [rt['x'] - 110, rt['y'] + 14, rt['z'] + 25], [rt['x'], rt['y'] + 5.5, rt['z']], 32)
        await ev(f"{K}.setTOD('sunset')"); await frames(2)
        E = await eggs()
        ok('sunset: signs lit (dimly)', E['egg_billboard']['lit'])
        await ev(f"{K}.setTOD('day')"); await frames(2)
        E = await eggs()
        ok('day again: signs off', not E['egg_billboard']['lit'] and not E['egg_rooftop']['lit'])
        await pg.evaluate("()=>window.__kgeu.stepFrame(0,true)")
        ok('no page errors', not pg.errs, pg.errs[:3])
        await b.close()
    srv.shutdown()
    return ok.done('egg_check')

sys.exit(asyncio.run(main()))
