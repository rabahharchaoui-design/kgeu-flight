# sensor item 2/8: screenshots of the ball pointed round the airframe (aft, aft and up, ahead and up, straight down,
# past straight down) on the MQ-9A and MQ-9B, to see the airframe masking and the turret hidden.
# Usage: .venv/bin/python tests/sensor_look_shots.py <outdir> [--type reaper|mq9b] [--tod day]
import asyncio, os, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, IPHONE_15

OUT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith('--') else 'overnight-screenshots/sensor/look')
TYPE = sys.argv[sys.argv.index('--type') + 1] if '--type' in sys.argv else 'reaper'
TOD = sys.argv[sys.argv.index('--tod') + 1] if '--tod' in sys.argv else 'day'
K = 'window.__kgeu'
PLACE = """()=>{const K=window.__kgeu,s=K.state(),L=K.LUKE;const x=L.x-5000,z=L.z+3500,hdg=0.6,V=80;
  s.pos.set(x,2400+K.groundHeight(x,z),z);s.vel.set(Math.sin(hdg)*V,0,-Math.cos(hdg)*V);
  s.quat.setFromEuler(new THREE.Euler(0,-hdg,0,'YXZ'));s.w.set(0,0,0);
  s.onGround=false;s.airTime=30;s.flapIdx=0;s.throttle=s.power=0.7;s.gearDown=false;s.gearPos=0;s.ap=null;
  K.touchIn.active=false;K.snapCam();K.stepFrame(1/60,false,true);
  while(K.camMode()!==2)K.cycleCam();K.stepFrame(1/60,false,true);
  window.__q0=s.quat.clone();window.__p0=s.pos.clone();return K.sensorMode();}"""
LOOK = """([az,el,z])=>{const K=window.__kgeu,S=K.SENSOR,s=K.state();S.tgt=S.track=S.geo=S.slewTo=null;S.rx=S.ry=0;S.zoom=z;
  S.az=az*Math.PI/180;S.el=el*Math.PI/180;
  for(let i=0;i<4;i++){s.quat.copy(window.__q0);s.pos.copy(window.__p0);K.stepFrame(1/60,false,true);}
  s.quat.copy(window.__q0);s.pos.copy(window.__p0);K.stepFrame(1/60);return K.sensor();}"""


async def main():
    os.makedirs(OUT, exist_ok=True)
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'})
        await pg.evaluate(f"()=>{{const K={K};K.setTOD('{TOD}');K.pick('{TYPE}');K.pickBase('luke');K.start('final');}}")
        await pg.wait_for_timeout(600)
        await pg.evaluate(PLACE)
        for name, az, el in [('aft_level', 180, -3), ('aft_up', 150, 12), ('ahead_up', 0, 15), ('abeam_up', 95, 20),
                             ('ahead_down', 0, -30), ('nadir', 0, -90), ('past_nadir', 0, -120), ('aft_down', 180, -40)]:
            s = await pg.evaluate(LOOK, [az, el, 0])
            await pg.wait_for_timeout(200)
            path = os.path.join(OUT, f'{TYPE}_{name}.png')
            await pg.screenshot(path=path, timeout=120000)
            print('  wrote', path, 'mask', s['mask'], 'az', s['az'], 'el', s['el'])
        print('  errors:', pg.errs[:3] if pg.errs else 'none')
        await b.close()
    srv.shutdown()

asyncio.run(main())
