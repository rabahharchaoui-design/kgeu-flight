# Fix2 item 3: a graphics tier change from the pause menu finishes while still paused, so Resume is instant.
# Case 1: a free flight (F-16, kgeu, Day) on Medium, paused, Settings from the pause sheet, tap High: applying; back to
# the sheet, Resume at once: still paused, #gfxBusy 'Applying graphics... resuming'; then it resumes by itself, the
# indicator gone, no program compiled over the next 10 flight frames, no flight stall tagged tier, csmBuild or prog, and
# the resume frame's gap under 3x the median of the 20 frames after it. Case 3: the same with the pause toggle (P),
# Medium to High as well. Case 2: pause, tap Medium (the tier it already is): Resume is instant, no indicator.
# Case 4: the battery guard's pendingTier applied at openMenu (MAIN MENU from the pause sheet): applying, the indicator in Settings until it drains.
# --shots: the pause sheet (and Settings) while applying at 568x320 and 844x390 to overnight-screenshots/fix2/item3/,
# with an overlap check of the indicator against the sheet's buttons. --only 1|2|3|4|shots runs one part, --vp 568|844
# one size of the shots.
# Run: .venv/bin/python tests/pause_tier_check.py [--shots] [--only N]
import asyncio, sys, os, statistics, time
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, finger, IPHONE_15

K = 'window.__kgeu'
ok = Checks()
SHOTS = '--shots' in sys.argv
ONLY = sys.argv[sys.argv.index('--only') + 1] if '--only' in sys.argv else None
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'overnight-screenshots', 'fix2', 'item3')

UI = """()=>{const g=document.getElementById('gfxBusy'),s=getComputedStyle(g),r=g.getBoundingClientRect(),K=window.__kgeu;
  return {vis:!g.hidden&&s.display!=='none'&&r.width>10&&r.height>8,txt:g.textContent,paused:K.paused(),ov:document.getElementById('pauseOv').classList.contains('on'),
    menu:document.getElementById('menu').classList.contains('on'),busy:K.gfxBusy()}}"""
# the indicator sits inside the Resume button and clear of every other button on the sheet
OVERLAP = """()=>{const g=document.getElementById('gfxBusy').getBoundingClientRect(),R=document.getElementById('pResume').getBoundingClientRect(),bad=[];
  if(g.left<R.left-0.5||g.right>R.right+0.5||g.top<R.top-0.5||g.bottom>R.bottom+0.5)bad.push('outside Resume '+[g.left,g.top,g.right,g.bottom,R.left,R.top,R.right,R.bottom].map(Math.round));
  const rg=document.createRange();rg.selectNodeContents(document.getElementById('pResume'));const l=rg.getBoundingClientRect();if(l.bottom>g.top+0.5)bad.push('over the RESUME label '+[l.bottom,g.top].map(Math.round));
  document.querySelectorAll('#pauseOv button').forEach(b=>{if(b.id==='pResume')return;const q=b.getBoundingClientRect();if(!q.width)return;
    if(q.left<g.right&&q.right>g.left&&q.top<g.bottom&&q.bottom>g.top)bad.push('overlaps '+(b.id||b.textContent.trim().slice(0,12)));});
  if(document.querySelector('#pauseOv .pz').scrollHeight>document.querySelector('#pauseOv .pz').clientHeight+1)bad.push('sheet overflows');
  return bad;}"""
SETCLIP = """()=>{const c=document.querySelector('#sSet .gfxSeg'),p=document.getElementById('gfxBusyS'),r=p.getBoundingClientRect(),G=document.querySelector('#sSet .setGrid').getBoundingClientRect();
  return {vis:!p.hidden&&r.width>10,over:c.scrollWidth>c.clientWidth+1,past:r.right>G.right+1||r.right>innerWidth}}"""
REC = """()=>{const K=window.__kgeu;window.__fr=[];const f=t=>{window.__fr.push([t,K.paused()]);if(window.__fr.length<400)requestAnimationFrame(f);};requestAnimationFrame(f);}"""

async def fly(b, url, vp=IPHONE_15):
    pg = await page(b, url, vp=vp, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3', 'kgeuTier': 'medium'})
    await pg.wait_for_function(f"()=>{K}&&{K}.WORLD.ready&&{K}.boot().pre.done", timeout=60000, polling=250)
    await pg.evaluate(f"()=>{{const r=document.getElementById('rotOk');if(r&&r.offsetParent)r.click();const K={K};K.pick('f16');K.pickBase('kgeu');K.setTOD('day');K.start('runway');K.stallsThr(250);}}")
    await pg.wait_for_timeout(3000)
    return pg

# headless the menu's frames drain a requeued run in well under a second; a phone takes seconds (6 s in the owner's
# log). gfxHold stands in for that: the tick's drain holds until released (gfxHold(0)) right after the Resume tap
async def pause_set_tier(pg, tier, hold=True):
    await finger(pg, '#bPause'); await pg.wait_for_timeout(400)
    await finger(pg, '#pSet'); await pg.wait_for_timeout(500)
    if hold: await pg.evaluate(f"()=>{K}.gfxHold(1e9)")
    await finger(pg, f'.gfxSeg [data-tier={tier}]'); await pg.wait_for_timeout(150)

async def wait_resumed(pg, label):
    t0 = time.monotonic()
    try:
        await pg.wait_for_function(f"()=>!{K}.gfxBusy().applying&&{K}.paused()===false", timeout=60000, polling=100)
        print(f'    {label}: resumed by itself {time.monotonic() - t0:.1f} s after the drain was let go (headless, ~3 fps)')
        return True
    except Exception:
        ok(f'{label}: resumed by itself within 60 s', False, await pg.evaluate(UI)); return False

async def after_checks(pg, label):
    s = await pg.evaluate(UI)
    ok(f'{label}: resumed by itself (paused false, pause sheet off, indicator hidden)', not s['paused'] and not s['ov'] and not s['vis'], s)
    await pg.wait_for_timeout(1200)
    log0 = (await pg.evaluate(f"()=>{K}.stalls()"))['log']
    await pg.wait_for_timeout(6800)   # ~20 headless frames after the resume
    fr = await pg.evaluate("()=>window.__fr")
    k = next((i for i in range(1, len(fr)) if fr[i - 1][1] and not fr[i][1]), None)
    if k is None:
        ok(f'{label}: the resume frame recorded', False, len(fr))
    else:
        gap = fr[k][0] - fr[k - 1][0]   # rAF stamps: the previous frame's start to the resumed frame's start
        nxt = [fr[i + 1][0] - fr[i][0] for i in range(k, min(len(fr) - 1, k + 20))]
        med = statistics.median(nxt) if nxt else 0
        print(f'    {label}: resume frame gap {gap:.0f} ms, median of the {len(nxt)} after it {med:.0f} ms, ratio {gap / med if med else 0:.2f}')
        ok(f'{label}: resume frame gap under 3x the median of the 20 frames after it', len(nxt) >= 15 and gap < 3 * med, [round(gap), round(med), len(nxt)])
    p0 = await pg.evaluate(f"()=>{K}.progN().compiles")
    for _ in range(10):
        await pg.evaluate(f"()=>{K}.stepFrame(1/60,false,false)")
    p1 = await pg.evaluate(f"()=>{K}.progN().compiles")
    await pg.evaluate(f"()=>{K}.stepFrame(0,true)")
    print(f'    {label}: progN compiles {p0} -> {p1} over 10 flight frames')
    ok(f'{label}: no program compiled over the next 10 flight frames', p1 == p0, [p0, p1])
    log1 = (await pg.evaluate(f"()=>{K}.stalls()"))['log']
    seen = set(); log = []
    for r in log0 + log1:
        key = (r['t'], r['gap'])
        if key not in seen: seen.add(key); log.append(r)
    bad = [r for r in log if r['scene'] == 'flight' and any(t == 'tier' or t == 'csmBuild' or t.startswith('prog') for t in r['tags'])]
    res = [r for r in log if 'resume' in r['tags']]
    print(f'    {label}: {len(log)} stall entries; resume entries {[(r["gap"], r["tags"]) for r in res][:2]}')
    ok(f'{label}: no flight stall tagged tier, csmBuild or prog', not bad, [(r['gap'], r['tags']) for r in bad][:3])

async def case1(b, url):
    pg = await fly(b, url)
    await pause_set_tier(pg, 'high')
    s = await pg.evaluate(UI)
    ok('1: tap High from the pause sheet\'s Settings: applying, the queue requeued', s['busy']['applying'] and not s['busy']['preDone'], s['busy'])
    sv = await pg.evaluate("()=>{const p=document.getElementById('gfxBusyS');return !p.hidden&&p.getBoundingClientRect().width>10}")
    ok('1: Settings shows the indicator under Graphics', sv)
    await finger(pg, '#mBack'); await pg.wait_for_timeout(200)
    s = await pg.evaluate(UI)
    ok('1: back on the pause sheet, still paused, indicator up', s['paused'] and s['ov'] and not s['menu'] and s['vis'] and 'Applying' in s['txt'], s)
    await pg.evaluate(REC)
    await finger(pg, '#pResume'); await pg.wait_for_timeout(100)
    s = await pg.evaluate(UI)
    ok('1: Resume at once: stays paused, #gfxBusy visible, "Applying graphics... resuming"', s['paused'] and s['ov'] and s['vis'] and 'Applying' in s['txt'] and 'resuming' in s['txt'] and s['busy']['resumeWait'], s)
    await finger(pg, '#pResume'); await pg.wait_for_timeout(50)
    s2 = await pg.evaluate(UI)
    ok('1: a second Resume tap changes nothing', s2['paused'] and s2['busy']['resumeWait'], s2['busy'])
    await pg.evaluate(f"()=>{K}.gfxHold(0)")
    if await wait_resumed(pg, '1'):
        await after_checks(pg, '1')
    ok('1: tier is High', await pg.evaluate(f"()=>{K}.GFX.tier") == 'high')
    ok('1: no page errors', not pg.errs, pg.errs[:3])
    await pg.context.close()

async def case3(b, url):
    # the pause toggle (P, togglePause) instead of Resume while applying
    pg = await fly(b, url)
    await pause_set_tier(pg, 'high')
    await finger(pg, '#mBack'); await pg.wait_for_timeout(200)
    await pg.evaluate(REC)
    await pg.keyboard.press('p'); await pg.wait_for_timeout(100)
    s = await pg.evaluate(UI)
    ok('3: the pause toggle while applying: stays paused, indicator "resuming"', s['paused'] and s['ov'] and s['vis'] and 'resuming' in s['txt'], s)
    await pg.evaluate(f"()=>{K}.gfxHold(0)")
    if await wait_resumed(pg, '3'):
        await after_checks(pg, '3')
    ok('3: no page errors', not pg.errs, pg.errs[:3])
    await pg.context.close()

async def case2(b, url):
    pg = await fly(b, url)
    await pause_set_tier(pg, 'medium', hold=False)
    s = await pg.evaluate(UI)
    ok('2: tap Medium (already Medium): not applying', not s['busy']['applying'] and s['busy']['preDone'], s['busy'])
    await finger(pg, '#mBack'); await pg.wait_for_timeout(200)
    s = await pg.evaluate(UI)
    ok('2: pause sheet, no indicator', s['paused'] and s['ov'] and not s['vis'], s)
    await pg.evaluate("()=>document.getElementById('pResume').click()")
    s = await pg.evaluate(UI)
    ok('2: Resume is instant (same task), no indicator', not s['paused'] and not s['ov'] and not s['vis'], s)
    ok('2: no page errors', not pg.errs, pg.errs[:3])
    await pg.context.close()

async def case4(b, url):
    # the battery guard's pendingTier applied at openMenu (MAIN MENU from the pause sheet) during a paused flight
    pg = await fly(b, url)
    await finger(pg, '#bPause'); await pg.wait_for_timeout(400)
    await pg.evaluate(f"()=>{{{K}.gfxHold(1e9);{K}.GFX.pendingTier='low';}}")
    await finger(pg, '#pMenu'); await pg.wait_for_timeout(300)
    s = await pg.evaluate(UI)
    ok('4: MAIN MENU with a pending battery-guard tier: Low applied, applying', s['busy']['applying'] and await pg.evaluate(f"()=>{K}.GFX.tier") == 'low', s['busy'])
    await pg.evaluate(f"()=>{K}.tabGo('sSet')"); await pg.wait_for_timeout(300)
    sv = await pg.evaluate("()=>{const p=document.getElementById('gfxBusyS');return !p.hidden&&p.getBoundingClientRect().width>10}")
    ok('4: Settings shows the indicator under Graphics', sv)
    await pg.evaluate(f"()=>{K}.gfxHold(0)")
    await pg.wait_for_function(f"()=>!{K}.gfxBusy().applying", timeout=60000, polling=200)
    sv = await pg.evaluate("()=>document.getElementById('gfxBusyS').hidden")
    ok('4: drained in the menu, the indicator gone', sv)
    ok('4: no page errors', not pg.errs, pg.errs[:3])
    await pg.context.close()

async def shots(b, url):
    os.makedirs(OUT, exist_ok=True)
    vps = [{'width': 568, 'height': 320}, IPHONE_15]
    if '--vp' in sys.argv: vps = [v for v in vps if v['width'] == int(sys.argv[sys.argv.index('--vp') + 1])]
    for vp in vps:
        n = f"{vp['width']}x{vp['height']}"
        pg = await fly(b, url, vp)
        await pause_set_tier(pg, 'high')
        c = await pg.evaluate(SETCLIP)
        ok(f'{n}: Settings indicator visible, Graphics chips not clipped', c['vis'] and not c['over'] and not c['past'], c)
        await pg.screenshot(path=os.path.join(OUT, f'settings_applying_{n}.png'))
        await finger(pg, '#mBack'); await pg.wait_for_timeout(200)
        bad = await pg.evaluate(OVERLAP)
        ok(f'{n}: indicator inside Resume, clear of every other button', not bad, bad)
        await pg.screenshot(path=os.path.join(OUT, f'pause_applying_{n}.png'))
        await finger(pg, '#pResume'); await pg.wait_for_timeout(100)
        bad = await pg.evaluate(OVERLAP)
        ok(f'{n}: "resuming" text still fits', not bad, bad)
        await pg.screenshot(path=os.path.join(OUT, f'pause_resuming_{n}.png'))
        await pg.evaluate(f"()=>{K}.gfxHold(0)")
        print('    shots in', OUT)
        await pg.context.close()

async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        if ONLY in (None, '1'): await case1(b, url)
        if ONLY in (None, '3'): await case3(b, url)
        if ONLY in (None, '2'): await case2(b, url)
        if ONLY in (None, '4'): await case4(b, url)
        if SHOTS or ONLY == 'shots': await shots(b, url)
        await b.close()
    srv.shutdown()
    sys.exit(ok.done('pause_tier_check'))

asyncio.run(main())
