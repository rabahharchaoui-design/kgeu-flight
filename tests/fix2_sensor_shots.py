# fix2 before/after shots: MQ-9A sensor ball at all four zoom levels, Day TV and IR
# white, locked on the Luke runway, at iPhone landscape (844x390). Lifted from
# tests/sensor_shots.py's PLACE/AIM helpers.
# Usage: .venv/bin/python tests/fix2_sensor_shots.py <outdir>
# Writes <outdir>/daytv_x1.png .. daytv_x8.png, ir_x1.png, ir_x8.png, daytv_x4_crop.png
import asyncio, os, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, IPHONE_15

OUT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else 'overnight-screenshots/fix2/before/sensor')
try:
    from PIL import Image
    HAVE_PIL = True
except ImportError:
    HAVE_PIL = False

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
    await pg.evaluate("(n)=>{const K=window.__kgeu;for(let i=0;i<n;i++)K.stepFrame(1/60,false,true);K.stepFrame(1/60);}", round(secs * 60))


async def shot(pg, name):
    path = os.path.join(OUT, name)
    await pg.screenshot(path=path, timeout=120000)
    print('  wrote', path)
    return path


def crop2x(src, dst):
    if not HAVE_PIL:
        print('  (PIL unavailable, skipped crop)', dst)
        return
    im = Image.open(src)
    w, h = im.size
    box = (w // 2 - 200, h // 2 - 150, w // 2 + 200, h // 2 + 150)
    c = im.crop(box)
    c = c.resize((c.width * 2, c.height * 2), Image.NEAREST)
    c.save(dst)
    print('  wrote', dst)


async def main():
    os.makedirs(OUT, exist_ok=True)
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'})
        await pg.evaluate("()=>{const K=window.__kgeu;K.setTOD('day');K.pick('reaper');K.pickBase('luke');K.start('final');}")
        await pg.wait_for_timeout(600)
        await pg.evaluate(PLACE)
        info = await pg.evaluate(AIM)
        print('  sensor:', info)
        daytv_x4 = None
        for mode, zi, name in [('tv', 0, 'daytv_x1.png'), ('tv', 1, 'daytv_x2.png'),
                                ('tv', 2, 'daytv_x4.png'), ('tv', 3, 'daytv_x8.png'),
                                ('irw', 0, 'ir_x1.png'), ('irw', 3, 'ir_x8.png')]:
            await pg.evaluate("([m,z])=>{const K=window.__kgeu,S=K.SENSOR;K.setSensorMode(m);S.zoom=z;}", [mode, zi])
            await settle(pg, 3.2)
            p_ = await shot(pg, name)
            if name == 'daytv_x4.png':
                daytv_x4 = p_
        if daytv_x4:
            crop2x(daytv_x4, os.path.join(OUT, 'daytv_x4_crop.png'))
        await pg.evaluate("()=>window.__kgeu.stepFrame(0,true)")
        if pg.errs:
            print('  page errors:', pg.errs[:5])
        else:
            print('  no console errors')
        await b.close()
    srv.shutdown()

asyncio.run(main())
