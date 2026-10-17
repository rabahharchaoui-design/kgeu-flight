# Crashfx review shots: a crash into a structure, seen from a fixed camera off the impact (and from far for the column),
# by day, at sunset and at night. Each case flies the aircraft straight into the structure (as crashfx_check), lets the
# breakup and the fire run for `secs` of sim time, then frames it.
# Run: .venv/bin/python -u tests/crashfx_shots.py <outdir> [--tod day,night] [--cases hangar,stadium] [--secs 6] [--root <dir>]
import asyncio, os, sys, json
from playwright.async_api import async_playwright
from harness import serve, launch, page, IPHONE_15

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
K = 'window.__kgeu'
args = sys.argv[1:]
out = args[0] if args and not args[0].startswith('--') else '/tmp/crashfx_shots'
def opt(k, d):
    return args[args.index(k) + 1] if k in args else d
TODS = opt('--tod', 'day,night').split(',')
NOFX = '--nofx' in args
SECS = float(opt('--secs', '6'))
ROOT = opt('--root', None)
# name: type, record selector, approach axis and side, distance back, height fraction, speed m/s, views [(dist out, up, side, look up)]
CASES = {
    'hangar':  ('cessna', "r.name==='a hangar'&&Math.abs(r.x-K.STR.list.filter(q=>q.name==='a hangar')[2].x)<1", 'x', 1, 40, 0.5, 50, [(45, 10, 22, 2), (160, 45, -60, 4)]),
    'hangar737': ('b737', "r.name==='a hangar'&&Math.abs(r.x-K.STR.list.filter(q=>q.name==='a hangar')[2].x)<1", 'x', 1, 60, 0.5, 75, [(60, 16, 30, 2), (200, 60, -80, 6)]),
    'stadium': ('b747', "r.name==='the stadium'", 'x', -1, 60, 0.45, 80, [(150, 30, 70, 6), (700, 160, -250, 60)]),
    'stadium172': ('cessna', "r.name==='the stadium'", 'x', -1, 40, 0.45, 50, [(50, 10, 25, 2)]),
    'tower':   ('f16', "r.name==='a tower'&&r.y1>120", 'x', 1, 80, 0.5, 220, [(140, 10, 60, 0), (600, 120, -200, 40)]),
    'house':   ('cessna', "r.name==='a house'&&Math.hypot(r.x+2473,r.z+1767.5)<1", 'x', -1, 30, 0.5, 45, [(35, 12, 16, 1)]),
    'terminal': ('a320', "r.name==='the terminal'&&r.y1>20", 'z', -1, 60, 0.5, 75, [(120, 25, 50, 4)]),
}
SEL = opt('--cases', ','.join(CASES)).split(',')

FLY = """([type,sel,ax,sg,back,frac,spd])=>{const K=window.__kgeu;K.pick(type);K.pickBase(K.baseOK(type,'kgeu')?'kgeu':'phx');K.start('runway');K.freeCam(null);
  for(let i=0;i<3;i++)K.stepFrame(1/30,false,true);
  const S=K.STR.list,f=new Function('r','K','return '+sel),r=S.find(q=>f(q,K));if(!r)return {err:'no record'};
  const st=K.state();let lx=0,lz=0;if(ax==='x')lx=sg*(r.hx+back);else lz=sg*(r.hz+back);
  const x=r.x+lx*r.c+lz*r.s,z=r.z-lx*r.s+lz*r.c,y=r.y0+frac*(r.y1-r.y0)+2;
  const d=new THREE.Vector3(r.x-x,0,r.z-z).normalize();
  st.pos.set(x,y,z);st.vel.copy(d).multiplyScalar(spd);st.quat.setFromUnitVectors(new THREE.Vector3(0,0,-1),d);st.onGround=false;st.gearDown=false;st.gearPos=0;st.w.set(0,0,0);st.airTime=5;
  let n=0;while(!st.crashed&&n<400){K.stepFrame(1/60,false,true);n++;}
  return {crashed:st.crashed,why:st.crashReason,imp:K.strImp(),cfx:K.cfx()};}"""

async def main():
    os.makedirs(out, exist_ok=True)
    srv, url = serve() if not ROOT else serve_root(ROOT)
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'})
        await pg.evaluate(f"()=>{{{K}.setSkill('pilot');{K}.setRadioOn&&{K}.setRadioOn(false);{K}.WST.off=true;{K}.fxHide({'true' if NOFX else 'false'});}}")
        info = {}
        for tod in TODS:
            await pg.evaluate(f"()=>{K}.setTOD('{tod}')")
            for c in SEL:
                t, sel, ax, sg, back, frac, spd, views = CASES[c]
                r = await pg.evaluate(FLY, [t, sel, ax, sg, back, frac, spd])
                if 'err' in r or not r['imp']:
                    print('  no impact', c, r); continue
                info[f'{c}_{tod}'] = {'why': r['why'], 'cfx': r['cfx'], 'imp': r['imp']}
                # let it play out in sim time, rendering now and then so the GPU keeps up
                n = int(SECS * 30)
                await pg.evaluate("(n)=>{const K=window.__kgeu;for(let i=0;i<n;i++)K.stepFrame(1/30,false,i%15!==14);}", n)
                im = r['imp']
                for vi, (dist, up, side, lup) in enumerate(views):
                    await pg.evaluate("""([p,n,dist,up,side,lup])=>{const K=window.__kgeu;const t1=[n[2],0,-n[0]];
                      K.freeCam({w:true,p:[p[0]+n[0]*dist+t1[0]*side,p[1]+up,p[2]+n[2]*dist+t1[2]*side],t:[p[0],p[1]+lup,p[2]],fov:55});
                      for(let i=0;i<3;i++)K.stepFrame(1/30);document.getElementById('crashTop').classList.remove('on');document.getElementById('crash').classList.remove('on');
                      document.getElementById('bigFlash').style.visibility='hidden';}""", [im['p'], im['n'], dist, up, side, lup])
                    await pg.wait_for_timeout(250)
                    fn = os.path.join(out, f'{c}_{tod}_{vi}.png')
                    await pg.screenshot(path=fn, timeout=120000)
                    print('  wrote', fn)
                await pg.evaluate(f"()=>{K}.freeCam(null)")
        json.dump(info, open(os.path.join(out, 'info.json'), 'w'), indent=1)
        print('errors:', [e for e in pg.errs][:5])
        await b.close()
    srv.shutdown()

def serve_root(root):
    import http.server, threading, functools
    from harness import Quiet
    h = functools.partial(Quiet, directory=root)
    s = http.server.ThreadingHTTPServer(('127.0.0.1', 0), h)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    return s, f'http://127.0.0.1:{s.server_address[1]}/index.html'

asyncio.run(main())
