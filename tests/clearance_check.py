# Ground clearance (phone 0929 item 13): every aircraft sitting on the runway has its tyre
# bottoms on the ground and everything else (fuselage, pods, antennas, ventral fins, nozzle,
# prop blades at every blade angle, the prop blur disc) clear of it; the same with the nose
# up at the type's normal rotation / flare pitch, pivoting on the main wheels. The parked
# ramp aircraft sit on the apron too.
# World-space vertices of every mesh against the ground under each one: the terrain mesh
# (terrainMeshH) plus the paved layer the runway paint lies on, found by one ray straight down.
# Run: .venv/bin/python tests/clearance_check.py [--noshots] [--noflows] [type ...]
# Side-on shots go to overnight-screenshots/phone0929/item13/.
import asyncio, os, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, IPHONE_15
ok = Checks()
SHOTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'overnight-screenshots', 'phone0929', 'item13')
K = 'window.__kgeu'
ARGS = [a for a in sys.argv[1:] if not a.startswith('--')]
TYPES = ARGS or ['cessna', 'archer', 'alpha', 'reaper', 'mq9b', 'f16', 'a10', 'c130', 'b737']
SHOT = '--noshots' not in sys.argv
FLOWS = '--noflows' not in sys.argv   # the takeoff and autoland sweep (slow: about 5 min)
TYRE_TOL = 0.05          # tyre bottoms within 5 cm of the surface
CLEAR = 0.05             # everything else at least 5 cm up
# prop tip clearance at rest, metres (real values, a little under: 172 about 11 in, Alpha
# about 10 in, the Reaper pusher tips small but positive over the ventral fin, Herc tips
# about 4 ft up on the wing)
PROP_MIN = {'cessna': 0.22, 'archer': 0.20, 'alpha': 0.20, 'reaper': 0.15, 'mq9b': 0.15, 'c130': 1.0}

MEASURE = r"""
(pitchAdd)=>{
  const k=window.__kgeu,pl=k.plane(),st=k.state(),HD=k.HD(),T=THREE;
  const tyreMat=HD&&HD.MAT.tyre;
  const g=pl.g;g.updateMatrixWorld(true);
  // the paved layer over the terrain mesh here: one ray down, the aircraft and the decals left out
  const {scene}=k.R3(),rc=new T.Raycaster(new T.Vector3(g.position.x,g.position.y+60,g.position.z),new T.Vector3(0,-1,0),0,200);
  const cand=[];scene.traverse(o=>{if(!o.isMesh||!o.visible)return;let p=o;while(p){if(p===g)return;p=p.parent;}
    const m=o.material;if(!m||m.depthWrite===false||m.transparent)return;cand.push(o);});
  const hits=rc.intersectObjects(cand,false);
  const tm=k.terrainMeshH(g.position.x,g.position.z);
  let lay=0;for(const h of hits){const d=h.point.y-tm;if(d>-0.01&&d<0.3){lay=d;break;}}
  const ground=(x,z)=>k.terrainMeshH(x,z)+lay;
  const inv=new T.Matrix4().copy(g.matrixWorld).invert();
  const P=pl.propRig,spin=P?P.ps:[],discs=P?P.ds:[];
  const isIn=(o,roots)=>{for(let p=o;p;p=p.parent)if(roots.includes(p))return true;return false;};
  const shown=o=>{for(let p=o;p&&p!==g;p=p.parent)if(!p.visible)return false;return true;};
  const v=new T.Vector3(),lv=new T.Vector3();
  const tyres=[],low={};let top=-1e9;   // low[kind] = lowest point {h, name, lx, ly, lz}
  function note(kind,h,o,w){if(!low[kind]||h<low[kind].h){lv.copy(w).applyMatrix4(inv);
    low[kind]={h:+h.toFixed(3),name:(o.name||o.parent&&o.parent.name||'')+' '+o.geometry.type+' '+(o.material&&o.material.color?o.material.color.getHexString():''),l:[+lv.x.toFixed(2),+lv.y.toFixed(2),+lv.z.toFixed(2)]};}}
  function scan(kind,o){const pos=o.geometry.attributes.position;if(!pos)return;
    for(let i=0;i<pos.count;i++){v.fromBufferAttribute(pos,i).applyMatrix4(o.matrixWorld);
      const h=v.y-ground(v.x,v.z);
      if(kind==='tyre'){lv.copy(v).applyMatrix4(inv);tyres.push([lv.x,lv.y,lv.z,h]);}
      else{note(kind,h,o,v);if(h>top)top=h;}}}
  g.traverse(o=>{
    if(!o.isMesh||!o.geometry)return;
    const prop=isIn(o,spin),disc=isIn(o,discs);
    if(prop||disc)return;                          // done below, at every blade angle
    if(pl.ab&&isIn(o,[pl.ab]))return;              // the afterburner flame is light, not airframe
    if(!shown(o))return;
    if(o.material&&o.material.transparent&&o.material.opacity<0.02&&!o.material.map)return;
    if(o.material===tyreMat)scan('tyre',o);
    else if(o.material&&o.material.color&&o.material.color.getHex()===0x17181a)scan('tyre',o);
    else scan(isIn(o,[pl.gear].filter(Boolean))?'gear':'airframe',o);
  });
  // props: every blade angle over a full turn, then the blur disc
  const z0=spin.map(s=>s.rotation.z);
  for(let a=0;a<24;a++){spin.forEach((s,i)=>{s.rotation.z=z0[i]+a*Math.PI*2/24;s.updateMatrixWorld(true);});
    spin.forEach(s=>s.traverse(o=>{if(o.isMesh&&o.geometry)scan('prop',o);}));}
  spin.forEach((s,i)=>{s.rotation.z=z0[i];s.updateMatrixWorld(true);});
  discs.forEach(d=>{d.updateMatrixWorld(true);scan('disc',d);});
  // tyres: cluster the vertices into wheels, lowest point of each
  const n=tyres.length,par=new Int32Array(n).map((_,i)=>i),f=i=>{while(par[i]!==i)i=par[i]=par[par[i]];return i;};
  // single link in plan view (x, z in the aircraft frame): a tyre is a short line of points there
  const idx=[...Array(n).keys()].sort((a,b)=>tyres[a][2]-tyres[b][2]);
  for(let ii=0;ii<n;ii++){const a=idx[ii];for(let jj=ii+1;jj<n;jj++){const b=idx[jj];if(tyres[b][2]-tyres[a][2]>0.25)break;
    if(Math.abs(tyres[a][0]-tyres[b][0])<0.2)par[f(a)]=f(b);}}
  const W={};for(let i=0;i<n;i++){const r=f(i),t=tyres[i];const w=W[r]||(W[r]={h:1e9,x:0,z:0,y:0,c:0});
    if(t[3]<w.h)w.h=t[3];w.x+=t[0];w.y+=t[1];w.z+=t[2];w.c++;}
  const wheels=Object.values(W).map(w=>({h:+w.h.toFixed(3),x:+(w.x/w.c).toFixed(2),y:+(w.y/w.c).toFixed(2),z:+(w.z/w.c).toFixed(2)}));
  const e=new T.Euler().setFromQuaternion(g.quaternion,'YXZ');
  return {wheels:wheels,low:low,top:+top.toFixed(2),lay:+lay.toFixed(3),pitch:+(e.x*180/Math.PI).toFixed(2),posY:+(g.position.y-tm).toFixed(3),
          stY:+(st.pos.y-tm).toFixed(3),onGround:st.onGround,gearPos:st.gearPos};
}
"""

def fmt(r):
    L = r['low']
    s = [f"pitch {r['pitch']:+.1f} deg lay {r['lay']:+.3f} y {r['posY']:+.3f}"]
    for kk in ('airframe', 'gear', 'prop', 'disc'):
        if kk in L: s.append(f"{kk} {L[kk]['h']:+.3f} @{L[kk]['l']}")
    w = r['wheels']
    s.append('tyres ' + ', '.join(f"{x['h']:+.3f}(z{x['z']:+.2f} y{x['y']:+.2f})" for x in sorted(w, key=lambda x: x['z'])))
    s.append(f"top {r['top']}")
    return '  '.join(s)

async def main():
    os.makedirs(SHOTS, exist_ok=True)
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'})
        ev = lambda js: pg.evaluate("()=>{" + js + "}")
        async def step(n, dt=1/60, render=False):
            await pg.evaluate("([n,dt,r])=>{for(let i=0;i<n;i++)window.__kgeu.stepFrame(dt,false,!r||i<n-1);}", [n, dt, render])
        await ev(f"{K}.setSkill('pilot')")
        for t in TYPES:
            print('--', t)
            await pg.evaluate("()=>window.__kgeu.stepFrame(0,true)")
            await ev(f"{K}.pick('{t}');{K}.pickBase({K}.baseOK('{t}','kgeu')?'kgeu':'phx');{K}.start('runway')"); await pg.wait_for_timeout(1200)
            await ev(f"const s={K}.state();s.throttle=0;s.brake=true;")
            await step(120)
            await ev(f"const s={K}.state();s.throttle=0;s.power=0;s.brake=true;")
            await step(2, render=True)
            r = await pg.evaluate(MEASURE, 0)
            print('  rest ', fmt(r))
            ac = await pg.evaluate(f"()=>{{const A={K}.TYPES['{t}'];return {{rot:A.rotP,td:A.tdPitch,gnd:A.gndPitch}}}}")
            ok(f'{t} on the ground, gear down', r['onGround'] and r['gearPos'] > 0.99, (r['onGround'], r['gearPos']))
            wh = r['wheels']
            ok(f'{t} every tyre on the surface (+-{TYRE_TOL} m)', wh and all(abs(w['h']) <= TYRE_TOL for w in wh), [w['h'] for w in wh])
            L = r['low']
            ok(f'{t} airframe clear > {CLEAR} m', L['airframe']['h'] > CLEAR, L['airframe'])
            if 'gear' in L: ok(f'{t} gear legs and hubs clear > 0.01 m', L['gear']['h'] > 0.01, L['gear'])
            if t in PROP_MIN:
                pm = min(L['prop']['h'], L.get('disc', {'h': 9})['h'])
                ok(f'{t} prop tips clear > {PROP_MIN[t]} m', pm > PROP_MIN[t], (L['prop'], L.get('disc')))
            if SHOT:
                span = await pg.evaluate(f"()=>{K}.TYPES['{t}'].len")
                d = span * 1.9
                cam = f"{{p:[{d},-0.9,0.4],t:[0,-0.1,0.4],fov:30}}"   # low and side on, the lens just over the tyres
                await ev(f"{K}.freeCam({cam})")
                await pg.evaluate("()=>window.__kgeu.stepFrame(1/60,false,false)")
                await pg.screenshot(path=f'{SHOTS}/{t}_side.png')
                await ev(f"{K}.freeCam(null)")
            # nose up on the main wheels: the type's normal rotation / flare pitch (as far as the
            # physics lets it on the ground), then the physics' ground pitch limit itself
            gp = min(max(ac['rot'], ac['td']), ac['gnd'])
            for tag, pitch in (('rot', gp), ('max', ac['gnd'])):
                # vr 0 for the moment: at a standstill the nose wheel would settle back down
                await ev(f"const s={K}.state(),e=new THREE.Euler().setFromQuaternion(s.quat,'YXZ');e.x={pitch};e.z=0;s.quat.setFromEuler(e);s.w.set(0,0,0);s.brake=true;s.throttle=0;{K}.TYPES['{t}']._vr={K}.TYPES['{t}'].vr;{K}.TYPES['{t}'].vr=0;")
                await step(2, render=True)
                await ev(f"{K}.TYPES['{t}'].vr={K}.TYPES['{t}']._vr;")
                r2 = await pg.evaluate(MEASURE, 0)
                print(f'  {tag}  ', fmt(r2))
                L = r2['low']
                props = min(L['prop']['h'] if 'prop' in L else 9, L['disc']['h'] if 'disc' in L else 9)
                if tag == 'rot':
                    # the aft main wheels on the surface (a tandem pair ahead of them lifts), none in it
                    hs = [w['h'] for w in r2['wheels']]
                    aft = [w['h'] for w in r2['wheels'] if w['z'] > max(x['z'] for x in r2['wheels']) - 0.3]
                    ok(f'{t} at {pitch:.2f} rad on the mains: aft mains on the surface, no tyre in it', all(abs(h) <= TYRE_TOL for h in aft) and min(hs) >= -TYRE_TOL, hs)
                    lowest = min(L['airframe']['h'], props)
                    ok(f'{t} at {pitch:.2f} rad: tail, nozzle, fins, prop clear > {CLEAR} m', lowest > CLEAR, (L['airframe'], L.get('prop')))
                    if SHOT:
                        await ev(f"{K}.freeCam({cam})")
                        await pg.evaluate("()=>window.__kgeu.stepFrame(1/60,false,false)")
                        await pg.screenshot(path=f'{SHOTS}/{t}_rotate.png')
                        await ev(f"{K}.freeCam(null)")
                elif props < 9:
                    ok(f'{t} at the {pitch:.2f} rad ground pitch limit the prop never touches', props > 0, L.get('prop'))
        # the real thing: an auto takeoff, a 1 nm autoland and a 1 nm Easy hands-off landing per
        # type, the lowest airframe and prop
        # points sampled whenever the wheels are within 3 m of the runway with the gear down
        if FLOWS:
            for t in TYPES:
                for flow in ('takeoff', 'autoland', 'easy'):
                    await pg.evaluate("()=>window.__kgeu.stepFrame(0,true)")
                    await ev(f"{K}.setSkill('{'rookie' if flow == 'easy' else 'pilot'}');{K}.pick('{t}');{K}.pickBase('kgeu');{K}.start('{'runway' if flow == 'takeoff' else 'final1'}')"); await pg.wait_for_timeout(1000)
                    await step(2)
                    if flow != 'easy': await ev(f"{K}.apToggle('{'to' if flow == 'takeoff' else 'land'}')")
                    lo = {'airframe': 9, 'prop': 9}; worst = {}; n = 0; done = False
                    for i in range(1500):
                        await step(4)
                        g = await pg.evaluate(f"()=>{{const s={K}.state();return {{agl:s.agl,gp:s.gearPos,on:s.onGround,c:s.crashed,v:s.ias,vr:{K}.TYPES['{t}'].vr,air:s.airTime}}}}")
                        if g['c']: break
                        if g['agl'] < 3 and g['gp'] > 0.9 and g['v'] > 0.5 * g['vr']:
                            r = await pg.evaluate(MEASURE, 0); n += 1
                            L = r['low']
                            for kk, h in (('airframe', L['airframe']['h']), ('prop', min(L['prop']['h'] if 'prop' in L else 9, L['disc']['h'] if 'disc' in L else 9))):
                                if h < lo[kk]: lo[kk] = h; worst[kk] = (r['pitch'], L.get(kk, L.get('disc')))
                        if flow == 'takeoff' and g['agl'] > 20: done = True; break
                        if flow != 'takeoff' and g['on'] and g['v'] < 0.4 * g['vr']: done = True; break
                    print(f'  {flow:8s} {n} samples, lowest airframe {lo["airframe"]:+.3f} prop {lo["prop"]:+.3f}  {worst}')
                    ok(f'{t} {flow}: done without a crash', done, g)
                    ok(f'{t} {flow}: airframe and prop clear > {CLEAR} m all the way', n > 0 and min(lo.values()) > CLEAR, (lo, worst))
            await ev(f"{K}.setSkill('pilot')")
        # the parked ramp aircraft on the apron
        pk = await pg.evaluate("""()=>{const k=window.__kgeu,T=THREE,out=[];for(const g of k.PARKED()){g.updateMatrixWorld(true);
            let lo=1e9,hi=-1e9;const v=new T.Vector3();g.traverse(o=>{if(!o.isMesh||!o.geometry)return;const P=o.geometry.attributes.position;
            for(let i=0;i<P.count;i++){v.fromBufferAttribute(P,i).applyMatrix4(o.matrixWorld);const h=v.y-k.terrainMeshH(v.x,v.z);if(h<lo)lo=h;}});
            // less the apron paint under it (one ray down, the parked aircraft left out)
            const {scene}=k.R3(),rc=new T.Raycaster(new T.Vector3(g.position.x,60,g.position.z),new T.Vector3(0,-1,0),0,200),cand=[];
            scene.traverse(o=>{if(!o.isMesh||!o.visible)return;for(let p=o;p;p=p.parent)if(k.PARKED().includes(p))return;const m=o.material;if(!m||m.depthWrite===false||m.transparent)return;cand.push(o);});
            const tm=k.terrainMeshH(g.position.x,g.position.z);let lay=0;for(const h of rc.intersectObjects(cand,false)){const d=h.point.y-tm;if(d>-0.01&&d<0.3){lay=d;break;}}
            out.push(+(lo-lay).toFixed(3));}return out;}""")
        print('  parked lowest points', pk)
        ok('parked aircraft sit on the apron paint (lowest point within 5 cm)', all(abs(h) <= TYRE_TOL for h in pk), pk)
        await pg.evaluate("()=>window.__kgeu.stepFrame(0,true)")
        ok('no page errors', not pg.errs, pg.errs[:3])
        await b.close()
    srv.shutdown()
    return ok.done('clearance_check')

sys.exit(asyncio.run(main()))
