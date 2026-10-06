# Phone3 item 5: Easy mode layout. Start a flight in Easy with a real tap and the stick, throttle and
# buttons must be on screen on the first frame. Then the iPhone home screen trip: the page is hidden for
# 10 s, and while it is away iOS leaves a stale transitional viewport behind (an offset top, a short height,
# a canvas of the wrong size) and the size change of a rotation arrives with no resize event at all. When
# the page shows again (visibilitychange, pageshow) the canvas must equal the viewport, the UI root must
# fill it from the top, and the controls must be visible and hit by a finger. Then a real rotation to
# portrait and back. Easy and Hard. iPhone 844x390.
# Run: .venv/bin/python tests/resume_check.py
import asyncio, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, finger, IPHONE_15
ok = Checks()
K = 'window.__kgeu'

STATE = """()=>{const K=window.__kgeu,R=K.R3(),c=R.renderer.domElement,cr=c.getBoundingClientRect(),u=document.getElementById('uiroot').getBoundingClientRect(),pr=R.renderer.getPixelRatio();
  const vv=getComputedStyle(document.documentElement),vars=[parseFloat(vv.getPropertyValue('--vvt')),parseFloat(vv.getPropertyValue('--vvw')),parseFloat(vv.getPropertyValue('--vvh'))];
  const shown=id=>{const e=document.getElementById(id);if(!e)return false;for(let n=e;n&&n.nodeType===1;n=n.parentElement){const s=getComputedStyle(n);if(s.display==='none'||s.visibility==='hidden'||parseFloat(s.opacity)<0.05)return false;}const r=e.getBoundingClientRect();return r.width>10&&r.height>10;};
  const vis=id=>{const e=document.getElementById(id);if(!e)return false;for(let n=e;n&&n.nodeType===1;n=n.parentElement){const s=getComputedStyle(n);if(s.display==='none'||s.visibility==='hidden'||parseFloat(s.opacity)<0.05)return false;}
    const r=e.getBoundingClientRect();if(r.width<10||r.height<10)return false;const h=document.elementFromPoint(r.left+r.width/2,r.top+r.height/2);return !!h&&(h===e||e.contains(h));};
  const btns=[...document.querySelectorAll('#dock button')].filter(b=>!b.hidden&&b.getBoundingClientRect().width>40).length;
  return {W:innerWidth,H:innerHeight,cw:c.width,ch:c.height,pr:pr,css:[cr.left,cr.top,cr.width,cr.height].map(Math.round),ui:[u.left,u.top,u.width,u.height].map(Math.round),
    aspect:+R.camera.aspect.toFixed(3),stick:vis('stickZone'),thr:vis('thr'),btns:btns,hud:shown('hud'),vars:vars,paused:K.paused(),scroll:scrollY}}"""

def good(s):
    return (s['css'] == [0, 0, s['W'], s['H']] and (s['paused'] or s['ui'] == [0, 0, s['W'], s['H']]) and s['vars'] == [0, s['W'], s['H']] and abs(s['cw'] - round(s['W'] * s['pr'])) <= 1
            and abs(s['ch'] - round(s['H'] * s['pr'])) <= 1 and abs(s['aspect'] - s['W'] / s['H']) < 0.01 and s['scroll'] == 0)

def controls(s):
    return s['stick'] and s['thr'] and s['btns'] >= 2 and s['hud']

HIDE = """()=>{Object.defineProperty(document,'hidden',{configurable:true,get:()=>true});Object.defineProperty(document,'visibilityState',{configurable:true,get:()=>'hidden'});
  document.dispatchEvent(new Event('visibilitychange'));window.dispatchEvent(new Event('pagehide'));
  window.__kgeu.stepFrame(1/60,false,true);   // a hidden page gets no animation frames: hold the loop
  // and the next size change comes with no resize event
  window.__swallow=e=>e.stopImmediatePropagation();window.addEventListener('resize',window.__swallow,true);
  if(window.visualViewport)visualViewport.addEventListener('resize',window.__swallow,true);}"""
# what iOS leaves behind when it comes back: a transitional viewport and a canvas from the other orientation
STALE = """()=>{const r=document.documentElement.style;r.setProperty('--vvt','64px');r.setProperty('--vvh','0px');
  window.__kgeu.R3().renderer.setSize(390,844,false);}"""
SHOW = """()=>{window.removeEventListener('resize',window.__swallow,true);if(window.visualViewport)visualViewport.removeEventListener('resize',window.__swallow,true);
  delete document.hidden;delete document.visibilityState;
  document.dispatchEvent(new Event('visibilitychange'));window.dispatchEvent(new PageTransitionEvent('pageshow',{persisted:true}));
  window.__kgeu.stepFrame(0,true);}"""

async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        for skill in ('rookie', 'pilot'):
            M = 'Easy' if skill == 'rookie' else 'Hard'
            pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': skill, 'kgeuTut': '1', 'kgeuCoach': '3'})
            await pg.wait_for_function(f"()=>{K}&&{K}.WORLD.ready", timeout=30000)
            for rep in range(3):
                await pg.evaluate(f"()=>{{{K}.pickPos('runway');{K}.openFly()}}"); await pg.wait_for_timeout(400)
                await finger(pg, '#bGo')
                await pg.evaluate(f"()=>{K}.stepFrame(1/30,false,true)")
                s = await pg.evaluate(STATE)
                ok(f'{M} start {rep + 1}: stick, throttle, buttons and HUD on the first frame', controls(s), s)
                await pg.evaluate(f"()=>{K}.stepFrame(0,true)")
                await pg.evaluate(f"()=>{K}.openMenu()"); await pg.wait_for_timeout(300)
            await pg.evaluate(f"()=>{{{K}.pickPos('final');{K}.openFly()}}"); await pg.wait_for_timeout(400)
            await finger(pg, '#bGo'); await pg.wait_for_timeout(800)
            s = await pg.evaluate(STATE)
            ok(f'{M}: flying, canvas equals the viewport', good(s) and controls(s), s)
            # the home screen trip: hidden 10 s, the phone rotated and back meanwhile (no resize event)
            await pg.evaluate(HIDE)
            await pg.set_viewport_size({'width': 390, 'height': 844}); await pg.wait_for_timeout(300)
            await pg.set_viewport_size(IPHONE_15)
            await pg.wait_for_timeout(10000)
            await pg.evaluate(STALE)
            bad = await pg.evaluate(STATE)
            ok(f'{M}: while away the layout really is stale (the test bites)', not good(bad), bad)
            await pg.evaluate(SHOW); await pg.wait_for_timeout(1500)
            s = await pg.evaluate(STATE)
            ok(f'{M}: back from the home screen: canvas equals the viewport, nothing pushed down', good(s), s)
            ok(f'{M}: back from the home screen: the pause sheet is up (the app was hidden mid flight)', await pg.evaluate(f"()=>{K}.paused()"))
            await pg.evaluate("()=>document.getElementById('pResume').click()"); await pg.wait_for_timeout(500)
            s = await pg.evaluate(STATE)
            ok(f'{M}: resumed: controls visible and under the finger', controls(s), s)
            # a real rotation to portrait and back
            await pg.evaluate("()=>document.body.classList.add('portraitok')")
            await pg.set_viewport_size({'width': 390, 'height': 844})
            await pg.evaluate("()=>window.dispatchEvent(new Event('orientationchange'))"); await pg.wait_for_timeout(1500)
            s = await pg.evaluate(STATE)
            ok(f'{M}: portrait: canvas equals the viewport, controls visible', good(s) and controls(s), s)
            await pg.set_viewport_size(IPHONE_15)
            await pg.evaluate("()=>window.dispatchEvent(new Event('orientationchange'))"); await pg.wait_for_timeout(1500)
            s = await pg.evaluate(STATE)
            ok(f'{M}: landscape again: canvas equals the viewport, controls visible', good(s) and controls(s), s)
            ok(f'{M}: no page errors', not pg.errs, pg.errs[:3])
            await pg.context.close()
        await b.close()
    srv.shutdown()
    sys.exit(ok.done('resume_check'))

asyncio.run(main())
