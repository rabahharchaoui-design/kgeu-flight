# One-off screenshot script for phone notes 0929, item 7 (the "now playing" ticker:
# tkUI/tkFit/tkOpen/tkPausedBy; CSS marquee for a long title; tap opens an in-place
# Prev/Play-Pause/Next strip in landscape or the pause sheet in portrait; dimmed paused
# state; moves down a row in the C-130 airdrop). iPhone-class sizes at dsf 2, mobile,
# touch: 844x390 and 932x430 landscape, 390x844 portrait.
# Test/screenshot infra only; does not touch game code.
# Run: .venv/bin/python tests/item07_shots.py
import asyncio, os, sys, io, math, struct, base64, wave
from playwright.async_api import async_playwright
sys.path.insert(0, os.path.dirname(__file__))
from harness import serve, page, finger, ROOT

SHOTS = os.path.join(ROOT, 'overnight-screenshots', 'phone0929', 'item07')
os.makedirs(SHOTS, exist_ok=True)
K = "window.__kgeu"
SR = 8000

def tone(freq, secs):
    b = io.BytesIO(); w = wave.open(b, 'wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes(b''.join(struct.pack('<h', int(9000 * math.sin(2 * math.pi * freq * i / SR))) for i in range(int(SR * secs))))
    w.close()
    return 'data:audio/wav;base64,' + base64.b64encode(b.getvalue()).decode()
TITLES = ['A Much Longer Song Title That Will Not Fit In The Pill', 'Short One']
TONES = [{'name': f'_i7{i}.wav', 'url': tone(f, 30.0), 'title': TITLES[i]} for i, f in enumerate((330, 440))]

TOP = """(m)=>{const K=window.__kgeu;
  const a=document.getElementById('atc');a.innerHTML='<b>Glendale Tower</b>Cessna 3 Kilo Echo, runway 1 clear to land, wind 050 at 5<span class="plain">Cleared to land runway 1</span>';
  a.classList.add('on','hasPlain');
  const e0=document.getElementById('miss');if(!window.__tkWas)window.__tkWas=[e0.classList.contains('on'),document.body.classList.contains('missOn'),document.getElementById('missT').textContent,document.getElementById('missS').textContent];
  if(m){const e=document.getElementById('miss');document.getElementById('missT').textContent='Drop the load on the red smoke';
    document.getElementById('missS').textContent='2.4 nm, 1,500 ft, 140 kt';e.classList.add('on');document.body.classList.add('missOn');}}"""
UNTOP = """()=>{document.getElementById('atc').classList.remove('on');
  const w=window.__tkWas,e=document.getElementById('miss');window.__tkWas=null;e.classList.toggle('on',w[0]);document.body.classList.toggle('missOn',w[1]);document.getElementById('missT').textContent=w[2];document.getElementById('missS').textContent=w[3];}"""

async def m(pg): return await pg.evaluate("()=>window.__kgeu.music()")
async def tk(pg): return await pg.evaluate("()=>window.__kgeu.ticker()")

async def wait_for(pg, fn, cond, limit=6000, every=150):
    t = 0
    while t < limit:
        s = await fn(pg)
        if cond(s): return s
        await pg.wait_for_timeout(every); t += every
    return await fn(pg)

async def shot(pg, name, note=''):
    path = os.path.join(SHOTS, name)
    await pg.screenshot(path=path, timeout=120000)
    print(f'wrote {path}' + (f'  {note}' if note else ''))

async def run_size(p, tag, vp, portrait):
    seed = {'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3', 'kgeuMusicFree': '1'}
    b = await p.chromium.launch(args=['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist',
        '--enable-unsafe-swiftshader', '--autoplay-policy=no-user-gesture-required'])
    srv, url = serve()
    pg = await page(b, url, vp=vp, storage=seed)
    await pg.evaluate("(l)=>window.__kgeu.musicLoad(l)", TONES)
    await pg.touchscreen.tap(min(vp['width']-10, 330), 8)
    await wait_for(pg, m, lambda s: s['playing'])
    if portrait:
        await pg.evaluate("()=>document.body.classList.add('portraitok')")

    # 1) free flight: ticker showing a long scrolling title
    await pg.evaluate(f"()=>{{const K={K};K.pick('cessna');K.pickBase('kgeu');K.start('runway')}}")
    s = await wait_for(pg, m, lambda s: s['playing'] and s['want'], 8000)
    t = await wait_for(pg, tk, lambda t: t['vis'] and t['scroll'], 6000)
    await pg.wait_for_timeout(500)
    await shot(pg, f'{tag}_01_free_flight_long_title.png', (t, s['title']))

    # 2) a mission with the mission card + two-line tower subtitle, ticker at the same time
    await pg.evaluate(TOP, True); await pg.wait_for_timeout(500)
    t = await tk(pg)
    await shot(pg, f'{tag}_02_mission_tower_ticker.png', t)
    await pg.evaluate(UNTOP)

    if not portrait:
        # 3) tap: the open Prev/Play/Next strip (game keeps flying)
        await finger(pg, '#tk'); await pg.wait_for_timeout(400)
        t = await tk(pg)
        await shot(pg, f'{tag}_03_open_strip.png', t)

        # 4) dimmed paused state (paused from the strip)
        await finger(pg, '#tkPlay')
        s = await wait_for(pg, m, lambda s: s['playing'] is None, 6000)
        t = await wait_for(pg, tk, lambda t: not t['ctlVis'], 8000)
        await pg.wait_for_timeout(300)
        await shot(pg, f'{tag}_04_dimmed_paused.png', t)
        # resume for cleanliness
        await finger(pg, '#tk')
        await wait_for(pg, m, lambda s: s['playing'] and not s['userPaused'], 6000)
    else:
        # 3) portrait: tap opens the pause sheet's music row instead of the strip
        await finger(pg, '#tk'); await pg.wait_for_timeout(500)
        await shot(pg, f'{tag}_03_portrait_pause_sheet_music_row.png')

        # 4) dimmed paused state, reached via the pause sheet's music row, then resumed
        await finger(pg, '#pMusic')
        s = await wait_for(pg, m, lambda s: s['playing'] is None, 6000)
        await pg.wait_for_timeout(300)
        pz = await pg.evaluate("()=>document.getElementById('pauseOv').classList.contains('on')")
        if pz:
            await finger(pg, '#pResume'); await pg.wait_for_timeout(600)
        t = await wait_for(pg, tk, lambda t: t['paused'], 3000)
        await shot(pg, f'{tag}_04_dimmed_paused.png', t)
        await finger(pg, '#tk'); await pg.wait_for_timeout(400)
        await finger(pg, '#pMusic')
        await wait_for(pg, m, lambda s: s['playing'] and not s['userPaused'], 6000)
        pz = await pg.evaluate("()=>document.getElementById('pauseOv').classList.contains('on')")
        if pz:
            await finger(pg, '#pResume'); await pg.wait_for_timeout(400)

    # 5) C-130 airdrop, ticker moved down a row, with badges
    await pg.evaluate(f"()=>{{const K={K};K.pick('c130');K.pickBase('kgeu');K.start('final')}}"); await pg.wait_for_timeout(1500)
    await pg.evaluate(f"()=>{K}.mission('drop')"); await pg.wait_for_timeout(2000)
    await pg.evaluate(f"()=>{{{K}.gradeBadge({{letter:'B',line:'Firm, left of centerline, a long way off the touchdown zone'}});document.getElementById('banner').innerHTML='<b>NEW RECORD</b><span>Smoothest landing 42 fpm</span>';document.getElementById('banner').classList.add('on')}}")
    await pg.wait_for_timeout(500)
    await pg.evaluate(TOP, True); await pg.wait_for_timeout(500)
    lookOn = await pg.evaluate("()=>document.body.classList.contains('lookOn')")
    t = await tk(pg)
    await shot(pg, f'{tag}_05_c130_airdrop_badges.png', (t, 'lookOn=' + str(lookOn)))
    await pg.evaluate(UNTOP)

    print(f'{tag}: errs={pg.errs[:5]}')
    await b.close()
    srv.shutdown()

async def main():
    async with async_playwright() as p:
        await run_size(p, '844x390', {'width': 844, 'height': 390}, False)
        await run_size(p, '932x430', {'width': 932, 'height': 430}, False)
        await run_size(p, '390x844', {'width': 390, 'height': 844}, True)

asyncio.run(main())
