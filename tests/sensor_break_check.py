# sensor item 8, break-ui on the sensor view: the worst realistic values through the game's own state (the data
# boundary), at every phone size. Cases:
#  hard_worst  IR BLK at UNFOV EZ 4X in a geo stare the airframe masks (the longest TL), looking aft and level so the
#              point of interest is sky (SPI ---, SLT --- NO RTN after LASE), AZ L1xx EL -1, at 50,000 ft and 330 kt
#  hard_rio    Rio: S and W coordinates, MGRS 23K; LRF ON; the dial past straight down (EL -120)
#  hard_tokyo  Tokyo: N and E with a three digit longitude, MGRS 54S
#  easy_worst  Easy on the range: no lock, out of range, the centre block's tail (Tap NEXT TARGET, then FIRE), a geo
#              stare masked (Holding the spot / View blocked), the plain cue 'Too far round'
#  strike_dc2  the range at declutter 2 (the strike block stays) and 1
# Each: no readout overlaps another readout, the map, pause or a button; all on screen; every button label inside its
# button; the cue clear of the readouts. Screenshots in overnight-screenshots/sensor/break.
# Usage: .venv/bin/python tests/sensor_break_check.py [--sizes 568x320,...] [--cases a,b]
import asyncio, os, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks

K = 'window.__kgeu'
def arg(k, d): return sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d
SIZES = arg('--sizes', '568x320,667x375,844x390,932x430,800x360,915x412,390x844,375x667').split(',')
CASES = arg('--cases', 'hard_worst,hard_rio,hard_tokyo,easy_worst,strike_dc2').split(',')
OUT = os.path.abspath('overnight-screenshots/sensor/break')
PLACE = """([hdgD,alt,V])=>{const K=window.__kgeu,s=K.state();const x=K.REGION_AZ?K.LUKE.x-6000:1500,z=K.REGION_AZ?K.LUKE.z+3000:-2500,hdg=hdgD*Math.PI/180;
  s.pos.set(x,alt/3.28084,z);s.vel.set(Math.sin(hdg)*V,0,-Math.cos(hdg)*V);
  s.quat.setFromEuler(new THREE.Euler(0,-hdg,0,'YXZ'));s.w.set(0,0,0);s.ias=V;
  s.onGround=false;s.airTime=30;s.flapIdx=0;s.throttle=s.power=0.7;s.gearDown=false;s.gearPos=0;s.ap=null;
  K.touchIn.active=false;K.snapCam();K.stepFrame(1/60,false,true);while(K.camMode()!==2)K.cycleCam();K.stepFrame(1/60,false,true);
  window.__q0=s.quat.clone();window.__p0=s.pos.clone();window.__slewPre=()=>{s.quat.copy(window.__q0);s.pos.copy(window.__p0);s.vel.set(Math.sin(hdg)*V,0,-Math.cos(hdg)*V);};return K.sensorMode();}"""
STEP = "(n)=>{const K=window.__kgeu;for(let i=0;i<n;i++){window.__slewPre&&window.__slewPre();K.stepFrame(1/60,false,true);}window.__slewPre&&window.__slewPre();K.stepFrame(1/60);return K.sensor();}"
CHECK = """()=>{const W=innerWidth,H=innerHeight,bad=[],out=[],lbl=[];
  const R=e=>{const r=e.getBoundingClientRect();return r.width>0&&r.height>0&&getComputedStyle(e).display!=='none'&&getComputedStyle(e).visibility!=='hidden'?r:null;};
  const tb=e=>{if(!R(e))return null;if(e.id==='shDialW'||e.tagName==='CANVAS'||e.tagName==='BUTTON')return R(e);const rg=document.createRange();rg.selectNodeContents(e);
    const rs=[...rg.getClientRects()].filter(r=>r.width>1);return rs.length?{left:Math.min(...rs.map(r=>r.left)),top:Math.min(...rs.map(r=>r.top)),right:Math.max(...rs.map(r=>r.right)),bottom:Math.max(...rs.map(r=>r.bottom))}:null;};
  const txt=['shTL','shTR','shTgt','shDialW','shMid','shCue'].map(i=>[i,tb(document.getElementById(i))]).filter(a=>a[1]&&(a[0]!=='shCue'||document.getElementById('shCue').classList.contains('on')));
  const oth=[['map',R(document.getElementById('map'))],['pause',R(document.getElementById('bPause'))],...[...document.querySelectorAll('#dock button,#fovInd')].map(e=>[e.id,R(e)])].filter(a=>a[1]);
  const hit=(a,b)=>a.left<b.right-1&&b.left<a.right-1&&a.top<b.bottom-1&&b.top<a.bottom-1;const bx=r=>[r.left,r.top,r.right,r.bottom].map(Math.round);
  for(let i=0;i<txt.length;i++){const [n,a]=txt[i];if(a.left<-1||a.top<-1||a.right>W+1||a.bottom>H+1)out.push(n+' '+bx(a));
    for(let j=i+1;j<txt.length;j++)if(hit(a,txt[j][1]))bad.push(n+' x '+txt[j][0]+' '+bx(a)+' '+bx(txt[j][1]));
    for(const [m,b] of oth)if(hit(a,b))bad.push(n+' x '+m+' '+bx(a)+' '+bx(b));}
  for(const e of document.querySelectorAll('#dock button')){const r=R(e);if(!r)continue;for(const i of e.querySelectorAll('i')){const q=i.getBoundingClientRect();
    if(q.width&&(q.left<r.left-0.5||q.right>r.right+0.5))lbl.push(e.id+' "'+i.textContent+'" '+Math.round(q.width)+' in '+Math.round(r.width));}}
  return {bad,out,lbl,TL:document.getElementById('shTL').innerText,TR:document.getElementById('shTR').innerText,TG:document.getElementById('shTgt').innerText};}"""


async def setup(pg, case):
    st = {'kgeuOnboard': 'rookie' if case.startswith('easy') else 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'}
    return st


async def run_case(pg, case):
    if case in ('hard_worst', 'hard_rio', 'hard_tokyo'):
        await pg.evaluate(f"()=>{{const K={K};K.setTOD('night');K.pick('mq9b');K.start('final');}}"); await pg.wait_for_timeout(800)
        alt = 50000 if case == 'hard_worst' else 9000
        await pg.evaluate("()=>{window.__kgeu.REGION_AZ=!!window.__kgeu.LUKE&&location.search.indexOf('r=')<0&&localStorage.getItem('kgeuRegion')===null;}")
        await pg.evaluate(PLACE, [357, alt, 170])
        if case == 'hard_worst':
            await pg.evaluate(f"()=>{{const K={K},S=K.SENSOR;K.setSensorMode('irb');S.zoom=7;S.az=-0.3;S.el=-0.6;}}"); await pg.evaluate(STEP, 3)
            await pg.evaluate(f"()=>{{const K={K},S=K.SENSOR;S.geo=S.spot.clone();}}"); await pg.evaluate(STEP, 2)
            await pg.evaluate(f"()=>{{const K={K},s=K.state();window.__q0.premultiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1,0,0),0.0));}}")
            await pg.evaluate(f"()=>{{const S={K}.SENSOR;S.geo=null;S.az=-2.9;S.el=-0.02;}}"); await pg.evaluate(STEP, 8)
            await pg.evaluate(f"()=>{{const S={K}.SENSOR;S.geo=S.spot.clone();S.lrfT=10;S.cue='GIMBAL';S.cueT=2;}}")
            # the longest top left line: an area track with MASK up (a masked track lasts 0.3 s; the state is set as it is then)
            await pg.evaluate(f"()=>{{const S={K}.SENSOR;S.geo=null;S.track=S.los.clone().multiplyScalar(500).add(new THREE.Vector3(...{K}.camPos()));S.acq=false;}}")
            await pg.evaluate(STEP, 1); await pg.evaluate(f"()=>{{const S={K}.SENSOR;S.mask=true;S.masked=true;S.maskChk=99;S.maskT=-99;}}")
        elif case == 'hard_rio':
            await pg.evaluate(f"()=>{{const K={K},S=K.SENSOR;K.setSensorMode('nir');S.zoom=4;S.az=0.4;S.el=-2.1;S.lrfT=10;}}")
        else:
            await pg.evaluate(f"()=>{{const K={K},S=K.SENSOR;K.setSensorMode('irw');S.zoom=6;S.az=1.2;S.el=-0.9;}}")
        await pg.evaluate(STEP, 6)
    elif case == 'easy_worst':
        await pg.evaluate(f"()=>{{const K={K};K.setTOD('haboob');K.pick('reaper');K.mission('range');}}"); await pg.wait_for_timeout(1500)
        await pg.evaluate("()=>{window.__slewPre=null;}")
        await pg.evaluate(f"()=>{{const K={K},S=K.SENSOR;S.az=3.0;S.el=0.3;S.zoom=4;}}"); await pg.evaluate(STEP, 3)
        await pg.evaluate(f"()=>{{const S={K}.SENSOR;S.cue='GIMBAL';S.cueT=2.4;S.geo=S.spot.clone();S.mask=true;S.masked=true;}}"); await pg.evaluate(STEP, 1)
    else:
        await pg.evaluate(f"()=>{{const K={K};K.setTOD('day');K.pick('reaper');K.mission('range');}}"); await pg.wait_for_timeout(1500)
        await pg.evaluate("()=>{window.__slewPre=null;}")
        await pg.evaluate(f"()=>{{const K={K},i=K.STRIKE.targets.findIndex(t=>t.kind==='hull');K.pointAt(i);K.trackHere();K.sensorDclt();K.sensorDclt();}}")
        await pg.evaluate(STEP, 6)


async def main():
    os.makedirs(OUT, exist_ok=True)
    c = Checks(); srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        for case in CASES:
            for sz in SIZES:
                w, h = [int(v) for v in sz.split('x')]
                st = await setup(None, case)
                if case == 'hard_rio': st['kgeuRegion'] = 'sbrj'
                if case == 'hard_tokyo': st['kgeuRegion'] = 'rjtt'
                pg = await page(b, url, vp={'width': w, 'height': h}, storage=st)
                await pg.wait_for_function("()=>!window.__kgeu.WORLD||true")
                if h > w: await pg.evaluate("()=>document.body.classList.add('portraitok')")
                try:
                    await run_case(pg, case)
                    await pg.evaluate("()=>{const t=document.getElementById('toast');t&&t.classList.remove('on');}")
                    await pg.wait_for_timeout(250)
                    r = await pg.evaluate(CHECK)
                    await pg.screenshot(path=os.path.join(OUT, f'{case}_{sz}.png'), timeout=120000)
                    c(f'{case} {sz}: readouts clear of each other and the controls, on screen, labels inside buttons', not r['bad'] and not r['out'] and not r['lbl'],
                      {k: r[k] for k in ('bad', 'out', 'lbl')} if (r['bad'] or r['out'] or r['lbl']) else '')
                    if sz == SIZES[0]: print('     TL', repr(r['TL']), '| TR', repr(r['TR']), '| TG', repr(r['TG']))
                except Exception as e:
                    c(f'{case} {sz}: ran', False, str(e)[:200])
                if pg.errs: c(f'{case} {sz}: no console errors', False, pg.errs[:3])
                await pg.close()
        await b.close()
    srv.shutdown(); c.done('sensor_break_check')

asyncio.run(main())
