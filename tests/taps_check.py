# Item 19: every main action is at most 2 taps from flight. Real touch taps (touchscreen.tap on
# the element centre), iPhone landscape at 844x390 and 568x320. Each action starts from the
# flying screen (running, not paused, no sheet up), taps its way there and counts the taps.
# Picks (aircraft, base, start, a mission card) are made within 2 taps; flying a changed pick
# is the Apply tap after that, and is checked too. Also: from app launch into flight, and the
# pause sheet (the one hub) fits at both sizes with no cut off buttons or chips.
# Run: .venv/bin/python tests/taps_check.py
import asyncio, sys, io, math, struct, base64, wave
from playwright.async_api import async_playwright
from harness import serve, page, Checks
ok = Checks()
K = 'window.__kgeu'
SR = 8000
SIZES = ({'width': 844, 'height': 390}, {'width': 568, 'height': 320})

def tone(freq, secs):
    b = io.BytesIO(); w = wave.open(b, 'wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes(b''.join(struct.pack('<h', int(9000 * math.sin(2 * math.pi * freq * i / SR))) for i in range(int(SR * secs))))
    w.close()
    return 'data:audio/wav;base64,' + base64.b64encode(b.getvalue()).decode()
TONES = [{'name': f'_tp{i}.wav', 'url': tone(f, 30.0), 'title': f'Tap Tone {i}'} for i, f in enumerate((330, 440, 550))]

FIT = """(sel)=>{const s=document.querySelector(sel);const W=innerWidth,H=innerHeight;const bad=[];
  s.querySelectorAll('button,input,.chip').forEach(e=>{const r=e.getBoundingClientRect();if(!r.width||getComputedStyle(e).visibility==='hidden')return;
    if(r.left<-0.5||r.top<-0.5||r.right>W+0.5||r.bottom>H+0.5)bad.push('off screen '+(e.id||e.textContent.trim().slice(0,16)));
    if(e.matches('button')&&(r.width<43.5||r.height<43.5))bad.push('small '+(e.id||e.textContent.trim().slice(0,16))+' '+Math.round(r.width)+'x'+Math.round(r.height));
    if(e.matches('button')&&e.scrollWidth>e.clientWidth+1)bad.push('text cut '+(e.id||e.textContent.trim().slice(0,16)));});
  s.querySelectorAll('.chip b,.qs b,.qs i,.pzNav span').forEach(e=>{if(e.offsetParent&&e.scrollWidth>e.clientWidth+1)bad.push('truncated '+e.textContent);});
  const hits=[...s.querySelectorAll('button')].filter(e=>e.getBoundingClientRect().width).map(e=>[e,e.getBoundingClientRect()]);
  for(let i=0;i<hits.length;i++)for(let j=i+1;j<hits.length;j++){const a=hits[i][1],b=hits[j][1];
    if(hits[i][0].contains(hits[j][0])||hits[j][0].contains(hits[i][0]))continue;
    if(Math.min(a.right,b.right)-Math.max(a.left,b.left)>1&&Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top)>1)bad.push('overlap '+hits[i][0].textContent.trim().slice(0,10)+' / '+hits[j][0].textContent.trim().slice(0,10));}
  return bad;}"""

FLYING = f"""()=>{{const K={K};const on=[...document.querySelectorAll('.overlay.on')].map(e=>e.id);
  return K.running()&&!K.paused()&&!on.length&&!K.PHOTO.on&&!K.FM.on}}"""

class Taps:
    def __init__(self, pg): self.pg = pg; self.n = 0
    async def __call__(self, sel, wait=450):
        r = await self.pg.evaluate("(s)=>{const e=document.querySelector(s);if(!e)return null;const r=e.getBoundingClientRect();"
                                   "if(!r.width||!r.height)return null;const x=r.x+r.width/2,y=r.y+r.height/2,h=document.elementFromPoint(x,y);"
                                   "return [x,y,!!h&&(e===h||e.contains(h))]}", sel)
        if not r: raise RuntimeError('not on screen: ' + sel)
        if not r[2]: raise RuntimeError('covered: ' + sel)
        await self.pg.touchscreen.tap(r[0], r[1]); self.n += 1
        await self.pg.wait_for_timeout(wait)

async def fly(pg, mode='runway'):
    await pg.evaluate(f"(m)=>{{const K={K};K.pick('cessna');K.pickBase('kgeu');K.pickPos('runway');K.setTOD('day');K.setSkill&&0;K.start(m)}}", mode)
    await pg.wait_for_timeout(700)
    if not await pg.evaluate(FLYING): raise RuntimeError('not on the flying screen')
    return Taps(pg)

async def run(pg, tag, name, steps, check, limit=2, extra=None):
    """steps: selectors tapped in order from flight; check: JS returning truthy once reached."""
    t = await fly(pg)
    pre = await pg.evaluate(extra) if extra else None
    try:
        for s in steps: await t(s)
        got = await pg.evaluate(check, pre) if pre is not None else await pg.evaluate(check)
    except Exception as e:
        got = 'error: ' + str(e)[:80]
    ok(f'{tag} {name}: {t.n} tap{"s" if t.n != 1 else ""} (<= {limit})', got is True and t.n <= limit, got)
    return t

async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist',
            '--enable-unsafe-swiftshader', '--autoplay-policy=no-user-gesture-required'])
        for vp in SIZES:
            tag = f"{vp['width']}x{vp['height']}"
            pg = await page(b, url, vp=vp, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3', 'kgeuMusicFree': '1', 'kgeuStickSens': '2'})
            await pg.evaluate(f"(l)=>{K}.musicLoad(l)", TONES)
            await pg.touchscreen.tap(vp['width'] / 2, 6); await pg.wait_for_timeout(300)

            # ---- from app launch into flight (home screen) ----
            for name, steps, chk in (
                ('launch: free flight (FLY, GO)', ['#hFly', '#bGo'], f"()=>{K}.running()&&!{K}.paused()&&{K}.state().mode==='runway'"),
                ('launch: a mission (MISSIONS, card)', ['#hMis', '#misCards [data-m="short"]'], f"()=>{K}.running()&&{K}.MISS.kind==='short'"),
                ('launch: an arcade game (ARCADE, card)', ['#hArc', '#arcCards .mcard[data-m=range]'], f"()=>{K}.running()&&{K}.state().mode==='range'"),
                ('launch: a lesson (FLIGHT SCHOOL, lesson)', ['#hSch', '#school .lrow[data-l=steep]'], f"()=>{K}.running()&&{K}.LES.on==='steep'"),
                ('launch: leaderboards (1 tap)', ['#hLb'], f"()=>{K}.curScr()==='sLb'"),
            ):
                await pg.evaluate(f"()=>{{const K={K};K.pick('cessna');K.pickBase('kgeu');K.pickPos('runway');K.openMenu()}}"); await pg.wait_for_timeout(400)
                t = Taps(pg)
                try:
                    for s in steps: await t(s, 900)
                    got = await pg.evaluate(chk)
                except Exception as e: got = 'error: ' + str(e)[:80]
                ok(f'{tag} {name}: {t.n} taps (<= 2)', got is True and t.n <= 2, got)

            # ---- from the flying screen ----
            await run(pg, tag, 'pause', ['#bPause'], f"()=>{K}.paused()&&document.getElementById('pauseOv').classList.contains('on')", 1)
            await run(pg, tag, 'pause and resume', ['#bPause', '#pResume'], FLYING)
            await run(pg, tag, 'restart (the Restart button on the sheet)', ['#bPause', '#pApply'],
                      f"(t0)=>{K}.RUN.t0>t0&&{K}.running()&&!{K}.paused()&&{K}.state().mode==='runway'", extra=f"()=>{K}.RUN.t0")
            await run(pg, tag, 'map (tap the minimap)', ['#map'], f"()=>{K}.FM.on", 1)
            await pg.evaluate(f"()=>{K}.fmClose()")
            await run(pg, tag, 'Action Shot', ['#bPause', '#pPhoto'], f"()=>{K}.PHOTO.on", 2)
            await pg.evaluate("()=>document.getElementById('phX').click()"); await pg.wait_for_timeout(300)
            await run(pg, tag, 'Easy/Hard (to Easy)', ['#bPause', '#pauseOv [data-skill="rookie"]'], f"()=>{K}.skill()==='rookie'")
            await pg.evaluate(f"()=>document.querySelector('#pauseOv [data-skill=\"pilot\"]').click()")
            await run(pg, tag, 'sound off', ['#bPause', '#pSound'], "()=>localStorage.getItem('kgeuMuted')==='1'&&document.querySelector('#pSound b').textContent==='Off'")
            await pg.evaluate("()=>document.getElementById('pSound').click()")
            await run(pg, tag, 'invert pitch', ['#bPause', '#pInv'], f"()=>{K}.TOUCH.inv===true&&document.querySelector('#pInv b').textContent==='On'")
            await pg.evaluate("()=>document.getElementById('pInv').click()")
            await run(pg, tag, 'stick sensitivity', ['#bPause', '#pSens'], f"()=>{K}.TOUCH.sens===3&&document.querySelector('#pSens b').textContent==='High'")
            await pg.evaluate(f"()=>{{const K={K};K.TOUCH.sens=2;localStorage.setItem('kgeuStickSens','2')}}")
            await run(pg, tag, 'full Settings (radio, volumes, callsign)', ['#bPause', '#pSet'], f"()=>{K}.curScr()==='sSet'&&document.getElementById('menu').classList.contains('on')")
            await run(pg, tag, 'leaderboards', ['#bPause', '#pLb'], f"()=>{K}.curScr()==='sLb'&&document.getElementById('menu').classList.contains('on')&&document.getElementById('lbList').children.length>0")
            t = Taps(pg); await t('#sLb .back')
            ok(f'{tag} leaderboards: back returns to the pause sheet', await pg.evaluate("()=>document.getElementById('pauseOv').classList.contains('on')&&!document.getElementById('menu').classList.contains('on')"))
            await run(pg, tag, 'quit to the main menu', ['#bPause', '#pMenu'], f"()=>{K}.curScr()==='sHome'&&document.getElementById('menu').classList.contains('on')")

            # a mission, an arcade game, a lesson: the list in 2 taps, the card starts it
            for name, btn, scr, card, chk in (
                ('missions', '#pMis', 'sMis', '#misCards [data-m="short"]', f"()=>{K}.MISS.kind==='short'&&{K}.running()"),
                ('arcade', '#pArc', 'sArc', '#arcCards .mcard[data-m=range]', f"()=>{K}.state().mode==='range'&&{K}.running()"),
                ('flight school', '#pSch', 'sSchool', '#school .lrow[data-l=steep]', f"()=>{K}.LES.on==='steep'&&{K}.running()"),
            ):
                t = await run(pg, tag, name + ' list', ['#bPause', btn], f"()=>{K}.curScr()==='{scr}'&&document.getElementById('menu').classList.contains('on')")
                if name == 'missions':
                    await t('.scr.on .back')
                    ok(f'{tag} missions: back returns to the pause sheet', await pg.evaluate("()=>document.getElementById('pauseOv').classList.contains('on')"))
                    await t(btn)
                try:
                    await t(card, 1200); got = await pg.evaluate(chk)
                except Exception as e: got = 'error: ' + str(e)[:80]
                ok(f'{tag} {name}: the card starts it', got is True, got)

            # change aircraft, base, start: picked in 2 taps, the button then reads Apply and flies them
            for name, sel, chk, fly_chk in (
                ('change aircraft', '#carPause .arrow.r', f"()=>{K}.prefs().type==='alpha'", f"()=>{K}.state().type==='alpha'"),
                ('change base', '#pauseOv .pick[data-b="luke"]', f"()=>{K}.prefs().base==='luke'", f"()=>{K}.state().base==='luke'"),
                ('change start', '#pauseOv .pick[data-pos="ramp"]', f"()=>{K}.prefs().pos==='ramp'", f"()=>{K}.state().mode==='ramp'"),
                ('change time of day (live)', '#pauseOv .pick[data-tod="night"]', f"()=>{K}.TOD().id==='night'", None),
            ):
                t = await run(pg, tag, name, ['#bPause', sel], chk)
                lbl = await pg.evaluate("()=>document.getElementById('pApply').textContent")
                if fly_chk:
                    ok(f'{tag} {name}: the Restart button now reads Apply', lbl == 'Apply', lbl)
                    await t('#pApply', 1200)
                    got = await pg.evaluate(fly_chk)
                    ok(f'{tag} {name}: Apply flies it', got is True and await pg.evaluate(FLYING), got)
                else:
                    ok(f'{tag} {name}: nothing to apply, the button still reads Restart', lbl == 'Restart', lbl)
            await pg.evaluate(f"()=>{K}.setTOD('day')")

            # music: the ticker strip (1 tap opens it, 1 more changes the track), and the pause sheet
            await fly(pg)
            await pg.evaluate(f"()=>{K}.setMusicOn(true)")
            vis = False
            for _ in range(40):
                vis = (await pg.evaluate(f"()=>{K}.ticker()"))['vis']
                if vis: break
                await pg.wait_for_timeout(200)
            ok(f'{tag} music: the ticker shows in flight', vis)
            p0 = (await pg.evaluate(f"()=>{K}.music()"))['playing']
            t = Taps(pg)
            try:
                await t('#tk', 400); await t('#tkNext', 1200)
                p1 = (await pg.evaluate(f"()=>{K}.music()"))['playing']
                got = bool(p1) and p1 != p0 and not await pg.evaluate(f"()=>{K}.paused()")
            except Exception as e: got = 'error: ' + str(e)[:80]
            ok(f'{tag} music next song from the ticker: {t.n} taps (<= 2), still flying', got is True and t.n <= 2, got)
            await run(pg, tag, 'music play/pause on the sheet', ['#bPause', '#pMusic'], "()=>['Play','Pause'].includes(document.getElementById('pMusic').textContent)")

            # the pause sheet fits: no cut off Main menu, no truncated chips, 44 px targets, no overlaps
            await fly(pg)
            await pg.evaluate(f"()=>{K}.togglePause()"); await pg.wait_for_timeout(500)
            bad = await pg.evaluate(FIT, '#pauseOv .pz')
            ok(f'{tag} pause sheet fits: nothing cut off or truncated, 44 px, no overlaps', not bad, bad[:5])
            mm = await pg.evaluate("()=>{const r=document.getElementById('pMenu').getBoundingClientRect();return r.bottom<=innerHeight&&r.right<=innerWidth&&r.top>=0}")
            ok(f'{tag} Main menu fully on screen', mm)
            await pg.evaluate(f"()=>{K}.togglePause()")
            ok(f'{tag} no page errors', not pg.errs, pg.errs[:3])
            await pg.context.close()
        await b.close()
    srv.shutdown()
    sys.exit(ok.done('taps_check'))
asyncio.run(main())
