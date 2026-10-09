# Item 4.6b: the player facing half of the world regions. iPhone landscape, Hard.
# (a) FLY: the location picker shows ARIZONA, JAPAN, FRANCE and BRAZIL over five airport cards with
#     their descriptions; no card, label, time chip or GO overlaps another at 844x390 and 667x375.
# (b) tapping Tokyo Haneda (reload stubbed) saves kgeuRegion rjtt and a FLY resume; loading in rjtt:
#     the Tokyo card selected, the summary says Tokyo Haneda, no Haboob chip, the story names 34R.
# (c) the pause sheet's picker has the same groups in Arizona and in a region; Apply with another
#     region's airport saves a free flight resume, and after a real reload that flight is running there.
# (d) MISSIONS, ARCADE and SCHOOL cards carry the ARIZONA tag outside Arizona; the airdrop from rjtt
#     saves a resume with the mission, and after a real reload the airdrop is running in Arizona.
# (e) radio at each region: the tower's cleared to land names the region tower and every clip of it
#     is in radio/clips.json; every clip in clips.json has a file; region chatter, none of Arizona's.
# (f) the map at each region: its data loads, the airport card and runway numbers show close in,
#     tapping a runway end sets the destination and the HUD readout shows it, the legend has no
#     Arizona only rows, no label overlaps at two zoom levels.
# (g) the Settings credits, (h) no console errors.
# Usage: .venv/bin/python tests/world_ui_check.py
import asyncio, sys, json, os
from playwright.async_api import async_playwright
from harness import serve, launch, page, IPHONE_15, IPHONE_SE, Checks, finger, ROOT

ok = Checks()
K = 'window.__kgeu'
BASE = {'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'}
STUB = "()=>{window.__kgeuReload=()=>{window.__reloaded=(window.__reloaded||0)+1;};}"
HOME = {'rjtt': '34R', 'lfpg': '26L', 'sbrj': '20L'}
TWR = {'rjtt': 'Tokyo Tower', 'lfpg': 'de Gaulle Tower', 'sbrj': 'Santos Dumont Tower'}
NAME = {'rjtt': 'Tokyo Haneda', 'lfpg': 'Paris CDG', 'sbrj': 'Rio Santos Dumont'}
CLIPS = set(json.load(open(os.path.join(ROOT, 'radio', 'clips.json'))))
DESC = {'kgeu': 'KGEU, the home field, 7,150 ft', 'luke': 'KLUF, F-16 base, two 10,000 ft runways', 'phx': 'KPHX, 11,500 ft, the airliners', 'rjtt': 'RJTT, runways out in Tokyo Bay',
        'lfpg': 'LFPG, four parallel runways', 'sbrj': 'SBRJ, 4,340 ft on Guanabara Bay'}

# the visible boxes on FLY: a card counts by the part its scrolling row shows
FLYBOX = """()=>{const s=document.getElementById('sFly'),out=[];
  const vis=e=>{const r=e.getBoundingClientRect(),L=e.closest('.locs');if(!L)return r;const q=L.getBoundingClientRect(),x0=Math.max(r.left,q.left),x1=Math.max(x0,Math.min(r.right,q.right));
    return {left:x0,right:x1,top:r.top,bottom:r.bottom,width:x1-x0,height:r.height};};
  s.querySelectorAll('.locs .gcap, .locs .pick, .pick[data-tod], .pick[data-pos], #bGo, .gcap').forEach(e=>{if(!e.offsetParent)return;const r=vis(e);if(r.width<1)return;
    out.push({id:e.dataset.b||e.dataset.tod||e.dataset.pos||e.id||e.textContent.trim(),cls:e.className,l:r.left,r:r.right,t:r.top,b:r.bottom});});
  const groups=[...s.querySelectorAll('.locs .lgrp')].map(g=>[g.querySelector('.gcap').innerText,[...g.querySelectorAll('.pick')].map(c=>[c.dataset.b,c.querySelector('b').textContent,c.querySelector('span').textContent,getComputedStyle(c.querySelector('span')).display])]);
  return {boxes:out,groups:groups,W:innerWidth,H:innerHeight};}"""


async def after_reload(pg, cond, secs=90):
    """wait through a real reload until cond holds in the new page"""
    for _ in range(secs * 4):
        try:
            if await pg.evaluate(cond):
                return True
        except Exception:
            pass
        await pg.wait_for_timeout(250)
    raise RuntimeError('timed out after the reload: ' + cond)


def overlaps(boxes):
    bad = []
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            a, b = boxes[i], boxes[j]
            if a['id'] == b['id'] and a['cls'] == b['cls']:
                continue
            if min(a['r'], b['r']) - max(a['l'], b['l']) > 0.5 and min(a['b'], b['b']) - max(a['t'], b['t']) > 0.5:
                bad.append(f"{a['id']}/{b['id']}")
    return bad


async def fly_layout(pg, tag, region):
    await pg.evaluate(f"()=>{K}.openFly()"); await pg.wait_for_timeout(500)
    f = await pg.evaluate(FLYBOX)
    want = [['ARIZONA', [['kgeu', 'Glendale'], ['luke', 'Luke AFB'], ['phx', 'Sky Harbor']]], ['JAPAN', [['rjtt', 'Tokyo Haneda']]], ['FRANCE', [['lfpg', 'Paris CDG']]], ['BRAZIL', [['sbrj', 'Rio Santos Dumont']]]]
    got = [[g[0], [[c[0], c[1]] for c in g[1]]] for g in f['groups']]
    ok(f'{tag}: four region groups, six airport cards in order (Sky Harbor since planes2)', got == want, got)
    ok(f'{tag}: every card has its one line description showing', all(c[2] == DESC[c[0]] and c[3] != 'none' for g in f['groups'] for c in g[1]),
       [c[2] for g in f['groups'] for c in g[1]])
    bad = overlaps(f['boxes'])
    off = [b['id'] for b in f['boxes'] if b['l'] < -0.5 or b['r'] > f['W'] + 0.5 or b['b'] > f['H'] + 0.5]
    ok(f'{tag}: no overlap among cards, labels, chips and GO, all on screen', not bad and not off, (bad[:6], off))


async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)

        # ---------------- Arizona ----------------
        print('\n--- Arizona ---')
        pg = await page(b, url, vp=IPHONE_15, storage=BASE)
        await pg.evaluate(STUB)
        await fly_layout(pg, 'az 844x390', 'az')
        await pg.screenshot(path=os.path.join(ROOT, 'overnight-screenshots', 'world_ui_fly_az_844.png'))
        await pg.set_viewport_size(IPHONE_SE); await pg.wait_for_timeout(400)
        await fly_layout(pg, 'az 667x375', 'az')
        await pg.screenshot(path=os.path.join(ROOT, 'overnight-screenshots', 'world_ui_fly_az_667.png'))
        await pg.set_viewport_size(IPHONE_15); await pg.wait_for_timeout(300)
        r = await pg.evaluate("()=>[document.querySelector('#sFly .pick[data-b=kgeu]').classList.contains('sel'),getComputedStyle(document.querySelector('#sFly .pick[data-tod=haboob]')).display]")
        ok('Arizona: Glendale selected, Haboob chip shows', r[0] and r[1] != 'none', r)
        # (b) tap Tokyo Haneda: scrolled into view, then a real finger
        await pg.evaluate(f"()=>{{{K}.pick('cessna');{K}.setTOD('sunset');{K}.pickPos('ramp');const c=document.querySelector('#sFly .pick[data-b=rjtt]'),L=c.closest('.locs');L.scrollLeft=c.closest('.lgrp').offsetLeft;}}")
        await pg.wait_for_timeout(200)
        await finger(pg, '#sFly .pick[data-b="rjtt"]'); await pg.wait_for_timeout(300)
        k = await pg.evaluate("()=>({r:localStorage.getItem('kgeuRegion'),b:localStorage.getItem('kgeuBase'),res:JSON.parse(sessionStorage.getItem('kgeuResume')||'null'),rl:window.__reloaded,t:localStorage.getItem('kgeuType'),tod:localStorage.getItem('kgeuTOD'),pos:localStorage.getItem('kgeuPos')})")
        ok('FLY: tapping Tokyo Haneda saves kgeuRegion rjtt, a FLY resume, and reloads', k['r'] == 'rjtt' and k['res'] == {'screen': 'fly'} and k['rl'] == 1 and k['b'] == 'rjtt', k)
        ok('the aircraft, time and start stay saved', k['t'] == 'cessna' and k['tod'] == 'sunset' and k['pos'] == 'ramp', k)
        await pg.evaluate("()=>{localStorage.setItem('kgeuRegion','az');localStorage.setItem('kgeuBase','kgeu');sessionStorage.removeItem('kgeuResume');}")
        # (g) credits
        await pg.evaluate(f"()=>{K}.nav('sSet',true)"); await pg.wait_for_timeout(200)
        c = await pg.evaluate("()=>{const e=document.getElementById('osmCredit'),s=document.getElementById('sSet');return {t:e.innerText,scroll:s.scrollHeight>s.clientHeight+1}}")
        ok('Settings credits: OpenStreetMap, OurAirports, SRTM / Copernicus DEM via Mapzen, no scrolling',
           'Map data © OpenStreetMap contributors' in c['t'] and 'Runways: OurAirports' in c['t'] and 'Terrain: SRTM, Copernicus DEM via Mapzen' in c['t'] and not c['scroll'], c)
        await pg.set_viewport_size(IPHONE_SE); await pg.wait_for_timeout(300)
        c = await pg.evaluate("()=>{const s=document.getElementById('sSet');return s.scrollHeight>s.clientHeight+1}")
        ok('Settings still fits at 667x375', not c)
        await pg.set_viewport_size(IPHONE_15); await pg.wait_for_timeout(300)
        # (c) pause sheet groups in Arizona, then Apply with Rio Santos Dumont
        await pg.evaluate(f"()=>{{{K}.pick('alpha');{K}.pickBase('kgeu');{K}.setTOD('day');{K}.pickPos('final1');{K}.start('final1');}}"); await pg.wait_for_timeout(600)
        await finger(pg, '#bPause'); await pg.wait_for_timeout(500)
        g = await pg.evaluate("()=>[...document.querySelectorAll('#locPz .lgrp')].map(g=>[g.querySelector('.glbl').textContent,[...g.querySelectorAll('.pick')].map(c=>c.dataset.b)])")
        ok('pause sheet (Arizona): the same four groups and six airports', g == [['ARIZONA', ['kgeu', 'luke', 'phx']], ['JAPAN', ['rjtt']], ['FRANCE', ['lfpg']], ['BRAZIL', ['sbrj']]], g)
        await pg.evaluate("()=>{const c=document.querySelector('#locPz .pick[data-b=sbrj]');c.closest('.locs').scrollLeft=1e4;}"); await pg.wait_for_timeout(200)
        await finger(pg, '#locPz .pick[data-b="sbrj"]'); await pg.wait_for_timeout(200)
        r = await pg.evaluate("()=>[document.getElementById('pApply').textContent,document.querySelector('#locPz .pick[data-b=sbrj]').classList.contains('sel'),window.__reloaded||0]")
        ok('pause: Rio picked waits for Apply (no reload yet, Apply reads Apply)', r == ['Apply', True, 1], r)
        await finger(pg, '#pApply'); await pg.wait_for_timeout(300)
        k = await pg.evaluate("()=>({r:localStorage.getItem('kgeuRegion'),res:JSON.parse(sessionStorage.getItem('kgeuResume')||'null'),rl:window.__reloaded})")
        s0 = (k['res'] or {}).get('start') or {}
        ok('pause Apply: kgeuRegion sbrj and a free flight resume with base, start, aircraft, time and Hard',
           k['r'] == 'sbrj' and k['rl'] == 2 and s0.get('mode') == 'free' and s0.get('base') == 'sbrj' and s0.get('pos') == 'final1'
           and s0.get('type') == 'alpha' and s0.get('tod') == 'day' and s0.get('skill') == 'pilot', k)
        # the real reload: the same resume, no stub
        await pg.evaluate("()=>{delete window.__kgeuReload;location.reload();}")
        await after_reload(pg, f"()=>window.__kgeu&&{K}.REGION.id==='sbrj'&&{K}.running()&&{K}.WORLD.ready")
        await pg.wait_for_timeout(500)
        s = await pg.evaluate(f"()=>{{const s={K}.state();return {{reg:{K}.REGION.id,type:s.type,base:s.base,mode:s.mode,agl:Math.round(s.agl),menu:document.getElementById('menu').classList.contains('on'),tod:{K}.TOD().id}}}}")
        ok('after the real reload: the Alpha flies the 1 mile final at Santos Dumont, day',
           s['reg'] == 'sbrj' and s['type'] == 'alpha' and s['base'] == 'sbrj' and s['mode'] == 'final' and s['agl'] > 60 and not s['menu'] and s['tod'] == 'day', s)
        await region_radio_map(pg, 'sbrj')
        ok('Arizona and Rio: no console errors', not pg.errs, pg.errs[:4])
        await pg.context.close()

        # ---------------- Tokyo, loaded straight in ----------------
        print('\n--- rjtt ---')
        pg = await page(b, url, vp=IPHONE_15, storage=dict(BASE, kgeuRegion='rjtt', kgeuType='cessna', kgeuTOD='haboob'))
        await pg.wait_for_function(f"()=>{K}.WORLD.ready", timeout=60000)
        await pg.evaluate(STUB)
        await fly_layout(pg, 'rjtt 844x390', 'rjtt')
        r = await pg.evaluate(f"""()=>({{sel:[...document.querySelectorAll('#sFly .pick.sel[data-b]')].map(c=>c.dataset.b),sum:document.getElementById('sumLine').textContent,
          hb:getComputedStyle(document.querySelector('#sFly .pick[data-tod=haboob]')).display,hbP:getComputedStyle(document.querySelector('#pauseOv .pick[data-tod=haboob]')).display,
          tod:{K}.TOD().id,saved:localStorage.getItem('kgeuTOD'),sub:{K}.flySub('cessna'),cardVis:(()=>{{const c=document.querySelector('#sFly .pick[data-b=rjtt]'),L=c.closest('.locs'),a=c.getBoundingClientRect(),q=L.getBoundingClientRect();return a.left>=q.left-1&&a.right<=q.right+1;}})()}})""")
        ok('rjtt: the Tokyo Haneda card is the selected one and in view', r['sel'] == ['rjtt'] and r['cardVis'], r)
        ok('rjtt: the summary line names Tokyo Haneda', 'at Tokyo Haneda' in r['sum'], r['sum'])
        ok('rjtt: no Haboob chip on FLY or the pause sheet; a saved Haboob flies as day and stays saved', r['hb'] == 'none' and r['hbP'] == 'none' and r['tod'] == 'day' and r['saved'] == 'haboob', r)
        ok('rjtt: the aircraft story names Tokyo Haneda and runway 34R, not Glendale', 'runway 34R' in r['sub'] and 'Tokyo Haneda' in r['sub'] and 'Glendale' not in r['sub'] and 'N8401L' in r['sub'], r['sub'])
        await finger(pg, '#carMain .story'); await pg.wait_for_timeout(300)
        t = await pg.evaluate("()=>document.getElementById('storyT').textContent")
        ok('rjtt: Story shows that text', 'runway 34R' in t, t)
        await finger(pg, '#storyX'); await pg.wait_for_timeout(200)
        await pg.set_viewport_size(IPHONE_SE); await pg.wait_for_timeout(400)
        await fly_layout(pg, 'rjtt 667x375', 'rjtt')
        await pg.screenshot(path=os.path.join(ROOT, 'overnight-screenshots', 'world_ui_fly_rjtt_667.png'))
        await pg.set_viewport_size(IPHONE_15); await pg.wait_for_timeout(300)
        # (c) pause groups in the region; tapping Glendale there waits for Apply
        await pg.evaluate(f"()=>{K}.start('runway')"); await pg.wait_for_timeout(600)
        await finger(pg, '#bPause'); await pg.wait_for_timeout(500)
        g = await pg.evaluate("()=>[[...document.querySelectorAll('#locPz .lgrp')].map(g=>[g.querySelector('.glbl').textContent,[...g.querySelectorAll('.pick')].map(c=>c.dataset.b)]),[...document.querySelectorAll('#locPz .pick.sel')].map(c=>c.dataset.b)]")
        ok('pause sheet (rjtt): the same groups, Tokyo selected', g[0] == [['ARIZONA', ['kgeu', 'luke', 'phx']], ['JAPAN', ['rjtt']], ['FRANCE', ['lfpg']], ['BRAZIL', ['sbrj']]] and g[1] == ['rjtt'], g)
        await pg.evaluate("()=>{document.getElementById('locPz').scrollLeft=0;}"); await pg.wait_for_timeout(150)
        await finger(pg, '#locPz .pick[data-b="kgeu"]'); await pg.wait_for_timeout(200)
        r = await pg.evaluate("()=>[document.getElementById('pApply').textContent,window.__reloaded||0]")
        ok('pause (rjtt): Glendale picked, Apply pending, no reload yet', r == ['Apply', 0], r)
        await finger(pg, '#pResume'); await pg.wait_for_timeout(300)
        # (d) Arizona tags; the airdrop switches back to Arizona
        await pg.evaluate(f"()=>{K}.openMenu('sArc')"); await pg.wait_for_timeout(300)
        m = await pg.evaluate("()=>[...document.querySelectorAll('#arcCards .mcard')].filter(c=>!c.dataset.m.startsWith('apt:')).map(c=>[c.dataset.m,!!c.querySelector('.azTag')&&c.querySelector('.azTag').textContent])")
        ok('rjtt CHALLENGES: every card tagged ARIZONA but the daily, which names its airport instead', m and all(x[1] == 'ARIZONA' for x in m if x[0] != 'daily') and [x[1] for x in m if x[0] == 'daily'] == [False], m)
        await pg.evaluate(f"()=>{K}.nav('sSchool')"); await pg.wait_for_timeout(300)
        sch = await pg.evaluate("()=>[...document.querySelectorAll('#school .lrow')].map(c=>!!c.querySelector('.azTag'))")
        ok('rjtt SCHOOL: every lesson tagged ARIZONA', sch and all(sch), sch)
        await pg.evaluate(f"()=>{K}.nav('sArc')"); await pg.wait_for_timeout(300)
        a = await pg.evaluate("()=>[...document.querySelectorAll('#arcCards .mcard')].map(c=>[c.dataset.m,!!c.querySelector('.azTag')])")
        ok('rjtt ARCADE: every Arizona card tagged ARIZONA, the strike too; the daily and the world airports not', a and all(x[1] for x in a if x[0] != 'daily' and not x[0].startswith('apt:'))
           and not any(x[1] for x in a if x[0] == 'daily' or x[0].startswith('apt:')) and any(x[0] == 'range' for x in a) and sum(x[0].startswith('apt:') for x in a) == 3, a)
        await finger(pg, '#arcCards .mcard[data-m="drop"]'); await pg.wait_for_timeout(300)
        k = await pg.evaluate("()=>({r:localStorage.getItem('kgeuRegion'),res:JSON.parse(sessionStorage.getItem('kgeuResume')||'null'),rl:window.__reloaded})")
        s0 = (k['res'] or {}).get('start') or {}
        ok('rjtt airdrop: kgeuRegion az and a resume with the mission (drop, C-130, time, Hard)',
           k['r'] == 'az' and k['rl'] == 1 and s0.get('mode') == 'drop' and s0.get('type') == 'c130' and s0.get('tod') == 'day' and s0.get('skill') == 'pilot', k)
        await pg.evaluate("()=>localStorage.setItem('kgeuRegion','rjtt')")
        for kind, sel, check in (('strike range', '#arcCards .mcard[data-m="range"]', lambda s: s.get('mode') == 'range' and s.get('type') == 'reaper'),):   # ui1: no landing card
            await pg.evaluate(f"()=>{K}.nav('sArc')"); await pg.wait_for_timeout(200)
            await finger(pg, sel); await pg.wait_for_timeout(300)
            s1 = (await pg.evaluate("()=>JSON.parse(sessionStorage.getItem('kgeuResume')||'null')") or {}).get('start') or {}
            ok(f'rjtt {kind}: the resume carries the mode, aircraft and start', check(s1) and 'pos' in s1, s1)
        await pg.evaluate(f"()=>{{localStorage.setItem('kgeuRegion','rjtt');{K}.nav('sSchool')}}"); await pg.wait_for_timeout(200)
        await finger(pg, '#school .lrow[data-l="steep"]'); await pg.wait_for_timeout(300)
        s1 = (await pg.evaluate("()=>JSON.parse(sessionStorage.getItem('kgeuResume')||'null')") or {}).get('start') or {}
        ok('rjtt lesson: the resume carries the lesson', s1.get('lesson') == 'steep', s1)
        # (e), (f) in Tokyo, then the airdrop with a real reload
        await pg.evaluate("()=>localStorage.setItem('kgeuRegion','rjtt')")
        await region_radio_map(pg, 'rjtt')
        ok('rjtt: no console errors', not pg.errs, pg.errs[:4])
        await pg.evaluate(f"()=>{{delete window.__kgeuReload;{K}.openMenu('sArc');}}"); await pg.wait_for_timeout(300)
        await finger(pg, '#arcCards .mcard[data-m="drop"]')
        await after_reload(pg, f"()=>window.__kgeu&&{K}.REGION.id==='az'&&{K}.running()")
        await pg.wait_for_timeout(600)
        s = await pg.evaluate(f"()=>({{reg:{K}.REGION.id,kind:{K}.MISS.kind,on:{K}.MISS.on,type:{K}.state().type,saved:{K}.prefs().type,menu:document.getElementById('menu').classList.contains('on')}})")
        ok('after the real reload the airdrop is running in Arizona, the saved aircraft untouched',
           s['reg'] == 'az' and s['kind'] == 'drop' and s['on'] and s['type'] == 'c130' and s['saved'] == 'cessna' and not s['menu'], s)
        ok('rjtt to Arizona: no console errors', not pg.errs, pg.errs[:4])
        await pg.context.close()

        # ---------------- Paris ----------------
        print('\n--- lfpg ---')
        pg = await page(b, url, vp=IPHONE_15, storage=dict(BASE, kgeuRegion='lfpg'))
        await pg.wait_for_function(f"()=>{K}.WORLD.ready", timeout=60000)
        await region_radio_map(pg, 'lfpg')
        ok('lfpg: no console errors', not pg.errs, pg.errs[:4])
        await pg.context.close()

        missing = [c for c in CLIPS if not os.path.exists(os.path.join(ROOT, 'radio', c + '.m4a'))]
        ok('every clip in radio/clips.json has a file', not missing, missing[:4])
        new = ['t_tokyo_tower', 't_tokyo_ground', 't_degaulle_tower', 't_degaulle_ground', 't_santosdumont_tower', 't_santosdumont_ground'] + \
              ['t_rwy_' + n for n in ('34r 34l 16r 16l 04 22 05 23 26l 26r 27l 27r 08l 08r 09l 09r 20l 20r 02l 02r'.split())]
        ok('the region tower, ground and every runway end clip is in the manifest', all(c in CLIPS for c in new), [c for c in new if c not in CLIPS])
        await b.close()
    sys.exit(ok.done('world_ui_check'))


OVL = """()=>{const L=%s.LBL(),P=L.placed,bad=[];const hit=(a,b)=>a[0]<b[2]&&a[2]>b[0]&&a[1]<b[3]&&a[3]>b[1];
  for(let i=0;i<P.length;i++){for(let j=i+1;j<P.length;j++)if(hit(P[i].box,P[j].box))bad.push(P[i].kind+'/'+P[j].kind);
    for(const u of L.ui)if(hit(P[i].box,u))bad.push(P[i].kind+'/ui');}
  return {n:P.length,kinds:[...new Set(P.map(p=>p.kind))],bad:bad,tfc:%s.FM.tfcDrawn}}""" % (K, K)


async def region_radio_map(pg, rid):
    """(e) the tower on a 3 nm final, region chatter, (f) the map. The page is in region rid."""
    await pg.evaluate(f"()=>{{const K={K};K.RADIO.log.length=0;K.pick('cessna');K.start('final');}}")
    line = None
    for _ in range(40):
        await pg.wait_for_timeout(300)
        log = await pg.evaluate(f"()=>{K}.radioLog()")
        line = next((l for l in log if 'cleared to land' in (l['text'] or '')), None)
        if line:
            break
    atc = await pg.evaluate("()=>document.getElementById('atc').innerText")
    ok(f'{rid}: cleared to land from {TWR[rid]}, runway {HOME[rid]}, shown in the radio box',
       line and line['who'].startswith(TWR[rid]) and f'runway {HOME[rid]}' in line['text'] and TWR[rid] in atc, (line, atc))
    clips = (line or {}).get('clips') or []
    ok(f'{rid}: every clip of that call is recorded (runway t_rwy_{HOME[rid].lower()})', clips and all(c in CLIPS for c in clips) and f't_rwy_{HOME[rid].lower()}' in clips,
       [c for c in clips if c not in CLIPS] or clips)
    ch = await pg.evaluate(f"""()=>{{const K={K};K.RADIO.log.length=0;K.VQ&&0;const C=K.CHAT_R[K.REGION.id]||[];
      const all=C.flat().map(l=>l.clips).flat(),az=K.CHAT.flat().map(l=>l.who).join('|');
      K.chatNow();return {{n:C.length,clips:all,az:az,q:K.radioQ().map(l=>l.who)}}}}""")
    ok(f'{rid}: its own chatter (3 exchanges, recorded clips), no Arizona callers queued',
       ch['n'] == 3 and all(c in CLIPS for c in ch['clips']) and ch['q'] and not any(w in ('Luke Tower', 'Phoenix Approach', 'Glendale Tower 121.0') for w in ch['q']), ch)
    # (f) the map
    await pg.wait_for_function(f"()=>{K}.MAPD.ready", timeout=30000)
    await pg.evaluate(f"()=>{K}.fmOpen()"); await pg.wait_for_timeout(300)
    await pg.evaluate(f"()=>{K}.fmFlush()"); await pg.wait_for_timeout(150)
    leg = await pg.evaluate("()=>[...document.querySelectorAll('#mapLegL .lrow')].map(b=>b.dataset.kind)")
    ok(f'{rid}: the legend has only what the region has (airport, landmark)', leg == ['airport', 'landmark'], leg)
    o = await pg.evaluate(OVL)
    ok(f'{rid}: map open, {o["n"]} labels, no overlaps', not o['bad'] and o['n'] >= 4 and 'place' in o['kinds'], o)
    d = await pg.evaluate(f"""()=>{{const M={K}.MAPD,A={K}.APTS;return {{roads:M.roads.reduce((s,a)=>s+(a?a.length:0),0),taxi:M.taxi.length,apron:M.apron.length,
      urban:!!(M.urban&&M.urban.data),apt:A.map(a=>a.label),places:{K}.PLACES.length,lm:{K}.LANDMARKS.length}}}}""")
    ok(f'{rid}: map data in: roads, taxiways, aprons, urban grid, places, landmarks, the airport card {NAME[rid]}',
       d['roads'] > 100 and d['taxi'] > 5 and d['apron'] > 0 and d['urban'] and d['places'] > 5 and d['lm'] > 0 and d['apt'] == [NAME[rid] + ' · ' + rid.upper()], d)
    # the traffic on the map: some aircraft drawn when the view covers the field
    ok(f'{rid}: traffic symbols drawn on the map', o['tfc'] > 0, o['tfc'])
    # close in on the field: the airport card and runway numbers
    await pg.evaluate(f"()=>{{const K={K},e=K.RWY_ENDS;K.FM.cx=e.reduce((s,q)=>s+q.x,0)/e.length;K.FM.cz=e.reduce((s,q)=>s+q.z,0)/e.length;K.FM.scale=0.07;K.fmFlush();}}")
    await pg.wait_for_timeout(150)
    o = await pg.evaluate(OVL)
    ok(f'{rid}: close in, the airport card and runway numbers show, no overlaps', 'airport' in o['kinds'] and 'rwy' in o['kinds'] and not o['bad'], o)
    # tap the home runway's threshold end
    q = await pg.evaluate(f"()=>{{const K={K},e=K.RWY_ENDS.find(e=>e.num==='{HOME[rid]}');return K.fmP(e.x,e.z)}}")
    await pg.touchscreen.tap(q[0], q[1]); await pg.wait_for_timeout(400)
    dd = await pg.evaluate(f"()=>{K}.dest()")
    ok(f'{rid}: tapping the {HOME[rid]} end sets the destination', dd and dd.get('num') == HOME[rid], dd)
    await finger(pg, '#mapX'); await pg.wait_for_timeout(600)
    h = await pg.evaluate("()=>({hidden:document.getElementById('hDest').hidden,t:document.getElementById('dTxt').innerText})")
    ok(f'{rid}: the HUD destination readout shows {rid.upper()} {HOME[rid]}', not h['hidden'] and f'{rid.upper()} {HOME[rid]}' in h['t'], h)
    await pg.evaluate(f"()=>{K}.setDest(null)")


asyncio.run(main())
