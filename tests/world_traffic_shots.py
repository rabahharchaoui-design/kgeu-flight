# Throwaway screenshots for the new AI traffic system (TFC). iPhone 15 landscape
# (844x390, device scale 2), Hard mode. Places the player near a spawned traffic
# aircraft by editing K.state() directly (pos/quat/vel), then uses the normal
# chase camera (camMode 0, the default) so the view looks like ordinary flight.
#
# Heading convention used throughout the game: for a compass heading h (degrees),
# forward = (sin(h), -cos(h)) in (x,z); tfcList() already returns hdg in that
# same compass-degrees form. PLACE() below inverts that to point the player at
# the target and offsets it "behind" and "to the side" in the target's own frame.
#
# Usage: .venv/bin/python tests/world_traffic_shots.py
import asyncio, os
from playwright.async_api import async_playwright
from harness import serve, launch, page, IPHONE_15

OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'overnight-screenshots', 'world', 'traffic'))

# place the player `behind` metres behind the target along its own heading, `side`
# metres to the target's right, `up` metres above it, nose pointed at the target.
PLACE = """([tid,behind,side,up])=>{
  const K=window.__kgeu,tgt=K.tfcList().find(o=>o.id===tid);
  if(!tgt)return null;
  const h=tgt.hdg*Math.PI/180;
  const fx=Math.sin(h),fz=-Math.cos(h),rx=Math.sin(h+Math.PI/2),rz=-Math.cos(h+Math.PI/2);
  const px=tgt.x-fx*behind+rx*side,pz=tgt.z-fz*behind+rz*side,py=tgt.y+up;
  const st=K.state();
  st.pos.set(px,py,pz);
  const dx=tgt.x-px,dz=tgt.z-pz,hh=Math.atan2(dx,-dz);
  st.quat.setFromEuler(new THREE.Euler(0,-hh,0,'YXZ'));
  st.vel.set(0,0,0);st.onGround=false;st.crashed=false;st.airTime=30;st.gearDown=false;st.gearPos=0;st.throttle=st.power=0.5;
  K.snapCam();
  return {px:px,py:py,pz:pz,tgt:tgt};
}"""

# look straight down at a world point from `up` metres above it (for the overhead fallback shot)
LOOK_DOWN = """([x,y,z,up])=>{
  const K=window.__kgeu,st=K.state();
  st.pos.set(x,y+up,z);
  st.quat.setFromEuler(new THREE.Euler(-Math.PI/2,0,0,'YXZ'));
  st.vel.set(0,0,0);st.onGround=false;st.crashed=false;st.airTime=30;st.gearDown=false;st.gearPos=0;st.throttle=st.power=0.3;
  K.snapCam();
}"""


async def setup_flight(pg, ac='cessna', base='kgeu', mode='final'):
    await pg.evaluate("([t,b,m])=>{const K=window.__kgeu;K.pick(t);K.pickBase(b);K.start(m);}", [ac, base, mode])
    await pg.wait_for_timeout(100)


async def settle(pg, n=4):
    await pg.evaluate("(n)=>{const K=window.__kgeu;for(let i=0;i<n;i++)K.stepFrame(1/60);}", n)


async def shot(pg, name):
    path = os.path.join(OUT, name)
    await pg.screenshot(path=path, timeout=120000)
    print('  wrote', path)


async def main():
    os.makedirs(OUT, exist_ok=True)
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'})

        # a: airliner on a 1500 m final, day, player placed to fill a good chunk of frame
        await setup_flight(pg, 'cessna', 'kgeu', 'final')
        await pg.evaluate("()=>window.__kgeu.tfcClear()")
        aid = await pg.evaluate("()=>window.__kgeu.tfcSpawn('airliner',{state:'final',dist:1500})")
        await pg.evaluate(PLACE, [aid, 55, 22, 6])
        await settle(pg)
        await shot(pg, 'airliner_final_day.png')

        # b: same, at night, close enough to see nav lights and the strobe
        await pg.evaluate("()=>window.__kgeu.setTOD('night')")
        await pg.evaluate("()=>window.__kgeu.tfcClear()")
        aid = await pg.evaluate("()=>window.__kgeu.tfcSpawn('airliner',{state:'final',dist:1500})")
        await pg.evaluate(PLACE, [aid, 45, 18, 5])
        await settle(pg)
        await shot(pg, 'airliner_night_lights.png')
        await pg.evaluate("()=>window.__kgeu.setTOD('day')")

        # c: helicopter close up, day
        await pg.evaluate("()=>window.__kgeu.tfcClear()")
        hid = await pg.evaluate("()=>window.__kgeu.tfcSpawn('heli',{})")
        await pg.evaluate(PLACE, [hid, 10, 4, 1.5])
        await settle(pg)
        await shot(pg, 'heli_day.png')

        # d: F-16 spawned at 'initial', player alongside
        await pg.evaluate("()=>window.__kgeu.tfcClear()")
        fid = await pg.evaluate("()=>window.__kgeu.tfcSpawn('f16',{state:'initial'})")
        await pg.evaluate(PLACE, [fid, 18, 8, 3])
        await settle(pg)
        await shot(pg, 'f16_break_luke.png')

        # e: normal flight view over Glendale with the mini map showing several traffic dots,
        # after 60 simulated seconds. Populate with the player parked at the KGEU ramp (the
        # proven method from traffic_check.py), then place the player in a normal airborne
        # flight pose over the field for the actual shot.
        await setup_flight(pg, 'cessna', 'kgeu', 'ramp')
        await pg.evaluate("()=>{window.__kgeu.TFC.auto=true;}")
        n_alive = await pg.evaluate(
            "()=>{const K=window.__kgeu;for(let i=0;i<600;i++)K.stepFrame(0.1,false,true);return K.tfcList().length}")
        # natural population puts most traffic near the other fields (Luke, Sky Harbor); force a
        # few cessnas into the Glendale pattern too so the minimap has several dots close by
        await pg.evaluate(
            "()=>{const K=window.__kgeu;['upwind','crosswind','downwind','base'].forEach(s=>K.tfcSpawn('cessna',{state:s}));}")
        n_alive = await pg.evaluate("()=>window.__kgeu.tfcList().length")
        st0 = await pg.evaluate("()=>{const K=window.__kgeu,s=K.state();return [s.pos.x,s.pos.y,s.pos.z]}")
        await pg.evaluate(
            "([x,y,z])=>{const K=window.__kgeu,st=K.state();st.pos.set(x,y+350,z);"
            "st.quat.setFromEuler(new THREE.Euler(-0.05,0,0,'YXZ'));st.vel.set(0,-2,-45);"
            "st.onGround=false;st.crashed=false;st.gearDown=false;st.gearPos=0;st.throttle=st.power=0.5;K.snapCam();}",
            st0)
        await settle(pg)
        await shot(pg, 'minimap_traffic.png')
        print(f'  traffic entries alive at (e): {n_alive}')

        # f: full map open, showing traffic
        await pg.evaluate("()=>window.__kgeu.fmOpen()")
        await pg.evaluate("()=>{const K=window.__kgeu;let n=0;do{K.fmFlush();}while(n++<3);}")
        await pg.wait_for_timeout(200)
        await shot(pg, 'fullmap_traffic.png')
        await pg.evaluate("()=>window.__kgeu.fmClose()")

        # g: airliner just after touchdown at Sky Harbor, from the air 300 m up looking down
        await setup_flight(pg, 'cessna', 'kgeu', 'final')
        await pg.evaluate("()=>window.__kgeu.tfcClear()")
        lid = await pg.evaluate("()=>window.__kgeu.tfcSpawn('airliner',{state:'final',end:0,dist:9000})")
        land = await pg.evaluate(
            "(id)=>{const K=window.__kgeu;for(let i=0;i<3000;i++){K.TFC.update(0.1);"
            "const o=K.tfcList().find(q=>q.id===id);if(!o)return null;if(o.state==='rollout'&&o.onGround)return o;}return null;}",
            lid)
        if land:
            await pg.evaluate(LOOK_DOWN, [land['x'], land['y'], land['z'], 300])
            await settle(pg)
        else:
            print('  WARNING: airliner never reached rollout, shooting final state instead')
            await settle(pg)
        await shot(pg, 'airliner_rollout_phx.png')

        if pg.errs:
            print('console errors:', pg.errs[:5])
        await pg.context.close()
        await b.close()
    srv.shutdown()


asyncio.run(main())
