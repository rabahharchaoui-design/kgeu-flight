# Graphics item 2: quality tiers and dynamic resolution. tierFromSignals table, the Settings > Graphics chips (override,
# pixel ratio, saved across a reload, the Auto label), the dynFeed state machine, Settings shots at 844x390 and 568x320
# to /tmp/gfx2/. Run: .venv/bin/python tests/gfx_tier_check.py
import asyncio, sys, os
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, finger, IPHONE_15

K = 'window.__kgeu'
OUT = '/tmp/gfx2'
ok = Checks()
IOS = 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1'
AND = 'Mozilla/5.0 (Linux; Android 13; SM-A135F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Mobile Safari/537.36'
TABLE = [
    ('iPhone 12', dict(gpu='Apple GPU', w=390, h=844, dpr=3, ua=IOS), 'medium'),
    ('iPhone 14 Pro', dict(gpu='Apple GPU', w=393, h=852, dpr=3, ua=IOS), 'high'),
    ('iPhone 15 Pro Max', dict(gpu='Apple GPU', w=430, h=932, dpr=3, ua=IOS), 'high'),
    ('iPhone SE 2', dict(gpu='Apple GPU', w=375, h=667, dpr=2, ua=IOS), 'low'),
    ('iPhone 13 mini', dict(gpu='Apple GPU', w=375, h=812, dpr=3, ua=IOS), 'medium'),
    ('desktop RTX 3060', dict(gpu='ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 (0x00002504) Direct3D11 vs_5_0 ps_5_0, D3D11)', w=1920, h=1080, dpr=1), 'high'),
    ('Mali-G52 412x915', dict(gpu='Mali-G52', w=412, h=915, dpr=2.6, ua=AND), 'low'),
    ('Adreno 730', dict(gpu='Adreno (TM) 730', w=412, h=915, dpr=3, ua=AND), 'high'),
    ('Adreno 618', dict(gpu='Adreno (TM) 618', w=412, h=915, dpr=3, ua=AND), 'medium'),
    ('SwiftShader', dict(gpu='Google SwiftShader', w=1280, h=800, dpr=1), 'low'),
    ('webdriver', dict(gpu='Google SwiftShader', w=390, h=844, dpr=3, webdriver=True), 'medium'),
    ('iPhone 14 Pro, slow bench demotes', dict(gpu='Apple GPU', w=393, h=852, dpr=3, ua=IOS, benchMs=20), 'medium'),
    ('iPhone 12, fast bench never promotes', dict(gpu='Apple GPU', w=390, h=844, dpr=3, ua=IOS, benchMs=0.5), 'medium'),
    ('iPhone SE, slow bench stays low', dict(gpu='Apple GPU', w=375, h=667, dpr=2, ua=IOS, benchMs=50), 'low'),
]

FEED = """([n,avg,low,dt])=>{const G=window.__kgeu;let s;for(let i=0;i<n;i++)s=G.dynFeed(avg,low,dt);return s;}"""

async def feed(pg, secs, avg, low, dt=1/60):
    return await pg.evaluate(FEED, [int(round(secs / dt)), avg, low, dt])

async def setshot(pg, name):
    await pg.evaluate(f"()=>{{{K}.openMenu();{K}.tabGo('sSet');}}"); await pg.wait_for_timeout(400)
    await pg.screenshot(path=os.path.join(OUT, name))

# the grid scrolls inside itself when a column has more rows than room (Callsign is a swipe away at 390 px tall):
# every row must sit inside the grid's box once scrolled to, and no chips row may be cut sideways
CLIP = """()=>{const G=document.querySelector('#sSet .setGrid'),bad=[];G.scrollTop=1e4;const g=G.getBoundingClientRect();
  document.querySelectorAll('#sSet .srow').forEach(r=>{const b=r.getBoundingClientRect(),c=r.querySelector('.chips');
    const nm=(r.querySelector('span')||{}).textContent||'?';
    if(c&&c.scrollWidth>c.clientWidth+1)bad.push(nm+' chips overflow '+c.scrollWidth+'>'+c.clientWidth);
    c&&c.querySelectorAll('button').forEach(x=>{const q=x.getBoundingClientRect();if(q.right>g.right+1||q.right>innerWidth)bad.push(nm+' button past the edge');});
    r.scrollIntoView({block:'nearest'});const v=r.getBoundingClientRect();if(v.bottom>g.bottom+1||v.top<g.top-1)bad.push(nm+' row not reachable');});
  G.scrollTop=0;if(document.querySelector('.gfxSeg').closest('.srow').getBoundingClientRect().bottom>g.bottom+1)bad.push('Graphics row hidden at rest');
  return bad;}"""

async def main():
    os.makedirs(OUT, exist_ok=True)
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'rookie', 'kgeuTut': '1'})
        for name, sig, want in TABLE:
            got = await pg.evaluate(f"(s)=>{K}.tierFromSignals(s)", sig)
            ok(f'tier: {name} -> {want}', got == want, got)
        g = await pg.evaluate(f"()=>({{tier:{K}.GFX.tier,auto:{K}.GFX.auto,dyn:{K}.GFX.dyn,scale:{K}.GFX.scale,pr:{K}.R3().renderer.getPixelRatio(),fx:typeof {K}.GFX.on,rank:{K}.GFX.rank()}})")
        ok('Playwright: auto medium, dyn off, scale 1, pixel ratio 1.5 (unchanged)', g['tier'] == 'medium' and g['auto'] == 'medium' and g['dyn'] is False and g['scale'] == 1 and abs(g['pr'] - 1.5) < 1e-6, g)
        fx = await pg.evaluate(f"()=>{{const G={K}.GFX;G.FX.__t='high';const a=G.on('__t');G.FX.__t='low';const c=G.on('__t');delete G.FX.__t;return [a,c,G.rank('high'),G.rank('low')];}}")
        ok('GFX.on: medium tier refuses a high effect, takes a low one', fx == [False, True, 2, 0], fx)

        # Settings > Graphics
        await setshot(pg, 'settings_844x390.png')
        lab = await pg.evaluate("()=>document.querySelector('.gfxSeg [data-tier=auto]').textContent")
        ok('Auto chip reads "Auto (Medium)"', '(Medium)' in lab, lab)
        sel = await pg.evaluate("()=>[...document.querySelectorAll('.gfxSeg .sel')].map(e=>e.dataset.tier)")
        ok('Auto is the selected chip by default', sel == ['auto'], sel)
        clip = await pg.evaluate(CLIP)
        ok('844x390: Graphics row in view, every row reachable, no chips clipped', not clip, clip)
        hook = await pg.evaluate(f"()=>{{window.__hk=[];return 1;}}")
        await finger(pg, '.gfxSeg [data-tier=low]'); await pg.wait_for_timeout(200)
        s = await pg.evaluate(f"()=>({{tier:{K}.GFX.tier,pr:{K}.R3().renderer.getPixelRatio(),ls:localStorage.getItem('kgeuTier'),sel:[...document.querySelectorAll('.gfxSeg .sel')].map(e=>e.dataset.tier)}})")
        ok('tap Low: tier low, pixel ratio 1, kgeuTier saved, chip selected', s == {'tier': 'low', 'pr': 1, 'ls': 'low', 'sel': ['low']}, s)
        await finger(pg, '.gfxSeg [data-tier=high]'); await pg.wait_for_timeout(200)
        pr = await pg.evaluate(f"()=>{K}.R3().renderer.getPixelRatio()")
        ok('tap High: pixel ratio 2', pr == 2, pr)
        await finger(pg, '.gfxSeg [data-tier=low]'); await pg.wait_for_timeout(200)
        await pg.reload(); await pg.wait_for_function('()=>window.__kgeu', timeout=30000)
        await pg.wait_for_function("()=>{const s=document.getElementById('splash');return !s||s.classList.contains('gone')}", timeout=30000)
        s = await pg.evaluate(f"()=>({{tier:{K}.GFX.tier,ov:{K}.GFX.override,pr:{K}.R3().renderer.getPixelRatio()}})")
        ok('Low survives a reload', s == {'tier': 'low', 'ov': 'low', 'pr': 1}, s)
        await pg.evaluate(f"()=>{K}.GFX.setTier('auto')")
        s = await pg.evaluate(f"()=>({{tier:{K}.GFX.tier,pr:{K}.R3().renderer.getPixelRatio(),ls:localStorage.getItem('kgeuTier')}})")
        ok('back to Auto: medium, 1.5, saved', s == {'tier': 'medium', 'pr': 1.5, 'ls': 'auto'}, s)

        # graphics item 6: the sun shadow cascades follow the tier (Low: no light and no shadow map at all)
        CSM = f"()=>{K}.csm()"
        await pg.evaluate(f"()=>{K}.GFX.setTier('low')"); c = await pg.evaluate(CSM)
        ok('Low: no cascade light in the scene, the shadow map off, the sun the one directional light',
           c['n'] == 0 and c['lights'] == 0 and c['inScene'] == 0 and c['enabled'] is False and c['dirLights'] == 1, c)
        await pg.evaluate(f"()=>{K}.GFX.setTier('medium')"); c = await pg.evaluate(CSM)
        ok('Medium: 2 cascades, 1,024 near and 512 mid', c['n'] == 2 and c['inScene'] == 2 and c['enabled'] is True and c['sizes'] == [1024, 512] and c['dirLights'] == 3, c)
        await pg.evaluate(f"()=>{K}.GFX.setTier('high')"); c = await pg.evaluate(CSM)
        ok('High: 3 cascades at 1,024', c['n'] == 3 and c['inScene'] == 3 and c['enabled'] is True and c['sizes'] == [1024, 1024, 1024] and c['dirLights'] == 4, c)
        await pg.evaluate(f"()=>{K}.GFX.setTier('auto')"); c = await pg.evaluate(CSM)
        ok('back to Auto: the 2 Medium cascades again', c['n'] == 2 and c['inScene'] == 2 and c['dirLights'] == 3, c)

        # dynFeed state machine: in flight (the live loop puts the scale back to 1 on the menu; dyn is off under Playwright)
        await pg.evaluate(f"()=>{{const K={K};K.pick('cessna');K.start('runway');}}"); await pg.wait_for_timeout(600)
        c = await pg.evaluate(f"()=>{{const K={K};K.setTOD('day');return K.csm();}}"); await pg.wait_for_timeout(600)
        c2 = await pg.evaluate(CSM)
        ok('Medium on the runway by day: near and mid cascades drawn, the maps redrawn', (c2['act'] & 3) == 3 and c2['renders'] > c['renders'], [c['renders'], c2])
        await pg.evaluate(f"()=>{{{K}.GFX.setScale(1);{K}.GFX.dynReset(true);}}")
        r = await feed(pg, 3.1, 50, 50)
        # graphics item 3: with the post chain on (medium) the canvas keeps 1.5 and the chain's scene target takes the scale
        pr = await pg.evaluate(f"()=>[{K}.R3().renderer.getPixelRatio(),{K}.GFX.scenePR(),{K}.GFX.post]")
        ok('dyn: 1% low 50 for 3.1 s steps to 0.85 (scene pixel ratio 1.5 x 0.85, canvas 1.5 under the post chain)',
           r == 0.85 and abs(pr[1] - 1.275) < 1e-6 and abs(pr[0] - (1.5 if pr[2] else 1.275)) < 1e-6, [r, pr])
        r = await feed(pg, 3.1, 50, 50)
        ok('dyn: inside the 5 s cooldown nothing moves', r == 0.85, r)
        r = await feed(pg, 2.0, 50, 50)
        ok('dyn: still low after the cooldown steps to 0.7', r == 0.7, r)
        r = await feed(pg, 5.0, 50, 50)
        ok('dyn: 0.7 is the floor', r == 0.7, r)
        r = await feed(pg, 10.1, 60, 58)
        ok('dyn: avg 60 1% low 58 for 10.1 s steps back up to 0.85', r == 0.85, r)
        await pg.evaluate(f"()=>{{{K}.GFX.setScale(1);{K}.GFX.dynReset(true);}}")
        r = await feed(pg, 2.9, 50, 50)
        ok('dyn: under 3 s of low frames, no change', r == 1, r)
        await pg.evaluate(f"()=>{{{K}.GFX.setScale(1);{K}.GFX.dynReset(true);}}")
        r = await feed(pg, 6.0, 50, 50, dt=0.3)
        ok('dyn: 300 ms frames are ignored', r == 1, r)
        await pg.evaluate(f"()=>{{{K}.GFX.setScale(1);{K}.GFX.dynReset(false);}}")
        r = await feed(pg, 2.9, 50, 50)
        ok('dyn: the first 3 s after a start count for nothing', r == 1 and await pg.evaluate(f"()=>{K}.GFX.dynS.lowT") == 0, r)
        r = await feed(pg, 3.2, 50, 50)
        ok('dyn: after the grace, 3 s of low frames step down', r == 0.85, r)
        # graphics item 8, the battery guard: 20 s straight at the 0.7 floor with the 1% low under 50 (not in the first 10 s
        # of a flight) drops one tier for the session, the scale back to 1, one toast a session; kgeuTier never written
        TF = """([n,avg,low,dt])=>{const G=window.__kgeu.GFX;let s;for(let i=0;i<n;i++)s=G.thermalFeed(avg,low,dt);return s;}"""
        async def tfeed(secs, low, dt=1/60):
            return await pg.evaluate(TF, [int(round(secs / dt)), 30, low, dt])
        ls0 = await pg.evaluate("()=>localStorage.getItem('kgeuTier')")
        await pg.evaluate(f"()=>{{const G={K}.GFX;G.setScale(0.7);G.thermalReset();document.getElementById('toast').classList.remove('on');document.getElementById('toast').textContent='';}}")
        r = await tfeed(9.9, 40)
        ok('thermal: the first 10 s of a flight count for nothing', r == 'medium' and await pg.evaluate(f"()=>{K}.GFX.thermS.lowT") == 0, r)
        r = await tfeed(19.9, 40)
        ok('thermal: 19.9 s at 0.7 under 50, still Medium', r == 'medium', r)
        r = await tfeed(0.3, 40, dt=0.3)
        ok('thermal: a 300 ms frame is ignored', r == 'medium', r)
        r = await tfeed(0.2, 40)
        s = await pg.evaluate(f"()=>({{tier:{K}.GFX.tier,scale:{K}.GFX.scale,ov:{K}.GFX.override,ls:localStorage.getItem('kgeuTier'),toasts:{K}.GFX.thermS.toasts,drops:{K}.GFX.thermS.drops,txt:document.getElementById('toast').textContent,pr:{K}.R3().renderer.getPixelRatio(),csm:{K}.csm().n}})")
        ok('thermal: 20 s at 0.7 under 50 drops Medium to Low, scale 1.0, Low applied (pixel ratio 1, no cascades), one toast',
           r == 'low' and s['tier'] == 'low' and s['scale'] == 1 and s['toasts'] == 1 and s['drops'] == 1 and s['txt'] == 'Graphics set to Low to keep things smooth' and s['pr'] == 1 and s['csm'] == 0, s)
        ok('thermal: the saved kgeuTier and the Settings pick untouched', s['ls'] == ls0 and s['ov'] == 'auto', [ls0, s])
        await pg.evaluate(f"()=>{{const G={K}.GFX;G.setScale(0.7);G.thermalReset();}}")
        r = await tfeed(40, 30)
        ok('thermal: on Low nothing happens', r == 'low' and await pg.evaluate(f"()=>{K}.GFX.thermS.drops") == 1, r)
        # a second episode (the session tier put back to Medium by hand): drops again, no second toast
        await pg.evaluate(f"()=>{{const G={K}.GFX;G.tier='medium';G.applyTier();G.setScale(0.7);G.thermalReset();document.getElementById('toast').classList.remove('on');document.getElementById('toast').textContent='';}}")
        r = await tfeed(10, 55)
        r = await tfeed(25, 55)
        ok('thermal: a 1% low of 55 at 0.7 is not a thermal episode', r == 'medium', r)
        await pg.evaluate(f"()=>{{{K}.GFX.setScale(0.85);}}")
        r = await tfeed(25, 30)
        ok('thermal: under 50 at 0.85 (not the floor) is not one either', r == 'medium', r)
        await pg.evaluate(f"()=>{{{K}.GFX.setScale(0.7);}}")
        r = await tfeed(20.1, 30)
        s = await pg.evaluate(f"()=>({{toasts:{K}.GFX.thermS.toasts,drops:{K}.GFX.thermS.drops,txt:document.getElementById('toast').textContent,ls:localStorage.getItem('kgeuTier')}})")
        ok('thermal: a second episode drops again without a second toast', r == 'low' and s['drops'] == 2 and s['toasts'] == 1 and s['txt'] == '' and s['ls'] == ls0, s)
        await pg.evaluate(f"()=>{K}.GFX.setTier('auto')")
        # the menu puts it back to 1
        await pg.evaluate(f"()=>{{{K}.openMenu();}}"); await pg.wait_for_timeout(300)
        s = await pg.evaluate(f"()=>[{K}.GFX.scale,{K}.R3().renderer.getPixelRatio()]")
        ok('menu: scale back to 1.0', s == [1, 1.5], s)
        # the pill prefix
        await pg.evaluate("()=>document.getElementById('oFps').click()"); await pg.wait_for_timeout(500)
        txt = await pg.evaluate("()=>document.getElementById('fpsPill').textContent")
        ok('FPS pill gains the tier and scale prefix', txt.startswith('M 1.00 · ') and 'fps' in txt, txt)
        await pg.evaluate("()=>document.getElementById('oFps').click()")
        ok('no console errors (844x390)', not pg.errs, pg.errs[:3])
        await pg.context.close()

        pg = await page(b, url, vp={'width': 568, 'height': 320}, storage={'kgeuOnboard': 'rookie', 'kgeuTut': '1'})
        await setshot(pg, 'settings_568x320.png')
        s = await pg.evaluate("""()=>{const r=document.querySelector('.gfxSeg').closest('.srow');r.scrollIntoView({block:'center'});
          const c=r.querySelector('.chips'),g=document.querySelector('#sSet .setGrid').getBoundingClientRect(),b=r.getBoundingClientRect();
          return {fit:c.scrollWidth<=c.clientWidth+1,inside:b.top>=g.top-1&&b.bottom<=g.bottom+1,right:Math.max(...[...c.children].map(x=>x.getBoundingClientRect().right))<=innerWidth};}""")
        await pg.wait_for_timeout(200)
        await pg.screenshot(path=os.path.join(OUT, 'settings_568x320_graphics.png'))
        ok('568x320: the Graphics row scrolls into view, chips not clipped', s == {'fit': True, 'inside': True, 'right': True}, s)
        ok('no console errors (568x320)', not pg.errs, pg.errs[:3])
        await b.close()
    srv.shutdown()
    return ok.done('gfx tier check')

if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
