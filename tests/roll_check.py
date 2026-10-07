# Item 3.1: the chase camera stays smooth through rolls, barrel rolls and loops.
# For each aircraft: put it at ~3000 m and cruise speed, hold the rAF loop, and drive
# every frame with __kgeu.stepFrame(1/60) while scripting the stick through touchIn.
# Per frame the aircraft attitude, camera attitude, camera up and camera position must
# move by less than a fixed step, with no NaN, and the aircraft must really roll.
# Run: .venv/bin/python tests/roll_check.py [f16 cessna ...]
# Frames are stepped without the WebGL draw (stepFrame skipRender) so the run stays quick.
import asyncio, sys, math
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, IPHONE_15
ok = Checks()

TYPES = {'cessna': 110, 'archer': 110, 'alpha': 100, 'f16': 420, 'a10': 300, 'b737': 280, 'a320': 280, 'b747': 290, 'reaper': 170, 'mq9b': 180, 'c130': 250}
if sys.argv[1:]: TYPES = {t: TYPES[t] for t in sys.argv[1:]}
# phases: name, seconds, ail, elev (touchIn.elev > 0 is a pull, see touch_check.py)
PHASES = [('roll', 3.0, 1.0, 0.0), ('barrel', 4.0, 0.8, 0.5), ('loop', 6.0, 0.0, 1.0), ('neutral', 2.0, 0.0, 0.0)]
LIM = {'ac': 0.35, 'cam': 0.2, 'up': 0.2, 'lag': 1.1}   # lag: camera never trails by more than ~60 deg

SETUP = """([kt])=>{const K=window.__kgeu,s=K.state();
  const V=kt/1.94384/Math.sqrt(1.097*Math.exp(-3000/9200)/1.225);
  s.pos.y=3000+K.groundHeight(s.pos.x,s.pos.z);s.vel.set(0,0,-V);s.quat.set(0,0,0,1);s.w.set(0,0,0);
  s.onGround=false;s.airTime=30;s.flapIdx=0;s.throttle=s.power=1;s.gearDown=false;s.gearPos=0;s.ap=null;
  K.touchIn.active=false;K.touchIn.ail=0;K.touchIn.elev=0;K.snapCam();K.stepFrame(1/60,false,true);return true;}"""

# run one phase entirely in the page, return per-frame maxima
PHASE = """([sec,ail,elev])=>{const K=window.__kgeu,s=K.state(),T=THREE;
  const W=window.__rc||(window.__rc={q:new T.Quaternion(),cq:new T.Quaternion(),up:new T.Vector3(),cp:new T.Vector3(),init:false});
  const m={lag:0,ac:0,cam:0,up:0,pos:0,posLim:0,nan:false,roll:0,crashed:false};
  const au=new T.Vector3(),q=new T.Quaternion(),cq=new T.Quaternion(),up=new T.Vector3(),cp=new T.Vector3(),dq=new T.Quaternion();
  const ang=(a,b)=>2*Math.acos(Math.min(1,Math.abs(a.dot(b))));
  const n=Math.round(sec*60);K.touchIn.active=true;K.touchIn.ail=ail;K.touchIn.elev=elev;
  for(let i=0;i<n;i++){
    K.stepFrame(1/60,false,true);
    q.copy(s.quat);cq.fromArray(K.camQuat());up.fromArray(K.camUp());cp.fromArray(K.camPos());
    if([q.x,q.y,q.z,q.w,cq.x,cq.y,cq.z,cq.w,up.x,up.y,up.z,cp.x,cp.y,cp.z].some(v=>!isFinite(v)))m.nan=true;
    // camera lag: how far the camera up trails the aircraft up (the aircraft visibly rolls ahead)
    m.lag=Math.max(m.lag,au.set(0,1,0).applyQuaternion(q).angleTo(up));
    if(W.init){
      m.ac=Math.max(m.ac,ang(W.q,q));m.cam=Math.max(m.cam,ang(W.cq,cq));
      m.up=Math.max(m.up,up.angleTo(W.up));
      const d=cp.distanceTo(W.cp),lim=s.vel.length()/60+3;m.pos=Math.max(m.pos,d);if(d>=lim)m.posLim++;
      // roll about the body nose axis (-z), from the body-frame relative rotation
      dq.copy(W.q).invert().multiply(q);if(dq.w<0){dq.x=-dq.x;dq.y=-dq.y;dq.z=-dq.z;dq.w=-dq.w;}
      const a=2*Math.acos(Math.min(1,dq.w)),sn=Math.sqrt(Math.max(1e-12,1-dq.w*dq.w));m.roll+=-dq.z/sn*a;}
    W.q.copy(q);W.cq.copy(cq);W.up.copy(up);W.cp.copy(cp);W.init=true;
    if(s.crashed){m.crashed=s.crashReason;break;}
  }
  K.touchIn.active=false;K.touchIn.ail=0;K.touchIn.elev=0;
  m.roll=Math.abs(m.roll)*180/Math.PI;return m;}"""

async def main():
    srv, url = serve()
    worst = {'ac': 0, 'cam': 0, 'up': 0}
    async with async_playwright() as p:
        b = await launch(p)
        for t, kt in TYPES.items():
            pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'pilot', 'kgeuType': t, 'kgeuTut': '1', 'kgeuCoach': '3'})
            await pg.evaluate(f"()=>{{const K=window.__kgeu;K.pick('{t}');K.pickBase('kgeu');K.start('final');}}")
            await pg.wait_for_timeout(600)
            cam = await pg.evaluate("()=>window.__kgeu.camMode()")
            if cam != 0:
                await pg.evaluate("()=>{while(window.__kgeu.camMode()!==0)window.__kgeu.cycleCam();}")
            await pg.evaluate(SETUP, [kt])
            print(f'{t}:')
            for name, sec, ail, elev in PHASES:
                m = await pg.evaluate(PHASE, [sec, ail, elev])
                for k in worst: worst[k] = max(worst[k], m[k])
                ok(f'{t} {name}: smooth', not m['nan'] and not m['crashed'] and m['ac'] < LIM['ac'] and m['cam'] < LIM['cam']
                   and m['up'] < LIM['up'] and m['posLim'] == 0 and m['lag'] < LIM['lag'],
                   f"ac {m['ac']:.3f} cam {m['cam']:.3f} up {m['up']:.3f} pos {m['pos']:.1f}m over {m['posLim']} roll {m['roll']:.0f}deg lag {math.degrees(m['lag']):.0f}deg"
                   + (' NaN' if m['nan'] else '') + (f" CRASH {m['crashed']}" if m['crashed'] else ''))
                if name == 'roll':
                    need = 300 if t == 'f16' else 90 if t == 'cessna' else 0
                    if need: ok(f'{t} really rolled > {need} deg', m['roll'] > need, f"{m['roll']:.0f}")
            await pg.evaluate("()=>window.__kgeu.stepFrame(0,true)")
            ok(f'{t} no console errors', not pg.errs, pg.errs[:3])
            await pg.context.close()
        await b.close()
    print(f"\nworst per-frame: aircraft {worst['ac']:.3f} rad, camera {worst['cam']:.3f} rad, up {worst['up']:.3f} rad")
    srv.shutdown()
    return ok.done('roll_check')

sys.exit(asyncio.run(main()))
