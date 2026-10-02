# Throwaway screenshot script for item 4.4 (Rio Santos Dumont landmarks). iPhone 15 landscape, chase
# camera, Hard, Cessna. The paris_shots recipe (pinned pose, snapCam every settle frame), absolute heights.
# Usage: .venv/bin/python tests/rio_shots.py
import asyncio, os, math
from playwright.async_api import async_playwright
from harness import serve, launch, page, IPHONE_15

K = 'window.__kgeu'
OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'overnight-screenshots', 'world', 'rio'))
BASE = {'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3', 'kgeuRegion': 'sbrj'}

PLACE = """([cx,cz,brgDeg,dist,y,hdgDeg,n])=>{const K=window.__kgeu,r=brgDeg*Math.PI/180,h=hdgDeg*Math.PI/180;
  const x=cx+dist*Math.sin(r),z=cz-dist*Math.cos(r),s=K.state();
  const pin=()=>{s.pos.set(x,y,z);s.vel.set(Math.sin(h)*55,0,-Math.cos(h)*55);s.quat.setFromEuler(new THREE.Euler(0,-h,0,'YXZ'));if(s.w)s.w.set(0,0,0);
    s.onGround=false;s.crashed=false;s.airTime=30;s.gearDown=false;s.gearPos=0;s.throttle=s.power=0.5;s.flapIdx=0;s.ap=null;};
  pin();K.snapCam();for(let i=0;i<n;i++){pin();K.snapCam();K.stepFrame(1/60);}pin();K.snapCam();return {x,y,z};}"""


async def cam(pg, mode=0):
    await pg.evaluate("(m)=>{let k=0;while(window.__kgeu.camMode()!==m&&k++<5)window.__kgeu.cycleCam();}", mode)


async def shot(pg, name, settle=12):
    if settle:
        await pg.evaluate("(n)=>{const K=window.__kgeu;for(let i=0;i<n;i++)K.stepFrame(1/60);}", settle)
    await pg.screenshot(path=os.path.join(OUT, name), timeout=120000)
    print('  wrote', name)


async def place(pg, c, brg, dist, y, hdg):
    await pg.evaluate(PLACE, [c[0], c[1], brg, dist, y, hdg, 12]); await cam(pg, 0)


async def main():
    os.makedirs(OUT, exist_ok=True)
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp=IPHONE_15, storage=BASE)
        await pg.wait_for_function(f"()=>{K}.WORLD.ready||{K}.WORLD.err", timeout=60000)
        await pg.evaluate(f"()=>{K}.setTOD('day')")
        P = await pg.evaluate("""()=>{const K=window.__kgeu,R=K.RIO,m=R.arc.pts[Math.floor(R.arc.pts.length/2)];
          return {sug:R.lm.sugarloaf,cv:R.cv,cvY:K.groundHeight(...R.cv),hc:R.hc,arc:[m.x,m.z,m.nx,m.nz],bb:[R.bb.x,R.bb.z,K.CITYBB.list[0].hdg],
            rh:K.wframe().rh*180/Math.PI,len:K.wframe().len,mus:R.mus,tw:[R.towers[0].x,R.towers[0].z],fav:[R.lm.cable_base]};}""")
        rh = P['rh']
        for tod in ('day', 'night'):
            await pg.evaluate(f"()=>{K}.setTOD('{tod}')")
            await pg.evaluate("()=>{const K=window.__kgeu;K.pick('cessna');K.pickPos('final');K.start('final');}"); await pg.wait_for_timeout(1500)
            await shot(pg, f'final3_{tod}.png')
            # 3 km past the departure end, 400 m, runway heading
            await place(pg, [0, 0], rh, P['len'] + 3000, 400, rh)
            await shot(pg, f'departure_{tod}.png', 0)
        await pg.evaluate(f"()=>{K}.setTOD('day')")
        # Sugarloaf and Urca from the bay, north east, 2.2 km, 250 m
        await place(pg, P['sug'], 40, 2200, 250, 220)
        await shot(pg, 'sugarloaf_bay.png', 0)
        # the cable car from the west of Urca
        await place(pg, P['sug'], 290, 1500, 330, 110)
        await shot(pg, 'cablecar.png', 0)
        # Christ, 350 m out on the field side, a little over the head
        await place(pg, P['cv'], 45, 350, P['cvY'] + 45, 225)
        await shot(pg, 'christ_close.png', 0)
        # Copacabana from the sea, 1.6 km, 220 m
        a = P['arc']; brg = math.degrees(math.atan2(-a[2], a[3] * -1)) % 360
        brg = math.degrees(math.atan2(-a[2], a[3])) % 360
        await place(pg, a[:2], brg, 1600, 220, (brg + 180) % 360)
        await shot(pg, 'copacabana.png', 0)
        await pg.evaluate(f"()=>{K}.setTOD('night')")
        await place(pg, a[:2], brg, 1600, 220, (brg + 180) % 360)
        await shot(pg, 'copacabana_night.png', 0)
        await place(pg, P['cv'], 45, 2500, P['cvY'] + 100, 225)
        await shot(pg, 'christ_night.png', 0)
        await pg.evaluate(f"()=>{K}.setTOD('day')")
        # the Niteroi bridge's span from the south, 1.5 km, 120 m
        await place(pg, P['hc'], 160, 1500, 120, 340)
        await shot(pg, 'bridge.png', 0)
        # Centro and the Museum of Tomorrow from the bay, 1.5 km east, 200 m
        await place(pg, P['mus'], 70, 1500, 200, 250)
        await shot(pg, 'centro.png', 0)
        # the billboard
        await place(pg, P['bb'][:2], P['bb'][2], 40, 20, rh)
        await shot(pg, 'billboard.png', 0)
        if pg.errs:
            print('  console errors:', pg.errs[:5])
        await b.close()

asyncio.run(main())
