# Arsenal balance numbers (not a pass/fail check): how often each missile kills against the real bandit AI, by mode,
# range and aspect, and how often the Hard bandits' long shot hits us with no reaction, with flares only, and with a BREAK
# as it closes. Seeded trials, our jet flying straight and level at 400 kt, 15,000 ft. Prints a table; --json writes it.
# Run: .venv/bin/python tests/arsenal_balance.py [--n 30] [--json /tmp/arsenal_balance.json]
import asyncio, json, sys, argparse
from playwright.async_api import async_playwright
from harness import serve, launch, page, IPHONE_15
K = "window.__kgeu"

# one trial in the page: a fresh wave of one bandit d metres away (head: flying at us, else away from us), then our
# missile of kind at it (with a lock assumed), stepped in 0.05 s until it ends: 1 a kill, 0 a miss
TRIAL = """([kind,d,head,seed])=>{const K=window.__kgeu,D=K.DF,s=K.state(),T=D.test;
  D.gap=0;D.kc=0;D.kcB=null;document.body.classList.remove('dfKc');for(const m of D.msl)if(m.on){m.on=false;m.mesh.g.visible=false;}
  D.waves=[1,2,3,4,9];D.t=90;D.out=0;D.hits=0;T.noBanditFire=true;T.hold=false;D.wave=1+(seed%4);T.wave(1);   // waves[] past 4: a wave 4 kill is not the run's win
  s.pos.set(D.C.x,(15000-1071)/3.28084+1.5,D.C.z);s.vel.set(0,0,-206);s.quat.setFromEuler(new THREE.Euler(0,0,0,'YXZ'));s.w.set(0,0,0);
  const b=D.bandits[0],n=new THREE.Vector3(0,0,-1);b.p.copy(s.pos).addScaledVector(n,d);b.hdg=head?Math.PI:0;b.gam=0;b.bank=0;b.spd=230;b.state='TURN';b.st=0;b.cool=0;
  b.v.set(Math.sin(b.hdg),0,-Math.cos(b.hdg)).multiplyScalar(b.spd);
  const k0=D.kills;K.dfShoot(b,kind);
  if(!D.on)return -1;
  for(let i=0;i<700;i++){K.stepFrame(0.05,false,true);if(D.kills>k0)return 1;if(!D.msl.some(m=>m.on&&!m.foe))return 0;}
  return 0;}"""
# the long shot at us from 7 nm head on: react 'none' | 'flare' (FLARES at 4 s and 2 s to go) | 'break' (BREAK at 2,600 m)
LONG = """([react,seed])=>{const K=window.__kgeu,D=K.DF,s=K.state(),T=D.test;
  D.gap=0;D.kc=0;for(const m of D.msl)if(m.on){m.on=false;m.mesh.g.visible=false;}
  D.waves=[1,2,3,4,9];D.t=90;D.out=0;T.noBanditFire=true;T.hold=true;T.lr=1;D.wave=2;T.wave(1);D.hits=0;D.inv=0;D.brk=0;D.brkCd=0;D.flares=30;
  s.pos.set(D.C.x,(15000-1071)/3.28084+1.5,D.C.z);s.vel.set(0,0,-206);s.quat.setFromEuler(new THREE.Euler(0,0,0,'YXZ'));s.w.set(0,0,0);
  const b=D.bandits[0],n=new THREE.Vector3(0,0,-1);b.p.copy(s.pos).addScaledVector(n,7*1852);b.hdg=Math.PI;b.gam=0;b.bank=0;b.spd=230;b.state='TURN';b.st=0;b.cool=0;
  b.v.set(Math.sin(b.hdg),0,-Math.cos(b.hdg)).multiplyScalar(b.spd);
  if(!D.on)return -1;K.dfLaunch(b,'emrm');T.noBanditFire=true;let f4=false,f2=false,br=false;
  for(let i=0;i<600;i++){K.stepFrame(0.05,false,true);const m=D.msl.find(m=>m.on&&m.foe);if(D.hits>0)return 1;if(!m||m.lost)return 0;
    const R=m.p.distanceTo(s.pos),vc=m.v.length()+206,tgo=R/vc;
    if(react==='flare'){if(!f4&&tgo<4){f4=true;K.dfPFlare(false);}if(!f2&&tgo<2){f2=true;K.dfPFlare(false);}}
    if(react==='break'&&!br&&R<2600){br=true;K.dfBreak();}}
  return 0;}"""

async def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--n', type=int, default=30); ap.add_argument('--json'); a = ap.parse_args()
    srv, url = serve(); out = {}
    async with async_playwright() as p:
        b = await launch(p)
        for mode in ('pilot', 'rookie'):
            pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': mode, 'kgeuTut': '1', 'kgeuType': 'f16'})
            await pg.evaluate(f"()=>{{const K={K};K.DF.test.noBrief=true;K.DF.test.seed=4242;K.dfStart();}}")   # seeded: the same dice every run
            await pg.evaluate("()=>{const K=window.__kgeu;for(let i=0;i<5;i++)K.stepFrame(0.1,false,true);}")
            name = 'Hard' if mode == 'pilot' else 'Easy'
            for kind, d, head, lab in (('srm', 1.5 * 1852, True, 'SRM 1.5 nm head on'), ('srm', 1 * 1852, False, 'SRM 1 nm from behind'),
                                       ('srm', 3 * 1852, False, 'SRM 3 nm from behind'),
                                       ('mrm', 3 * 1852, True, 'MRM 3 nm head on'), ('mrm', 6 * 1852, True, 'MRM 6 nm head on'),
                                       ('mrm', 9 * 1852, True, 'MRM 9 nm head on'), ('mrm', 4 * 1852, False, 'MRM 4 nm from behind')):
                hits = 0
                for i in range(a.n):
                    r = await pg.evaluate(TRIAL, [kind, d, head, 1000 + i]); assert r >= 0, 'the run ended mid batch'; hits += r
                out[f'{name} {lab}'] = hits / a.n
                print(f'  {name:4} {lab:24} kill {hits}/{a.n} = {hits / a.n:.0%}', flush=True)
            if mode == 'pilot':
                for react in ('none', 'flare', 'break'):
                    hits = 0
                    for i in range(a.n):
                        r = await pg.evaluate(LONG, [react, 2000 + i]); assert r >= 0, 'the run ended mid batch'; hits += r
                    out[f'Hard long shot, {react}'] = hits / a.n
                    print(f'  Hard long shot at us, react {react:6} hit {hits}/{a.n} = {hits / a.n:.0%}', flush=True)
            if pg.errs: print('  console errors:', pg.errs[:3])
            await pg.context.close()
        await b.close()
    srv.shutdown()
    if a.json: json.dump(out, open(a.json, 'w'), indent=1)
    return 0

if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
