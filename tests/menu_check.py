# Feature 6: the menu. Every screen fits an iPhone in landscape with no scrolling,
# every tap target is at least 44 px, safe areas are respected, the FLY flow goes
# aircraft -> where and when -> GO and starts exactly what was picked, and the
# keyboard chart never shows on a touch device. Run: .venv/bin/python tests/menu_check.py
import asyncio, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, finger
ok = Checks()
SCREENS = ['sHome', 'sFly1', 'sFly2', 'sFly3', 'sMis', 'sSchool', 'sArc', 'sSet', 'sHelp']
FIT = """(id)=>{const s=document.getElementById(id);const W=innerWidth,H=innerHeight;const bad=[];
  if(s.scrollHeight>s.clientHeight+1||s.scrollWidth>s.clientWidth+1)bad.push('scrolls '+s.scrollWidth+'x'+s.scrollHeight);
  const cur=document.querySelector('.acard.sel');
  s.querySelectorAll('button,input,.chip').forEach(e=>{const r=e.getBoundingClientRect();if(!r.width||getComputedStyle(e).visibility==='hidden')return;
    if(e.closest('.acard')&&e.closest('.acard')!==cur)return;       // the other cards wait off screen by design
    if(r.left<-0.5||r.top<-0.5||r.right>W+0.5||r.bottom>H+0.5)bad.push('off screen '+(e.id||e.textContent.trim().slice(0,16)));
    if(e.matches('button')&&(r.width<43.5||r.height<43.5))bad.push('small '+(e.id||e.textContent.trim().slice(0,16))+' '+Math.round(r.width)+'x'+Math.round(r.height));});
  const hits=[...s.querySelectorAll('button')].filter(e=>e.getBoundingClientRect().width).map(e=>[e,e.getBoundingClientRect()]);
  for(let i=0;i<hits.length;i++)for(let j=i+1;j<hits.length;j++){const a=hits[i][1],b=hits[j][1];
    if(hits[i][0].contains(hits[j][0])||hits[j][0].contains(hits[i][0]))continue;
    if(Math.min(a.right,b.right)-Math.max(a.left,b.left)>1&&Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top)>1)bad.push('overlap '+hits[i][0].textContent.trim().slice(0,10)+' / '+hits[j][0].textContent.trim().slice(0,10));}
  return bad;}"""

async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        for vp in ({'width': 667, 'height': 375}, {'width': 844, 'height': 390}, {'width': 932, 'height': 430}):
            pg = await page(b, url, vp=vp, storage={'kgeuOnboard': 'rookie', 'kgeuTut': '1', 'kgeuCoach': '3'})
            tag = f"{vp['width']}x{vp['height']}"
            for sid in SCREENS:
                await pg.evaluate(f"()=>{{window.__kgeu.openFly();window.__kgeu.nav('{sid}')}}"); await pg.wait_for_timeout(250)
                bad = await pg.evaluate(FIT, sid)
                ok(f'{tag} {sid} fits with no scrolling, 44 px targets, no overlaps', not bad, bad[:4])
            if vp['width'] == 667:
                home = await pg.evaluate("""()=>{window.__kgeu.nav('sHome',true);return [...document.querySelectorAll('#sHome button')].map(b=>b.id)}""")
                ok('home has only FLY, MISSIONS, ARCADE plus Records and Settings', sorted(home) == sorted(['hRec','hSet','hFly','hMis','hArc']), home)
                keys = await pg.evaluate("()=>{window.__kgeu.nav('sHelp');const k=document.querySelector('.keys');return getComputedStyle(k).display}")
                ok('keyboard and controller chart is hidden on a touch device', keys == 'none', keys)
                # the whole FLY flow by finger
                await pg.evaluate("()=>{window.__kgeu.pick('cessna');window.__kgeu.nav('sHome',true)}"); await pg.wait_for_timeout(200)
                await finger(pg, '#hFly'); await pg.wait_for_timeout(600)
                ok('FLY opens the aircraft carousel', await pg.evaluate("()=>window.__kgeu.curScr()") == 'sFly1')
                await finger(pg, '#carR'); await pg.wait_for_timeout(500); await finger(pg, '#carR'); await pg.wait_for_timeout(500)
                t = await pg.evaluate("()=>window.__kgeu.prefs().type")
                ok('the arrows move through the aircraft', t == 'f16', t)
                # swipe back one card
                r = await pg.evaluate("()=>{const r=document.getElementById('car').getBoundingClientRect();return [r.x,r.y,r.width,r.height]}")
                y = r[1] + r[3]*0.35
                await pg.evaluate("""([x0,x1,y])=>{const c=document.getElementById('car');const ev=(t,x)=>c.dispatchEvent(new PointerEvent(t,{pointerId:3,clientX:x,clientY:y,bubbles:true}));
                  ev('pointerdown',x0);for(let i=1;i<=6;i++)ev('pointermove',x0+(x1-x0)*i/6);ev('pointerup',x1);}""", [r[0]+r[2]*0.3, r[0]+r[2]*0.8, y])
                await pg.wait_for_timeout(700)
                t = await pg.evaluate("()=>window.__kgeu.prefs().type")
                ok('swiping right goes back one aircraft', t == 'alpha', t)
                await pg.evaluate("()=>document.querySelector('.acard[data-t=\"f16\"]').click()"); await pg.wait_for_timeout(500)
                await finger(pg, '.acard[data-t="f16"] .story'); await pg.wait_for_timeout(300)
                ok('Story opens the tail number history', await pg.evaluate("()=>document.getElementById('storyOv').classList.contains('on')&&document.getElementById('storyT').textContent.length>40"))
                await finger(pg, '#storyX'); await pg.wait_for_timeout(200)
                await finger(pg, '.acard[data-t="f16"] .pickme'); await pg.wait_for_timeout(300)
                ok('Next goes to where and when', await pg.evaluate("()=>window.__kgeu.curScr()") == 'sFly2')
                await finger(pg, '.pick[data-b="luke"]'); await finger(pg, '.pick[data-tod="sunset"]'); await finger(pg, '.pick[data-pos="final"]')
                await finger(pg, '#f2Next'); await pg.wait_for_timeout(300)
                line = await pg.evaluate("()=>document.getElementById('sumLine').textContent")
                ok('GO screen has the one line summary', line == 'F-16 at Luke AFB, sunset, on 3 mile final', line)
                await finger(pg, '.scr.on .back'); await pg.wait_for_timeout(200)
                ok('back returns one step', await pg.evaluate("()=>window.__kgeu.curScr()") == 'sFly2')
                await finger(pg, '#f2Next'); await pg.wait_for_timeout(200)
                await finger(pg, '#bGo'); await pg.wait_for_timeout(1500)
                s = await pg.evaluate("()=>{const s=window.__kgeu.state();return {type:s.type,base:s.base,mode:s.mode,menu:document.getElementById('menu').classList.contains('on'),agl:Math.round(s.agl)}}")
                ok('GO flies exactly what was picked', s['type'] == 'f16' and s['base'] == 'luke' and s['mode'] == 'final' and not s['menu'] and s['agl'] > 100, s)
                ok('time of day took effect', await pg.evaluate("()=>window.__kgeu.TOD().id") == 'sunset')
                # pause -> settings -> back returns to the pause sheet
                await finger(pg, '#bPause'); await pg.wait_for_timeout(300)
                await finger(pg, '#pSet'); await pg.wait_for_timeout(300)
                ok('settings open from the pause sheet', await pg.evaluate("()=>window.__kgeu.curScr()") == 'sSet')
                await finger(pg, '#sSet .back'); await pg.wait_for_timeout(300)
                ok('back from settings returns to the pause sheet', await pg.evaluate("()=>document.getElementById('pauseOv').classList.contains('on')&&!document.getElementById('menu').classList.contains('on')"))
                await finger(pg, '#pMenu'); await pg.wait_for_timeout(300)
                await finger(pg, '#hMis'); await pg.wait_for_timeout(300)
                n = await pg.evaluate("()=>[...document.querySelectorAll('#misCards .mcard')].map(c=>c.dataset.m)")
                ok('missions are cards: short field, dash, flight school', n == ['short', 'dash', 'school'], n)
                await finger(pg, '#misCards [data-m="short"]'); await pg.wait_for_timeout(1200)
                s = await pg.evaluate("()=>({t:window.__kgeu.state().type,saved:window.__kgeu.prefs().type,kind:window.__kgeu.MISS.kind})")
                ok('a mission card starts it without changing the saved aircraft', s == {'t': 'c130', 'saved': 'f16', 'kind': 'short'}, s)
                await pg.evaluate("()=>window.__kgeu.openMenu()"); await pg.wait_for_timeout(200)
                await finger(pg, '#hRec'); await pg.wait_for_timeout(300)
                ok('Records opens from the corner icon', await pg.evaluate("()=>document.getElementById('recOv').classList.contains('on')"))
            ok(f'{tag} no page errors', not pg.errs, pg.errs[:3])
            await pg.context.close()
        await b.close()
    sys.exit(ok.done('menu_check'))
asyncio.run(main())
