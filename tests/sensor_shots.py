# Sensor ball screenshots: a Reaper at 15,000 ft about 8 km south-west of Luke, the
# ball locked on the Luke runway centre. Day TV, IR white hot, IR black hot, IR white
# hot at x8, and IR white hot at night, at iPhone landscape (844x390).
# Usage: .venv/bin/python tests/sensor_shots.py
# Writes overnight-screenshots/sensor/{daytv,ir_white,ir_black,ir_white_x8,night_ir_white}.png
import asyncio, os
from playwright.async_api import async_playwright
from harness import serve, launch, page, IPHONE_15

OUT = os.path.abspath('overnight-screenshots/sensor')

# Place the Reaper 8 km SW of the 03L/21R runway centre at 4570 m, heading NW so Luke
# sits off the right wing, enter the ball view (its autopilot takes over), aim the ball
# at the runway centre and lock it.
PLACE = """()=>{const K=window.__kgeu,s=K.state(),L=K.LUKE,sn=Math.sin(L.h),cs=Math.cos(L.h);
  const cx=L.x+(-152.5)*cs,cz=L.z+(-152.5)*sn;window.__rc=[cx,cz];
  const d=8000/Math.SQRT2,x=cx-d,z=cz+d,hdg=-Math.PI/4,V=80;
  s.pos.set(x,4570+K.groundHeight(x,z),z);s.vel.set(Math.sin(hdg)*V,0,-Math.cos(hdg)*V);
  s.quat.setFromEuler(new THREE.Euler(0,-hdg,0,'YXZ'));s.w.set(0,0,0);
  s.onGround=false;s.airTime=30;s.flapIdx=0;s.throttle=s.power=0.7;s.gearDown=false;s.gearPos=0;s.ap=null;
  K.touchIn.active=false;K.touchIn.ail=0;K.touchIn.elev=0;K.snapCam();K.stepFrame(1/60,false,true);
  while(K.camMode()!==2)K.cycleCam();
  K.stepFrame(1/60,false,true);return true;}"""
AIM = """()=>{const K=window.__kgeu,s=K.state(),S=K.SENSOR,[cx,cz]=window.__rc;
  const o=K.camPos(),gy=K.groundHeight(cx,cz),dx=cx-o[0],dy=gy-o[1],dz=cz-o[2],hz=Math.hypot(dx,dz);
  const e=new THREE.Euler().setFromQuaternion(s.quat,'YXZ');
  let az=Math.atan2(dx,-dz)+e.y;az=Math.atan2(Math.sin(az),Math.cos(az));
  S.az=az;S.el=Math.atan2(dy,hz);S.track=null;S.tgt=null;K.stepFrame(1/60,false,true);K.sensorLock();
  for(let i=0;i<60;i++)K.stepFrame(1/60,false,true);return K.sensor();}"""


async def settle(pg, secs):
    # simulate without drawing, then draw one frame for the shot (and clear the toasts)
    await pg.evaluate("(n)=>{const K=window.__kgeu;for(let i=0;i<n;i++)K.stepFrame(1/60,false,true);K.stepFrame(1/60);}", round(secs*60))


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
        for tod, shots in (('day', [('tv', 0, 'daytv.png'), ('irw', 0, 'ir_white.png'), ('irb', 0, 'ir_black.png'), ('irw', 3, 'ir_white_x8.png')]),
                           ('night', [('irw', 0, 'night_ir_white.png')])):
            await pg.evaluate("(t)=>{const K=window.__kgeu;K.setTOD(t);K.pick('reaper');K.pickBase('luke');K.start('final');}", tod)
            await pg.wait_for_timeout(600)
            await pg.evaluate(PLACE)
            info = await pg.evaluate(AIM)
            print(f'  {tod}: sensor', info)
            for mode, zi, name in shots:
                await pg.evaluate("([m,z])=>{const K=window.__kgeu,S=K.SENSOR;K.setSensorMode(m);S.zoom=z;}", [mode, zi])
                await settle(pg, 3.2)
                await shot(pg, name)
        await pg.evaluate("()=>window.__kgeu.stepFrame(0,true)")
        if pg.errs: print('  page errors:', pg.errs[:3])
        await b.close()

asyncio.run(main())
