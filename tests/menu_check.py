# Feature 6: the menu. Every screen fits an iPhone in landscape with no scrolling,
# every tap target is at least 44 px, safe areas are respected, the FLY flow goes
# aircraft -> where and when -> GO and starts exactly what was picked, and the
# keyboard chart never shows on a touch device. Run: .venv/bin/python tests/menu_check.py
import asyncio, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, finger
ok = Checks()
CAR = ['cessna','alpha','f16','reaper','mq9b','c130']
CAR_AFTER_10 = CAR[(CAR.index('c130') + 10) % 6]
SCREENS = ['sHome', 'sFly', 'sMis', 'sSchool', 'sArc', 'sSet', 'sHelp']
FIT = """(id)=>{const s=document.getElementById(id);const W=innerWidth,H=innerHeight;const bad=[];
  if(s.scrollHeight>s.clientHeight+1||s.scrollWidth>s.clientWidth+1)bad.push('scrolls '+s.scrollWidth+'x'+s.scrollHeight);
  // the location row scrolls sideways (4.6b): a card counts by the part its row shows, a card scrolled out of sight not at all
  const RC=e=>{const r=e.getBoundingClientRect(),L=e.closest('.locs');if(!L)return r;const q=L.getBoundingClientRect(),x0=Math.max(r.left,q.left),x1=Math.max(x0,Math.min(r.right,q.right));
    return {left:x0,right:x1,top:r.top,bottom:r.bottom,width:x1-x0,height:r.height};};
  s.querySelectorAll('button,input,.chip').forEach(e=>{const r0=e.getBoundingClientRect(),r=RC(e);if(r.width<0.5||getComputedStyle(e).visibility==='hidden')return;
    if(r.left<-0.5||r.top<-0.5||r.right>W+0.5||r.bottom>H+0.5)bad.push('off screen '+(e.id||e.textContent.trim().slice(0,16)));
    if(e.matches('button')&&(r0.width<43.5||r0.height<43.5))bad.push('small '+(e.id||e.textContent.trim().slice(0,16))+' '+Math.round(r0.width)+'x'+Math.round(r0.height));});
  const hits=[...s.querySelectorAll('button')].filter(e=>RC(e).width>=0.5).map(e=>[e,RC(e)]);
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
                ok('home has only FLY, FLIGHT SCHOOL, MISSIONS, ARCADE, LEADERBOARDS plus Records and Settings', sorted(home) == sorted(['hRec','hSet','hFly','hSch','hMis','hArc','hLb']), home)
                keys = await pg.evaluate("()=>{window.__kgeu.nav('sHelp');const k=document.querySelector('.keys');return getComputedStyle(k).display}")
                ok('keyboard and controller chart is hidden on a touch device', keys == 'none', keys)
                # two taps from opening the app to flying: FLY, then GO
                await pg.evaluate("()=>{window.__kgeu.pick('cessna');window.__kgeu.pickBase('kgeu');window.__kgeu.setTOD('day');window.__kgeu.pickPos('runway');window.__kgeu.nav('sHome',true)}"); await pg.wait_for_timeout(200)
                await finger(pg, '#hFly'); await pg.wait_for_timeout(600)
                ok('FLY goes straight to the one fly screen', await pg.evaluate("()=>window.__kgeu.curScr()") == 'sFly')
                one = await pg.evaluate("()=>{const s=document.getElementById('sFly');return [!!s.querySelector('#carMain .cwin'),s.querySelectorAll('.pick[data-b]').length,s.querySelectorAll('.pick[data-tod]').length,s.querySelectorAll('.pick[data-pos]').length,!!s.querySelector('#bGo')]}")
                ok('carousel, location (five airports, 4.6b), time, start and GO are all on that one screen', one == [True, 5, 4, 4, True], one)   # start: runway, ramp, 1 mi final, 3 mi final
                await finger(pg, '#bGo'); await pg.wait_for_timeout(1400)
                s1 = await pg.evaluate("()=>{const s=window.__kgeu.state();return [s.type,s.base,s.mode,document.getElementById('menu').classList.contains('on')]}")
                ok('GO flies the saved picks (2 taps from home)', s1 == ['cessna', 'kgeu', 'runway', False], s1)
                # looping carousel
                await pg.evaluate("()=>window.__kgeu.openFly()"); await pg.wait_for_timeout(400)
                seen = []
                for _ in range(8):
                    await finger(pg, '#carMain .arrow.r'); await pg.wait_for_timeout(350)
                    seen.append(await pg.evaluate("()=>window.__kgeu.prefs().type"))
                ok('right arrow loops past the last aircraft back to the first', seen[:7] == ['alpha','f16','reaper','mq9b','c130','cessna','alpha'], seen)
                for _ in range(3):
                    await finger(pg, '#carMain .arrow.l'); await pg.wait_for_timeout(350)
                t = await pg.evaluate("()=>window.__kgeu.prefs().type")
                ok('left arrow loops backwards too', t == 'mq9b' or t == 'c130', t)
                await pg.evaluate("()=>{window.__kgeu.pick('cessna');window.__kgeu.openFly()}"); await pg.wait_for_timeout(300)
                r = await pg.evaluate("()=>{const r=document.querySelector('#carMain .cwin').getBoundingClientRect();return [r.x,r.y,r.width,r.height]}")
                y = r[1] + r[3]*0.3
                async def swipe(x0, x1):
                    await pg.evaluate("""([x0,x1,y])=>{const c=document.querySelector('#carMain .cwin');const ev=(t,x)=>c.dispatchEvent(new PointerEvent(t,{pointerId:3,clientX:x,clientY:y,bubbles:true}));
                      ev('pointerdown',x0);for(let i=1;i<=6;i++)ev('pointermove',x0+(x1-x0)*i/6);ev('pointerup',x1);}""", [x0, x1, y])
                    await pg.wait_for_timeout(500)
                await swipe(r[0]+r[2]*0.8, r[0]+r[2]*0.3)
                ok('swiping left goes to the next aircraft', await pg.evaluate("()=>window.__kgeu.prefs().type") == 'alpha')
                await swipe(r[0]+r[2]*0.3, r[0]+r[2]*0.8); await swipe(r[0]+r[2]*0.3, r[0]+r[2]*0.8)
                ok('swiping right past the first wraps to the last', await pg.evaluate("()=>window.__kgeu.prefs().type") == 'c130')
                for _ in range(10): await swipe(r[0]+r[2]*0.8, r[0]+r[2]*0.3)
                ok('keeps swiping forever', await pg.evaluate("()=>window.__kgeu.prefs().type") == CAR_AFTER_10)
                await finger(pg, '#carMain .story'); await pg.wait_for_timeout(300)
                ok('Story opens the tail number history', await pg.evaluate("()=>document.getElementById('storyOv').classList.contains('on')&&document.getElementById('storyT').textContent.length>40"))
                await finger(pg, '#storyX'); await pg.wait_for_timeout(200)
                await pg.evaluate("()=>window.__kgeu.pick('f16')")
                await finger(pg, '#sFly .pick[data-b="luke"]'); await finger(pg, '#sFly .pick[data-tod="sunset"]'); await finger(pg, '#sFly .pick[data-pos="final"]')
                line = await pg.evaluate("()=>document.getElementById('sumLine').textContent")
                ok('the header summarises the picks', line == 'F-16 at Luke AFB, sunset, segment on 3 mile final', line)
                await finger(pg, '#bGo'); await pg.wait_for_timeout(1500)
                s = await pg.evaluate("()=>{const s=window.__kgeu.state();return {type:s.type,base:s.base,mode:s.mode,menu:document.getElementById('menu').classList.contains('on'),agl:Math.round(s.agl)}}")
                ok('GO flies exactly what was picked', s['type'] == 'f16' and s['base'] == 'luke' and s['mode'] == 'final' and not s['menu'] and s['agl'] > 100, s)
                ok('time of day took effect', await pg.evaluate("()=>window.__kgeu.TOD().id") == 'sunset')
                # change flight from the pause sheet
                await finger(pg, '#bPause'); await pg.wait_for_timeout(400)
                bad = await pg.evaluate(FIT.replace("document.getElementById(id)", "document.getElementById(id).querySelector('.pz')"), 'pauseOv')
                ok('pause sheet with Change flight fits, 44 px targets, no overlaps', not bad, bad[:4])
                ok('pause aircraft row marks the current aircraft', await pg.evaluate("()=>document.querySelector('#pAc .pick.sel').dataset.t==='f16'"))
                await finger(pg, '#pAc .pick[data-t="alpha"]'); await pg.wait_for_timeout(400)
                await finger(pg, '#pauseOv .pick[data-b="kgeu"]'); await finger(pg, '#pauseOv .pick[data-tod="night"]'); await finger(pg, '#pauseOv .pick[data-pos="ramp"]')
                await finger(pg, '#pApply'); await pg.wait_for_timeout(1500)
                s = await pg.evaluate("()=>{const s=window.__kgeu.state();return [s.type,s.base,s.mode,window.__kgeu.TOD().id,window.__kgeu.paused(),document.getElementById('menu').classList.contains('on')]}")
                ok('Apply restarts at once with the new aircraft, base, time and start, no main menu', s == ['alpha', 'kgeu', 'ramp', 'night', False, False], s)
                sync = await pg.evaluate("()=>{window.__kgeu.openFly();return [window.__kgeu.prefs().type,document.querySelector('#sFly .pick[data-tod=night]').classList.contains('sel'),document.querySelector('#sFly .pick[data-pos=ramp]').classList.contains('sel'),document.querySelector('#carMain .nm').textContent.startsWith('Pipistrel')]}")
                ok('the main menu shows the same choices', sync == ['alpha', True, True, True], sync)
                await finger(pg, '.scr.on .back'); await pg.wait_for_timeout(200)
                await finger(pg, '#hMis'); await pg.wait_for_timeout(300)
                n = await pg.evaluate("()=>[...document.querySelectorAll('#misCards .mcard')].map(c=>[c.dataset.m,!!c.querySelector('svg.ico'),!!c.querySelector('.stars')])")
                ok('mission cards have an icon and stars', [x[0] for x in n] == ['daily', 'short', 'dash'] and all(x[1] and x[2] for x in n), n)
                await finger(pg, '#misCards [data-m="short"]'); await pg.wait_for_timeout(1200)
                s = await pg.evaluate("()=>({t:window.__kgeu.state().type,saved:window.__kgeu.prefs().type,kind:window.__kgeu.MISS.kind})")
                ok('a mission card starts it without changing the saved aircraft', s == {'t': 'c130', 'saved': 'alpha', 'kind': 'short'}, s)
                await pg.evaluate("()=>window.__kgeu.openMenu()"); await pg.wait_for_timeout(200)
                await finger(pg, '#hRec'); await pg.wait_for_timeout(300)
                ok('Records opens from the corner icon', await pg.evaluate("()=>document.getElementById('recOv').classList.contains('on')"))
            ok(f'{tag} no page errors', not pg.errs, pg.errs[:3])
            await pg.context.close()
        await b.close()
    sys.exit(ok.done('menu_check'))
asyncio.run(main())
