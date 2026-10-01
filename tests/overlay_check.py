# Phone2 item 4: no overlay burn in. Every mission, arcade game and lesson is flown, ended through
# the real UI (the pause sheet's Main menu, the result cards, the crash card) and then the main menu
# (sHome) and the FLY screen (sFly, the see-through showroom) must show nothing from that flight:
# no mission card, jump lights, DZ hint / chip / chevron, destination chip, lesson panel, tutorial
# arrow, ticker strip, sensor HUD, target marks, look pad, crash card, badges or result sheets, and
# none of its 3D (drop zone smoke, panels, run in line and gates, the guide hoops, the ghost, the
# pallet). Then free flight from the menu must come up with its own HUD and nothing of the mission.
# Also the one path that keeps the flight: pause, a menu screen from the sheet (Missions), Back,
# Resume: the airdrop must still be intact. Hard, then Easy. iPhone 844x390, real touch taps.
# Run: .venv/bin/python tests/overlay_check.py
import asyncio, os, sys
from playwright.async_api import async_playwright
from harness import serve, page, Checks, IPHONE_15, ROOT
ok = Checks()
K = 'window.__kgeu'
SHOTS = os.path.join(ROOT, 'overnight-screenshots', 'phone2', 'item4')

# what is still showing: DOM overlays (really visible, not just classed), the 3D left overs and
# the mode state that would bring them back. fly=true: in free flight, where the flight HUD,
# warnings, toasts, the tower and the ticker are allowed.
LEFT = """(fly)=>{const K=window.__kgeu,$=id=>document.getElementById(id),out=[];
  const vis=e=>{if(!e||e.hidden)return false;for(let n=e;n&&n.nodeType===1;n=n.parentElement){const s=getComputedStyle(n);
      if(s.display==='none'||s.visibility==='hidden'||parseFloat(s.opacity)<0.02)return false;}
    const r=e.getBoundingClientRect();return r.width>0&&r.height>0&&r.right>0&&r.bottom>0&&r.left<innerWidth&&r.top<innerHeight;};
  document.querySelectorAll('.overlay.on').forEach(e=>{if(e.id!=='menu'||fly)out.push('overlay #'+e.id);});
  const ids=['miss','jumpLt','dzHint','dzMark','dzArrow','hDest','lesson','tutArrow','sensorHud','lookPad','crash','crashTop','bDrop'];
  if(!fly)ids.push('warn','toast','atc','sideToast','tk','tkCtl','sixpack');
  ids.forEach(id=>{if(vis($(id)))out.push('#'+id+' '+($(id).textContent||'').trim().slice(0,28));});
  document.querySelectorAll('#tgtMarks .on').forEach(()=>out.push('target mark'));
  document.querySelectorAll('#badges .badge').forEach(e=>{if(e.classList.contains('on')||vis(e))out.push('badge #'+e.id);});
  if(!fly&&!$('hDest').hidden)out.push('hDest not hidden');
  const d=K.dest();if(d&&!fly)out.push('DEST '+JSON.stringify(d));
  if(fly&&d&&(d.name==='Drop zone'||d.apt))out.push('mission DEST '+JSON.stringify(d));
  if(K.DZ.on)out.push('DZ.on');if(K.DZ.g&&K.DZ.g.visible)out.push('DZ 3D visible');
  if(K.GUIDE.on||K.GUIDE.hoops.some(h=>h.visible))out.push('guide hoops');
  if(K.MISS.on)out.push('MISS.on '+K.MISS.kind);if(K.MISS.pallet)out.push('pallet');
  if(K.ARC.on)out.push('ARC.on '+K.ARC.kind);if(K.LES.on)out.push('LES.on '+K.LES.on);if(K.STRIKE.active)out.push('STRIKE.active');
  if(K.LB&&K.LB.E.ghost)out.push('ghost');
  if(K.ticker().open)out.push('ticker controls open');
  ['lookOn','crashOn','sensorOn'].forEach(c=>{if(document.body.classList.contains(c))out.push('body.'+c);});
  if(!fly&&document.body.classList.contains('hasDest'))out.push('body.hasDest');
  return out;}"""

HUD = """()=>{const vis=e=>{if(!e)return false;for(let n=e;n&&n.nodeType===1;n=n.parentElement){const s=getComputedStyle(n);
    if(s.display==='none'||s.visibility==='hidden'||parseFloat(s.opacity)<0.02)return false;}const r=e.getBoundingClientRect();return r.width>0&&r.height>0;};
  return ['hud','map','stickZone','thr','bPause'].filter(id=>!vis(document.getElementById(id)));}"""

VIS_IDS = """(ids)=>ids.filter(id=>{const e=document.getElementById(id);if(!e||e.hidden)return false;
  for(let n=e;n&&n.nodeType===1;n=n.parentElement){const s=getComputedStyle(n);if(s.display==='none'||s.visibility==='hidden'||parseFloat(s.opacity)<0.02)return false;}
  const r=e.getBoundingClientRect();return r.width>0&&r.height>0;})"""

async def tap(pg, sel, wait=500):
    r = await pg.evaluate("(s)=>{const e=document.querySelector(s);if(!e)return null;const r=e.getBoundingClientRect();"
                          "if(!r.width||!r.height)return null;const x=r.x+r.width/2,y=r.y+r.height/2,h=document.elementFromPoint(x,y);"
                          "return [x,y,!!h&&(e===h||e.contains(h)),h&&(h.id||h.className)]}", sel)
    if not r: raise RuntimeError('not on screen: ' + sel)
    if not r[2]: raise RuntimeError(f'covered: {sel} by {r[3]}')
    await pg.touchscreen.tap(r[0], r[1])
    await pg.wait_for_timeout(wait)

async def run_s(pg, sec):
    # a few seconds of flight without waiting on the ~3 fps headless loop
    await pg.evaluate(f"(n)=>{{const K={K};for(let i=0;i<n;i++)K.stepFrame(0.05,false,true);K.stepFrame(0,true)}}", int(sec * 20))

# each mode: how to start it and how to get it to something worth leaving
async def m_drop(pg):
    await pg.evaluate(f"()=>{{const K={K};K.pick('c130');K.start('drop')}}"); await pg.wait_for_timeout(900)
    await run_s(pg, 7)   # the hint holds 6 s, the jump lights and chevron come up
async def m_drop_pallet(pg):
    await pg.evaluate(f"()=>{{const K={K};K.pick('c130');K.start('drop')}}"); await pg.wait_for_timeout(900)
    await pg.evaluate(f"()=>{{const K={K},s=K.state();s.pos.x=K.DROPZ.x+260;s.pos.z=K.DROPZ.z}}")
    await run_s(pg, 1)
    await pg.evaluate(f"()=>{{const K={K};K.missDrop();K.missTick(600,1/60)}}")   # the bundle is still under canopy
async def m_short(pg):
    await pg.evaluate(f"()=>{{const K={K};K.pick('c130');K.start('short')}}"); await pg.wait_for_timeout(900); await run_s(pg, 2)
async def m_dash(pg):
    await pg.evaluate(f"()=>{{const K={K};K.pick('f16');K.start('runway','luke')}}"); await pg.wait_for_timeout(900); await run_s(pg, 2)
async def m_range(pg):
    await pg.evaluate(f"()=>{K}.mission('range')"); await pg.wait_for_timeout(900); await run_s(pg, 3)
def m_arc(kind):
    async def f(pg):
        await pg.evaluate(f"()=>{{const K={K};K.pick('cessna');K.arcStart('{kind}')}}"); await pg.wait_for_timeout(900); await run_s(pg, 2)
    return f
def m_les(id):
    async def f(pg):
        await pg.evaluate(f"()=>{K}.startLesson('{id}')"); await pg.wait_for_timeout(900); await run_s(pg, 2)
    return f
async def m_free(pg):
    await pg.evaluate(f"()=>{{const K={K};K.pick('cessna');K.pickBase('kgeu');K.pickPos('runway');K.start('runway')}}"); await pg.wait_for_timeout(900); await run_s(pg, 2)

MODES = [('airdrop', m_drop), ('airdrop pallet in the air', m_drop_pallet), ('short field', m_short), ('F-16 dash', m_dash),
         ('strike range', m_range), ('landing challenge', m_arc('landing')), ('1 mile challenge', m_arc('landing1')),
         ('daily', m_arc('daily'))] + [(f'lesson {l}', m_les(l)) for l in ('first', 'steep', 'slow', 'stall', 'engine', 'pattern')] + [('free flight', m_free)]

EASY = ('airdrop', 'short field', 'strike range', 'landing challenge', 'daily', 'lesson first', 'lesson pattern', 'free flight')

async def on(pg, sel): return await pg.evaluate("(s)=>document.querySelector(s).classList.contains('on')", sel)

async def check_menu(pg, tag, name, shot):
    await pg.wait_for_timeout(700)   # toast and tower fade out
    scr = await pg.evaluate(f"()=>{K}.curScr()")
    ok(f'{tag} {name}: on the main menu', scr == 'sHome' and await on(pg, '#menu'), scr)
    left = await pg.evaluate(LEFT, False)
    ok(f'{tag} {name}: main menu shows nothing of the flight', not left, left)
    if shot: await pg.screenshot(path=f'{SHOTS}/{shot}_home.png')
    await tap(pg, '#hFly', 900)
    left = await pg.evaluate(LEFT, False)
    ok(f'{tag} {name}: FLY screen (see through) shows nothing of the flight', await pg.evaluate(f"()=>{K}.curScr()") == 'sFly' and not left, left)
    if shot: await pg.screenshot(path=f'{SHOTS}/{shot}_fly.png')

async def check_free(pg, tag, name, from_menu=True):
    if from_menu:
        await tap(pg, '#bGo', 1200)
    ok(f'{tag} {name}: free flight is running', await pg.evaluate(f"()=>{K}.running()&&!{K}.paused()&&!document.getElementById('menu').classList.contains('on')"))
    await run_s(pg, 1.5); await pg.wait_for_timeout(300)
    left = await pg.evaluate(LEFT, True)
    ok(f'{tag} {name}: free flight has none of the mission overlays', not left, left)
    miss = await pg.evaluate(HUD)
    ok(f'{tag} {name}: free flight HUD, map, stick, throttle and pause show', not miss, miss)

async def main():
    os.makedirs(SHOTS, exist_ok=True)
    srv, url = serve()
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader'])
        for skill, tag in (('pilot', 'Hard'), ('rookie', 'Easy')):
            pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': skill, 'kgeuTut': '1', 'kgeuCoach': '3'})
            await pg.evaluate(f"()=>{K}.setSkill('{skill}')")
            await pg.touchscreen.tap(422, 6); await pg.wait_for_timeout(300)

            # Easy: the modes whose overlays differ in Easy (DZ chip, route, guide hoops, lesson arrow)
            only = sys.argv[1] if len(sys.argv) > 1 else None   # e.g. airdrop: just the modes with that in their name
            for name, go in (MODES if tag == 'Hard' else [m for m in MODES if m[0] in EASY]):
                if only and only not in name: continue
                try:
                    await go(pg)
                    await tap(pg, '#bPause', 500); await tap(pg, '#pMenu', 600)
                except Exception as e:
                    ok(f'{tag} {name}: ended through pause, Main menu', False, str(e)[:120]); continue
                await check_menu(pg, tag, name, f"{tag.lower()}_{name.replace(' ', '_')}")
                await check_free(pg, tag, name)

            # the airdrop result card: each of its buttons leaves nothing of the drop behind
            for btn, want in (('#mFree', 'continue'), ('#mRetry', 'drop')):
                await pg.evaluate(f"()=>{{const K={K};K.pick('c130');K.start('drop')}}"); await pg.wait_for_timeout(700)
                await pg.evaluate(f"()=>{{const K={K},s=K.state();s.pos.x=K.DROPZ.x+260;s.pos.z=K.DROPZ.z}}"); await run_s(pg, 1)
                await pg.evaluate(f"()=>{{const K={K};K.missDrop();K.missTick(4000,1/60)}}"); await pg.wait_for_timeout(400)
                if not ok(f'{tag} airdrop result card is up', await on(pg, '#missOv')): continue
                await tap(pg, btn, 1200)
                left = await pg.evaluate(LEFT, True)
                s = await pg.evaluate(f"()=>({{mode:{K}.state().mode,kind:{K}.MISS.kind,res:!!{K}.MISS.result,pallet:!!{K}.MISS.pallet}})")
                if want == 'continue':
                    # CONTINUE keeps flying where the C-130 is, the mission and its overlays gone (the NEW RECORD
                    # badge earned by that drop may still be fading out over the flight: it is not a mission overlay)
                    left = [x for x in left if x != 'badge #banner']
                    ok(f'{tag} airdrop card {btn}: keeps flying, nothing of the drop', not s['res'] and not s['pallet'] and not left, [s, left])
                    await tap(pg, '#bPause', 500); await tap(pg, '#pMenu', 600)
                    await check_menu(pg, tag, 'airdrop card then Main menu', f"{tag.lower()}_airdrop_card_menu" if tag == 'Hard' else None)
                else:
                    E = skill == 'rookie'
                    st = await pg.evaluate(f"()=>({{dz:{K}.DZ.on,g:{K}.DZ.g.visible,res:!!{K}.MISS.result,pallet:!!{K}.MISS.pallet,hint:document.getElementById('dzHint').classList.contains('on'),card:document.getElementById('missOv').classList.contains('on')}})")
                    ok(f'{tag} airdrop card {btn}: a fresh drop (DZ back, no result, no pallet)', s['kind'] == 'drop' and st['dz'] and st['g'] and st['hint'] and not st['res'] and not st['pallet'] and not st['card'], st)

            # the airdrop card's MAIN MENU
            await pg.evaluate(f"()=>{{const K={K};K.pick('c130');K.start('drop')}}"); await pg.wait_for_timeout(700)
            await pg.evaluate(f"()=>{{const K={K},s=K.state();s.pos.x=K.DROPZ.x+260;s.pos.z=K.DROPZ.z}}"); await run_s(pg, 1)
            await pg.evaluate(f"()=>{{const K={K};K.missDrop();K.missTick(4000,1/60)}}"); await pg.wait_for_timeout(400)
            if ok(f'{tag} airdrop result card is up (for MAIN MENU)', await on(pg, '#missOv')):
                await tap(pg, '#mMenu', 700)
                await check_menu(pg, tag, 'airdrop card MAIN MENU', None)
                await check_free(pg, tag, 'after the airdrop card MAIN MENU')

            # a crash: the crash card's MENU
            await m_free(pg)
            await pg.evaluate(f"()=>{K}.crashNow('Test crash')")
            got = False
            for _ in range(40):
                await pg.evaluate(f"()=>{K}.stepFrame(0.1,false,true)")
                if await on(pg, '#crash'): got = True; break
            await pg.evaluate(f"()=>{K}.stepFrame(0,true)")
            if ok(f'{tag} crash card is up', got):
                # it slides up (slowly in the headless browser)
                await pg.wait_for_function("()=>document.getElementById('cMenu').getBoundingClientRect().bottom<=innerHeight", timeout=8000)
                try:
                    await tap(pg, '#cMenu', 700)
                    await check_menu(pg, tag, 'crash card MENU', f"{tag.lower()}_crash" if tag == 'Hard' else None)
                    await check_free(pg, tag, 'after a crash')
                except Exception as e: ok(f'{tag} crash card MENU', False, str(e)[:120])

            # a lesson ended from its own panel (End): the panel and arrow go, free flight goes on
            await m_les('steep')(pg)
            try:
                await tap(pg, '#lesQuit', 500)
                left = await pg.evaluate(LEFT, True)
                ok(f'{tag} lesson End: the panel goes', not left, left)
            except Exception as e: ok(f'{tag} lesson End button', False, str(e)[:120])

            # the path that keeps the flight: pause, Missions from the sheet, Back, Resume
            await pg.evaluate(f"()=>{{const K={K};K.pick('c130');K.start('drop')}}"); await pg.wait_for_timeout(900); await run_s(pg, 2)
            before = await pg.evaluate(f"()=>({{on:{K}.MISS.on,dz:{K}.DZ.on,g:{K}.DZ.g.visible,dest:{K}.dest()}})")
            up = await pg.evaluate(VIS_IDS, ['dzHint', 'dzMark', 'dzArrow', 'jumpLt', 'miss', 'lookPad', 'bDrop'])
            ok(f'{tag} airdrop in flight: its overlays are up before the pause', len(up) >= 2, up)
            try:
                await tap(pg, '#bPause', 500); await tap(pg, '#pMis', 700)
                vis = await pg.evaluate(VIS_IDS, ['dzHint', 'dzMark', 'dzArrow', 'jumpLt', 'miss', 'hDest', 'lookPad', 'bDrop'])
                ok(f'{tag} pause, Missions: no drop overlay over the menu screen', not vis, vis)
                if tag == 'Hard': await pg.screenshot(path=f'{SHOTS}/hard_pause_missions.png')
                await tap(pg, '#sMis .back', 600)
                ok(f'{tag} Back returns to the pause sheet', await on(pg, '#pauseOv') and not await on(pg, '#menu'))
                await tap(pg, '#pResume', 600)
                after = await pg.evaluate(f"()=>({{on:{K}.MISS.on,kind:{K}.MISS.kind,dz:{K}.DZ.on,g:{K}.DZ.g.visible,dest:{K}.dest(),run:{K}.running()&&!{K}.paused()}})")
                ok(f'{tag} Resume: the airdrop is intact (mission, DZ, its route)', after['on'] and after['kind'] == 'drop' and after['dz'] and after['g']
                   and after['run'] and after['dest'] == before['dest'], [before, after])
                await run_s(pg, 1)
                if skill == 'rookie':
                    ok(f'{tag} Resume: the DZ chip or chevron is back', await pg.evaluate("()=>['dzMark','dzArrow'].some(id=>document.getElementById(id).classList.contains('on'))"))
            except Exception as e: ok(f'{tag} resume path', False, str(e)[:120])

            ok(f'{tag} no page errors', not pg.errs, pg.errs[:3])
            await pg.context.close()
        await b.close()
    srv.shutdown()
    sys.exit(ok.done('overlay_check'))
asyncio.run(main())
