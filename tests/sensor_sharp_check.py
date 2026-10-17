# fix2 item 4: the MQ-9 sensor view is drawn crisp. Medium tier, iPhone landscape (844x390).
# With the dynamic scale at 0.7, the sensor view (Day TV and IR) draws the scene at the full target size, no bloom,
# no SMAA, sharpened; leaving it the scene is back at 0.7 and the dynamic state is as it was (frozen, not reset); no
# 'scale' or 'rt' stall tag from the switches; then Day TV at x4, the canvas centre's Laplacian variance with the
# sharpening on beats it off (__kgeu.sharpOff) by at least 15 percent.
# Usage: .venv/bin/python -u tests/sensor_sharp_check.py
import asyncio, io, sys
from playwright.async_api import async_playwright
from PIL import Image
from harness import serve, launch, page, IPHONE_15, Checks

PLACE = """()=>{const K=window.__kgeu,s=K.state(),L=K.LUKE,sn=Math.sin(L.h),cs=Math.cos(L.h);
  const cx=L.x+(-177)*cs,cz=L.z+(-177)*sn;window.__rc=[cx,cz];
  const d=8000/Math.SQRT2,x=cx-d,z=cz+d,hdg=-Math.PI/4,V=80;
  s.pos.set(x,4570+K.groundHeight(x,z),z);s.vel.set(Math.sin(hdg)*V,0,-Math.cos(hdg)*V);
  s.quat.setFromEuler(new THREE.Euler(0,-hdg,0,'YXZ'));s.w.set(0,0,0);
  s.onGround=false;s.airTime=30;s.flapIdx=0;s.throttle=s.power=0.7;s.gearDown=false;s.gearPos=0;s.ap=null;
  K.touchIn.active=false;K.touchIn.ail=0;K.touchIn.elev=0;K.snapCam();K.stepFrame(1/60,false,true);return true;}"""
AIM = """()=>{const K=window.__kgeu,s=K.state(),S=K.SENSOR,[cx,cz]=window.__rc;
  const o=K.camPos(),gy=K.groundHeight(cx,cz),dx=cx-o[0],dy=gy-o[1],dz=cz-o[2],hz=Math.hypot(dx,dz);
  const e=new THREE.Euler().setFromQuaternion(s.quat,'YXZ');
  let az=Math.atan2(dx,-dz)+e.y;az=Math.atan2(Math.sin(az),Math.cos(az));
  S.az=az;S.el=Math.atan2(dy,hz);S.track=null;S.tgt=null;K.stepFrame(1/60,false,true);K.sensorLock();
  for(let i=0;i<60;i++)K.stepFrame(1/60,false,true);return K.sensor();}"""
# into the sensor view (the scale set to 0.7 first, a marker in the dynamic state), one drawn frame
ENTER = """()=>{const K=window.__kgeu,G=K.GFX,c0=K.progN().compiles;K.setScale(0.7);G.dynS.t=40;G.dynS.lowT=1.25;G.dynS.cool=0;
  while(K.camMode()!==2)K.cycleCam();for(let i=0;i<3;i++)K.stepFrame(1/60);return {pfx:K.pfx(),dyn:Object.assign({},G.dynS),comp:K.progN().compiles-c0};}"""
LEAVE = """()=>{const K=window.__kgeu,G=K.GFX,d=Object.assign({},G.dynS);while(K.camMode()===2)K.cycleCam();K.stepFrame(1/60);return {pfx:K.pfx(),dyn:d};}"""


def lapvar(png):
    im = Image.open(io.BytesIO(png)).convert('L')
    w, h = im.size
    p = list(im.tobytes())
    vals = []
    for y in range(1, h - 1):
        r = y * w
        for x in range(1, w - 1):
            i = r + x
            vals.append(p[i - 1] + p[i + 1] + p[i - w] + p[i + w] - 4 * p[i])
    m = sum(vals) / len(vals)
    return sum((v - m) ** 2 for v in vals) / len(vals)


async def main():
    ok = Checks()
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3', 'kgeuTier': 'medium'})
        await pg.evaluate("()=>{const K=window.__kgeu;K.setTOD('day');K.pick('reaper');K.pickBase('luke');K.start('final');}")
        await pg.wait_for_timeout(600)
        await pg.evaluate(PLACE)
        # round 2: no program links in flight across the sensor views: IR in, out, Day TV in, out, IR white, IR black,
        # out, each 3 drawn frames; the compiles counter after the first sensor frame never moves
        seq = await pg.evaluate("""()=>{const K=window.__kgeu,F=()=>{for(let i=0;i<3;i++)K.stepFrame(1/60);},C=()=>K.progN().compiles,
            keys=()=>K.progList().map(p=>p.name+' '+p.cacheKey),out=[];
          K.stepFrame(1/60);const c00=C(),k0=keys();
          K.setSensorMode('irw');while(K.camMode()!==2)K.cycleCam();K.stepFrame(1/60);const c0=C();out.push(['first IR frame',c0-c00]);F();out.push(['IR in',C()]);
          while(K.camMode()===2)K.cycleCam();F();out.push(['IR out',C()]);
          K.setSensorMode('tv');while(K.camMode()!==2)K.cycleCam();F();out.push(['TV in',C()]);
          while(K.camMode()===2)K.cycleCam();F();out.push(['TV out',C()]);
          while(K.camMode()!==2)K.cycleCam();K.setSensorMode('irw');F();out.push(['IR white',C()]);
          K.setSensorMode('irb');F();out.push(['IR black',C()]);
          while(K.camMode()===2)K.cycleCam();F();out.push(['out',C()]);
          const nk=keys().filter(k=>!k0.includes(k)).map(k=>k.slice(0,400));
          return {c0:c0,steps:out,newProgs:nk};}""")
        grew = [s_ for s_ in seq['steps'][1:] if s_[1] != seq['c0']]
        ok('no program linked after the first sensor frame (IR, out, TV, out, IR white, IR black, out)', not grew,
           f"c0 {seq['c0']} first frame +{seq['steps'][0][1]} steps {seq['steps'][1:]}" + (f" new {seq['newProgs']}" if grew else ''))
        ok('the first sensor frame links nothing either', seq['steps'][0][1] == 0, seq['newProgs'] if seq['steps'][0][1] else '')
        await pg.evaluate("()=>{const K=window.__kgeu;K.stepFrame(1/60);K.stallsThr(250);K.stallsClear();}")
        base = await pg.evaluate("()=>window.__kgeu.pfx()")
        ok('medium: post chain on', base['post'] is True, base)
        comp = []
        for mode in ('tv', 'irw'):
            await pg.evaluate("(m)=>window.__kgeu.setSensorMode(m)", mode)
            e = await pg.evaluate(ENTER)
            if e['comp']: comp.append((mode, e['comp']))
            if mode == 'tv':
                await pg.evaluate(AIM)
                e = await pg.evaluate("()=>{const K=window.__kgeu;K.stepFrame(1/60);return {pfx:K.pfx(),dyn:Object.assign({},K.GFX.dynS)};}")
            f = e['pfx']
            ok(f'{mode}: sensor view at full size (sw,sh = w,h) with scale 0.7 kept', f['sw'] == f['w'] and f['sh'] == f['h'] and f['scale'] == 0.7 and f['sens'], f)
            ok(f'{mode}: no bloom, no SMAA, sharpened', not f['bloomed'] and not f['smaa'] and f['sharp'] > 0, f['sharp'])
            ok(f'{mode}: dynamic state frozen in the sensor view', abs(e['dyn']['lowT'] - 1.25) < 1e-9 and e['dyn']['t'] == 40, e['dyn'])
            l = await pg.evaluate(LEAVE)
            f = l['pfx']
            ok(f'{mode}: out of the sensor view back at 0.7', abs(f['sw'] - 0.7 * f['w']) <= 1 and f['scale'] == 0.7 and f['sharp'] == 0 and not f['sens'], f)
            ok(f'{mode}: dynamic state not reset', abs(l['dyn']['lowT'] - 1.25) < 1e-9, l['dyn'])
        ok('no program compiled entering the sensor views (Day TV, IR, the sharpened composite)', not comp, comp)
        # real frames across a switch in and out (the loop released), then the stall log's tags
        # headless frames run ~180 ms, under the spec's 250 ms: 120 ms here so the switch frames are logged with their tags
        await pg.evaluate("()=>{const K=window.__kgeu;K.stallsThr(120);K.stallsClear();K.stepFrame(0,true);}")
        await pg.wait_for_timeout(1500)
        await pg.evaluate("()=>{const K=window.__kgeu;while(K.camMode()!==2)K.cycleCam();}")
        await pg.wait_for_timeout(2500)
        await pg.evaluate("()=>{const K=window.__kgeu;while(K.camMode()===2)K.cycleCam();}")
        await pg.wait_for_timeout(2500)
        st = await pg.evaluate("()=>window.__kgeu.stalls().log.map(e=>e.tags||e.tag||'')")
        bad = [t for t in st if any(k in (t if isinstance(t, list) else str(t).split(' ')) for k in ('scale', 'rt'))]
        ok('stall entries logged around the switches, none tagged scale or rt', len(st) > 0 and not bad, f'{len(st)} entries, bad {bad[:3]}')
        sc = await pg.evaluate("()=>window.__kgeu.GFX.scale")
        ok('scale still 0.7 after the real frames', sc == 0.7, sc)
        # sharpness: Day TV at x4, the canvas centre 300x200, overlay and sensor HUD hidden
        await pg.evaluate("()=>{const K=window.__kgeu;K.stepFrame(1/60,false,true);while(K.camMode()!==2)K.cycleCam();K.setSensorMode('tv');K.SENSOR.zoom=2;}")
        await pg.evaluate(AIM)
        await pg.evaluate("()=>{const K=window.__kgeu;for(let i=0;i<120;i++)K.stepFrame(1/60,false,true);"
                          "for(const id of ['sensorFx','sensorHud'])document.getElementById(id).style.visibility='hidden';}")
        bb = await pg.evaluate("()=>{const r=document.getElementById('gl').getBoundingClientRect();return [r.x,r.y,r.width,r.height];}")
        clip = {'x': bb[0] + bb[2] / 2 - 150, 'y': bb[1] + bb[3] / 2 - 100, 'width': 300, 'height': 200}
        res = {}
        for off in (False, True):
            await pg.evaluate("(v)=>{const K=window.__kgeu;K.sharpOff(v);K.stepFrame(0);K.stepFrame(1/60);}", off)
            res[off] = lapvar(await pg.screenshot(clip=clip, timeout=120000))
        gain = res[False] / res[True] - 1 if res[True] else 0
        ok('x4 Laplacian variance: sharpening on beats off by 15%+', gain >= 0.15, f'on {res[False]:.1f} off {res[True]:.1f} gain {gain*100:.1f}%')
        await pg.evaluate("()=>{const K=window.__kgeu;K.sharpOff(false);K.stepFrame(0,true);}")
        ok('no page errors', not pg.errs, pg.errs[:3])
        await b.close()
    srv.shutdown()
    sys.exit(ok.done('sensor_sharp_check'))

asyncio.run(main())
