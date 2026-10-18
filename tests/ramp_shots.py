# Runways item 8: a gate start and a pushback at Sky Harbor and Haneda (the 737, chase view, Hard), the tug at the
# nose mid push and the aircraft on the taxilane after it, plus Easy's taxi route line after the taxi clearance, and the
# rough ground stop (the Cessna off Glendale's apron at taxi speed, no crash, the stuck caption).
#   .venv/bin/python tests/ramp_shots.py [out_dir]     (default overnight-screenshots/runways_ramp)
import asyncio, os, sys, json
from playwright.async_api import async_playwright
from harness import serve, launch, page, IPHONE_15

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), '..', 'overnight-screenshots', 'runways_ramp')
HARD = {'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'}
EASY = {'kgeuOnboard': 'rookie', 'kgeuTut': '1', 'kgeuCoach': '3'}
CAM_JS = "(m)=>{const K=window.__kgeu;let k=0;while(K.camMode()!==m&&k++<6)K.cycleCam();}"
START_JS = "([t,b])=>{const K=window.__kgeu;K.setTOD('day');if(K.setWX){try{K.setWX('clear');}catch(e){}}K.pick(t);K.pickBase(b);K.start('ramp');}"
STEP_JS = "([secs])=>{const K=window.__kgeu,s=K.state(),t0=s.time;let n=0;while(s.time-t0<secs&&n++<4000)K.stepFrame(0.25,false,true);K.snapCam();for(let i=0;i<4;i++)K.stepFrame(1/30);return {t:+(s.time-t0).toFixed(1),x:Math.round(s.pos.x),z:Math.round(s.pos.z),PB:{on:K.PB.on,ph:K.PB.ph,done:K.PB.done},PR:{gate:K.PR.gate,on:K.PR.on},near:K.traffic().filter(o=>o.onGround&&Math.hypot(o.x-s.pos.x,o.z-s.pos.z)<400).map(o=>o.cs+':'+o.state),atc:(document.getElementById('atc')||{}).textContent||'',txr:K.txr?K.txr():null,stuck:!!s.stuck,crashed:!!s.crashed,toast:(document.getElementById('toast')||{}).textContent||''};}"

async def shot(pg, name):
    path = os.path.join(OUT, name + '.png'); await pg.screenshot(path=path); print('  ', path)

async def gate_and_push(b, url, region, base):
    storage = dict(HARD)
    if region != 'az': storage['kgeuRegion'] = region
    pg = await page(b, url, vp=IPHONE_15, storage=storage)
    if region != 'az':
        await pg.wait_for_function("()=>window.__kgeu.WORLD.ready||window.__kgeu.WORLD.err", timeout=60000); await pg.wait_for_timeout(1500)
    await pg.evaluate(START_JS, ['b737', base]); await pg.wait_for_timeout(1500)
    await pg.evaluate(CAM_JS, 0)
    r = await pg.evaluate(STEP_JS, [3]); print('  gate', json.dumps(r)); await shot(pg, f'{base}_gate')
    ok = await pg.evaluate("()=>window.__kgeu.pushback()"); print('  pushback()', ok)
    r = await pg.evaluate(STEP_JS, [14]); print('  mid', json.dumps(r)); await shot(pg, f'{base}_push_mid')
    r = await pg.evaluate(STEP_JS, [40]); print('  after', json.dumps(r)); await shot(pg, f'{base}_push_after')
    r = await pg.evaluate(STEP_JS, [60]); print('  later', json.dumps(r)); await shot(pg, f'{base}_push_later')
    print('  errs', pg.errs[:3]); await pg.context.close()

async def easy_route(b, url):
    pg = await page(b, url, vp=IPHONE_15, storage=EASY)
    await pg.evaluate(START_JS, ['cessna', 'kgeu']); await pg.wait_for_timeout(1500)
    await pg.evaluate(CAM_JS, 0)
    r = await pg.evaluate(STEP_JS, [12]); print('  easy route', json.dumps(r)); await shot(pg, 'kgeu_easy_route')
    print('  errs', pg.errs[:3]); await pg.context.close()

async def rough(b, url):
    pg = await page(b, url, vp=IPHONE_15, storage=HARD)
    await pg.evaluate(START_JS, ['cessna', 'kgeu']); await pg.wait_for_timeout(1500)
    await pg.evaluate(CAM_JS, 0)
    r = await pg.evaluate("""()=>{const K=window.__kgeu,s=K.state();const x0=s.pos.x,z0=s.pos.z;let t=null;
      for(let r=50;r<=400&&!t;r+=25)for(let a=0;a<8&&!t;a++){const x=x0+Math.cos(a*Math.PI/4)*r,z=z0+Math.sin(a*Math.PI/4)*r;if(!K.isPaved(x,z))t={x:x,z:z};}
      const dx=t.x-x0,dz=t.z-z0,L=Math.hypot(dx,dz);s.vel.set(dx/L*6,0,dz/L*6);s.onGround=true;s.throttle=s.power=0;
      const t0=s.time;let n=0;while(s.time-t0<40&&n++<2000){K.stepFrame(0.25,false,true);if(s.crashed)break;}
      K.snapCam();for(let i=0;i<4;i++)K.stepFrame(1/30);
      return {paved:K.isPaved(s.pos.x,s.pos.z),v:+Math.hypot(s.vel.x,s.vel.z).toFixed(2),stuck:!!s.stuck,crashed:!!s.crashed,toast:(document.getElementById('toast')||{}).textContent||''};}""")
    print('  rough', json.dumps(r)); await shot(pg, 'kgeu_rough_stuck')
    print('  errs', pg.errs[:3]); await pg.context.close()

async def main():
    os.makedirs(OUT, exist_ok=True)
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        print('== Sky Harbor'); await gate_and_push(b, url, 'az', 'phx')
        print('== Haneda'); await gate_and_push(b, url, 'rjtt', 'rjtt')
        print('== Easy route line'); await easy_route(b, url)
        print('== rough ground'); await rough(b, url)
        await b.close()
    srv.shutdown()

asyncio.run(main())
