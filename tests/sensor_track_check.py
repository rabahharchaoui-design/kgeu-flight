# sensor item 5: tracking. A point track holds the moving truck on the range (the gate on it); an area track holds its
# ground patch while the truck drives off; a geo stare holds a coordinate as the aircraft orbits and survives the
# airframe masking it (an area track there breaks); a target jumping out of a narrow field of view, a destroyed
# target and a track pulled past 20 km break with the cue; in free flight a freeway car can be point tracked.
# Usage: .venv/bin/python tests/sensor_track_check.py
import asyncio, math
from playwright.async_api import async_playwright
from harness import serve, launch, page, IPHONE_15, Checks

K = 'window.__kgeu'
ADV = "(n)=>{const K=window.__kgeu;for(let i=0;i<n;i++)K.stepFrame(1/30,false,true);K.stepFrame(1/60);return K.sensor();}"
MOVER = "()=>{const K=window.__kgeu;return K.STRIKE.targets.findIndex(t=>t.moving);}"


async def main():
    c = Checks(); srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'})
        await pg.evaluate(f"()=>{{const K={K};K.setTOD('day');K.pick('reaper');K.mission('range');}}")
        await pg.wait_for_timeout(1500)
        mi = await pg.evaluate(MOVER)
        # point track on the mover
        await pg.evaluate(f"(i)=>{{const K={K};K.pointAt(i);K.trackHere();}}", mi)
        s = await pg.evaluate(ADV, 2)
        c('point track on the moving truck', s['kind'] == 'pt', s['kind'])
        p0 = await pg.evaluate(f"(i)=>{{const t={K}.STRIKE.targets[i];return [t.x,t.z];}}", mi)
        s = await pg.evaluate(ADV, 300)
        p1 = await pg.evaluate(f"(i)=>{{const t={K}.STRIKE.targets[i],S={K}.SENSOR;return [t.x,t.z,Math.hypot(S.spot.x-t.x,S.spot.z-t.z)];}}", mi)
        moved = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
        c('10 s on: the truck drove on, the track held, the crosshair on it', s['kind'] == 'pt' and moved > 50 and p1[2] < 12, (s['kind'], round(moved), round(p1[2], 1)))
        g = await pg.evaluate(f"()=>{K}.gate()")
        c('the gate sits on the truck in the picture', g['c'] == 'on pt' and abs(g['x'] - 422) < 20 and abs(g['y'] - 195) < 20, g)
        # area track: the patch stays, the truck leaves it
        await pg.evaluate(f"()=>{{const K={K},S=K.SENSOR;S.tgt=null;S.track=S.spot.clone();window.__a=S.track.clone();}}")
        s = await pg.evaluate(ADV, 300)
        d = await pg.evaluate(f"(i)=>{{const S={K}.SENSOR,t={K}.STRIKE.targets[i];return [Math.hypot(S.spot.x-window.__a.x,S.spot.z-window.__a.z),Math.hypot(t.x-window.__a.x,t.z-window.__a.z)];}}", mi)
        c('area track: the crosshair holds the ground patch as the truck drives away', s['kind'] == 'ar' and d[0] < 3 and d[1] > 60, (s['kind'], [round(v, 1) for v in d]))
        # geo stare: 30 s of orbit
        await pg.evaluate(f"()=>{{const K={K},S=K.SENSOR;S.track=null;S.geo=S.spot.clone();window.__g=S.geo.clone();}}")
        s = await pg.evaluate(ADV, 900)
        d = await pg.evaluate(f"()=>{{const S={K}.SENSOR;return Math.hypot(S.spot.x-window.__g.x,S.spot.z-window.__g.z);}}")
        c('geo stare: the coordinate held through 30 s of orbit', s['kind'] == 'geo' and d < 3, (s['kind'], round(d, 1)))
        # masked: geo survives, an area track breaks (the aircraft turned so the spot is aft and above the belly plane)
        TURN = """()=>{const K=window.__kgeu,s=K.state();const q=s.quat.clone();window.__q1=q;
          const e=new THREE.Euler().setFromQuaternion(q,'YXZ');const S=K.SENSOR,o=K.camPos();
          const brg=Math.atan2(S.spot.x-o[0],-(S.spot.z-o[2]));   // point the nose away from the spot and pitch up hard
          s.quat.setFromEuler(new THREE.Euler(0.9,-(brg+Math.PI),0,'YXZ'));window.__q1=s.quat.clone();window.__p1=s.pos.clone();return true;}"""
        HOLD = "(n)=>{const K=window.__kgeu,s=K.state();for(let i=0;i<n;i++){s.quat.copy(window.__q1);s.pos.copy(window.__p1);s.vel.set(0,0,0);K.stepFrame(1/30,false,true);}return K.sensor();}"
        await pg.evaluate(TURN); s = await pg.evaluate(HOLD, 20)
        c('geo stare masked by the airframe: held, MASK shown', s['kind'] == 'geo' and s['mask'], (s['kind'], s['mask'], s['az'], s['el']))
        await pg.evaluate(f"()=>{{const S={K}.SENSOR;S.geo=null;S.track=S.spot.clone();}}"); s = await pg.evaluate(HOLD, 20)
        c('area track masked by the airframe: lost after 0.3 s with MASK', s['kind'] == '' and s['cue'] == 'MASK', (s['kind'], s['cue']))
        await pg.evaluate("()=>{window.__q1=null;}")
        # restart the range for the rest
        await pg.evaluate(f"()=>{{const K={K};K.mission('range');}}"); await pg.wait_for_timeout(1200)
        mi = await pg.evaluate(MOVER)
        await pg.evaluate(f"(i)=>{{const K={K};K.pointAt(i);K.trackHere();K.SENSOR.zoom=7;}}", mi); s = await pg.evaluate(ADV, 30)
        c('UNFOV EZ 4X point track holds', s['kind'] == 'pt' and s['fov'] < 0.03, (s['kind'], s['fov']))
        await pg.evaluate(f"(i)=>{{const t={K}.STRIKE.targets[i];t.moving=false;t.x+=220;}}", mi); s = await pg.evaluate(ADV, 3)
        c('a target jumping out of the narrow picture faster than the ball can follow: TRK LOST', s['kind'] == '' and s['cue'] == 'TRK LOST', (s['kind'], s['cue']))
        # a destroyed target
        await pg.evaluate(f"()=>{{const K={K};K.SENSOR.zoom=1;const i=K.STRIKE.targets.findIndex(t=>t.kind==='bunker');K.pointAt(i);K.trackHere();}}"); s = await pg.evaluate(ADV, 3)
        await pg.evaluate(f"()=>{{const K={K},t=K.STRIKE.targets.find(t=>t.kind==='bunker');t.dead=true;}}"); s = await pg.evaluate(ADV, 2)
        c('the tracked target destroyed: TRK LOST', s['kind'] == '' and s['cue'] == 'TRK LOST', (s['kind'], s['cue']))
        # past 20 km
        await pg.evaluate(f"()=>{{const K={K},i=K.STRIKE.targets.findIndex(t=>!t.dead&&!t.moving);K.pointAt(i);K.trackHere();}}"); await pg.evaluate(ADV, 2)
        await pg.evaluate(f"()=>{{const K={K},s=K.state(),t=K.SENSOR.tgt;s.pos.x=t.x+21000;s.pos.z=t.z;s.pos.y=4000;K.snapCam();}}"); s = await pg.evaluate(ADV, 3)
        c('a point track pulled past 20 km: lost', s['kind'] == '' and s['cue'] == 'TRK LOST', (s['kind'], s['cue']))
        if pg.errs: c('no console errors (range)', False, pg.errs[:3])
        await pg.close()
        # free flight: a freeway car
        pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'})
        await pg.evaluate(f"()=>{{const K={K};K.setTOD('day');K.pick('mq9b');K.pickBase('kgeu');K.start('final');}}"); await pg.wait_for_timeout(600)
        ok = await pg.evaluate(f"""()=>{{const K={K},s=K.state(),X=K.FWY_X;const x=X+2500,z=-6000,V=75;
          s.pos.set(x,1800,z);s.vel.set(0,0,-V);s.quat.set(0,0,0,1);s.onGround=false;s.airTime=30;s.gearDown=false;s.gearPos=0;s.ap=null;
          K.snapCam();K.stepFrame(1/60,false,true);while(K.camMode()!==2)K.cycleCam();K.stepFrame(1/60,false,true);
          // look at the freeway straight west, find a car near the spot by sliding the look along the road
          const o=K.camPos(),dx=X-o[0],dz=0;let best=null;
          for(let zz=-7500;zz<-4500;zz+=40){{const dy=0.4-o[1],h=Math.hypot(X-o[0],zz-o[2]);K.sensorLook(Math.atan2(X-o[0],-(zz-o[2]))*180/Math.PI,Math.atan2(-dy,h)*180/Math.PI);
            K.trackHere();if(K.SENSOR.tgt){{best=K.SENSOR.tgt.name;break;}}}}
          return best;}}""")
        c('free flight: a freeway car point tracked as Vehicle', ok == 'Vehicle', ok)
        s = await pg.evaluate(ADV, 150)
        d = await pg.evaluate(f"()=>{{const S={K}.SENSOR;return S.tgt?Math.hypot(S.spot.x-S.tgt.x,S.spot.z-S.tgt.z):-1;}}")
        c('... and held for 5 s as it drives (crosshair on it)', s['kind'] == 'pt' and 0 <= d < 10, (s['kind'], d))
        if pg.errs: c('no console errors (free flight)', False, pg.errs[:3])
        await b.close()
    srv.shutdown(); c.done('sensor_track_check')

asyncio.run(main())
