# Red Flag Dogfight voices and sound (5.4): every d_c_ (cockpit), d_w_ (wingman Viper 2) and d_a_ (AWACS Sentry) clip
# is in radio/clips.json with a non empty file; the briefing card (Sound on for the full experience, FIGHT'S ON 60 pt or
# larger, the wave clock held until the tap); navigator.audioSession (stubbed) set to playback at the first tap, and
# without it on an iPhone the card says Turn off silent mode; wave 1 queues Sentry's picture call matching the spawn
# (count, bearing word, miles, angels); an enemy launch plays the cockpit Missile launch dry at once and a queued
# wingman call waits behind it; kills call Splash one then Splash two; no two voices overlap; Easy and Hard subtitles.
# Run: .venv/bin/python tests/dogfight_voice_check.py
import asyncio, json, math, os, sys
from playwright.async_api import async_playwright
from harness import serve, THREE, IGNORE, splash_gone, Checks, finger, ROOT
ok = Checks()
K = 'window.__kgeu'
STEP = "(n)=>{const K=window.__kgeu;for(let i=0;i<n;i++)K.stepFrame(0.1,false,true);}"
STUB = "Object.defineProperty(navigator,'audioSession',{value:{type:'auto'},configurable:true});"
SEED = ("(()=>{if(sessionStorage.getItem('__seeded'))return;sessionStorage.setItem('__seeded','1');localStorage.clear();"
        "localStorage.setItem('kgeuOnboard','pilot');localStorage.setItem('kgeuTut','1');localStorage.setItem('kgeuType','f16');})()")
IPHONE_UA = 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1'
# step the sim by real elapsed time every 50 ms (sim seconds and audio seconds match, as voice_queue_check does)
DRIVE = """()=>{const K=window.__kgeu;let last=performance.now();clearInterval(window.__iv);
  window.__iv=setInterval(()=>{const n=performance.now(),d=Math.min(0.1,(n-last)/1000);last=n;K.stepFrame(d,false,true);},50);}"""
STOP = "()=>{clearInterval(window.__iv);}"
D_C = ['launch', 'pullup', 'bingo', 'warning', 'flares', 'altitude']
D_W = ['fox2', 'guns', 'tally1', 'tally2', 'goodkill', 'break_r', 'break_l', 'winchester', 'niceflares', 'six', 'kio'] + [f'splash_{n}' for n in range(1, 11)]
D_A = ['bandit', 'sentry', 'g1', 'g2', 'g3', 'g4', 'miles', 'angels', 'clean', 'fightson', 'deck', 'hot', 'rtr', 's30', 'kio'] + \
      ['b_' + b for b in ('n', 'ne', 'e', 'se', 's', 'sw', 'w', 'nw')] + [f'num_{n}' for n in [5] + list(range(10, 21))]
BRG = ['north', 'northeast', 'east', 'southeast', 'south', 'southwest', 'west', 'northwest']

def overlaps(log, tol):
    """records whose audible span overlaps an earlier one's by more than tol seconds (a line cut the instant it
    started sits inside the voice that cut it: its overlap is its own short span, not the cutter's length)"""
    r = sorted([e for e in log if e['a1'] is not None], key=lambda e: e['a0'])
    bad = []
    for i in range(1, len(r)):
        end = max(e['a1'] for e in r[:i])
        o = min(end, r[i]['a1']) - r[i]['a0']
        if o > tol: bad.append((r[i - 1]['text'][:24], r[i]['text'][:24], round(o, 2)))
    return bad

async def ctx_page(b, url, stub, ua=None):
    ctx = await b.new_context(viewport={'width': 844, 'height': 390}, has_touch=True, is_mobile=True, device_scale_factor=2, **({'user_agent': ua} if ua else {}))
    await ctx.add_init_script(SEED)
    if stub: await ctx.add_init_script(STUB)
    pg = await ctx.new_page(); pg.errs = []
    pg.on('pageerror', lambda e: pg.errs.append(str(e)))
    pg.on('console', lambda m: pg.errs.append(m.text) if m.type == 'error' and not any(k in m.text for k in IGNORE) else None)
    await pg.route('**/three.min.js', lambda r: r.fulfill(body=THREE, content_type='application/javascript'))
    await pg.route('**/fonts.googleapis.com/**', lambda r: r.abort())
    await pg.route('**/fonts.gstatic.com/**', lambda r: r.abort())
    await pg.goto(url); await pg.wait_for_function('()=>window.__kgeu', timeout=30000); await splash_gone(pg)
    await pg.wait_for_timeout(300)
    return ctx, pg

async def main():
    # ---- the clips ----
    clips = json.load(open(os.path.join(ROOT, 'radio/clips.json')))
    want = ['d_c_' + c for c in D_C] + ['d_w_' + c for c in D_W] + ['d_a_' + c for c in D_A]
    miss = [c for c in want if c not in clips]
    bad = [c for c in want if not os.path.exists(os.path.join(ROOT, 'radio', c + '.m4a')) or os.path.getsize(os.path.join(ROOT, 'radio', c + '.m4a')) < 500]
    ok(f'clips.json lists all {len(want)} dogfight clips (d_c_, d_w_, d_a_), each file there and not empty', not miss and not bad, (miss[:5], bad[:5]))
    srv, url = serve()
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader', '--autoplay-policy=no-user-gesture-required'])
        ctx, pg = await ctx_page(b, url, stub=True)
        s0 = await pg.evaluate(f"()=>({{type:navigator.audioSession.type,set:{K}.audioSessionSet}})")
        # ---- the briefing card, the first tap ----
        await pg.evaluate(f"()=>{{{K}.openMenu();{K}.nav('sArc')}}"); await pg.wait_for_timeout(300)
        await finger(pg, '#arcCards [data-m="dogfight"]'); await pg.wait_for_timeout(500)
        s1 = await pg.evaluate(f"()=>({{type:navigator.audioSession.type,set:{K}.audioSessionSet}})")
        ok('navigator.audioSession (stubbed): untouched before any tap, type playback after the first tap, K.audioSessionSet true',
           s0['type'] == 'auto' and s0['set'] is False and s1['type'] == 'playback' and s1['set'] is True, (s0, s1))
        await pg.evaluate(f"()=>{K}.DF.test.noBanditFire=true")
        br = await pg.evaluate("""()=>{const o=document.getElementById('dfBrief'),g=document.getElementById('dfbGo').getBoundingClientRect(),s=document.getElementById('dfbSil');
          return {on:o.classList.contains('on'),txt:o.innerText,w:g.width,h:g.height,sil:!s.hidden&&s.offsetParent!==null,mode:document.getElementById('dfbMode').textContent,inView:g.bottom<=innerHeight&&g.top>=0}}""")
        ok('the briefing card: RED FLAG DOGFIGHT, the range, Sound on for the full experience, the three hints, the HARD chip',
           br['on'] and all(t in br['txt'] for t in ('RED FLAG DOGFIGHT', 'Barry M. Goldwater Range', 'Sound on for the full experience', 'FOX 2', 'GUN', 'FLARES')) and br['mode'] == 'HARD', br['txt'])
        ok("FIGHT'S ON is 60 pt or larger and on screen; no silent mode line when audioSession exists", br['w'] >= 60 and br['h'] >= 60 and br['inView'] and not br['sil'], br)
        await pg.evaluate(STEP, 20)
        t0 = await pg.evaluate(f"()=>({{t:{K}.DF.t,q:{K}.radioQ().length,cur:!!{K}.VQ.cur}})")
        ok('under the card the wave clock holds (2 s stepped) and nothing is said yet', t0['t'] == 90 and t0['q'] == 0 and not t0['cur'], t0)
        # wait for the clips before the fight's first calls
        for _ in range(40):
            if await pg.evaluate(f"()=>{{const R={K}.RADIO;return R.want&&R.got+Math.max(0,R.err)>=R.want}}"): break
            await pg.wait_for_timeout(500)
        await finger(pg, '#dfbGo'); await pg.wait_for_timeout(100)
        sp = await pg.evaluate(f"""()=>{{const K={K},D=K.DF,s=K.state();let x=0,y=0,z=0,n=0;for(const b of D.bandits)if(b.alive){{x+=b.p.x;y+=b.p.y;z+=b.p.z;n++;}}x/=n;y/=n;z/=n;
          const lines=K.radioLog().concat(K.radioQ()).map(l=>({{who:l.who,text:l.text,clips:l.clips}}));
          return {{brief:document.getElementById('dfBrief').classList.contains('on'),paused:!K.state().crashed&&K.DF.brief,n:n,brg:Math.atan2(x-s.pos.x,-(z-s.pos.z))*180/Math.PI,nm:Math.hypot(x-s.pos.x,z-s.pos.z)/1852,ft:(y-1.5)*3.28084+1071,pic:D.pic,lines:lines}}}}""")
        await pg.evaluate(STEP, 10)
        t1 = await pg.evaluate(f"()=>{K}.DF.t")
        ok("FIGHT'S ON: the card goes, the clock runs", not sp['brief'] and t1 < 90, (sp['brief'], t1))
        bw = BRG[int(round(((sp['brg'] % 360) + 360) % 360 / 45)) % 8]
        ang = max(10, min(20, round(sp['ft'] / 1000))); mi = max(5, min(20, round(sp['nm'] / 5) * 5))
        G = ['', 'g1', 'g2', 'g3', 'g4']
        exp = ['d_a_sentry', 'd_a_' + G[sp['n']], 'd_a_b_' + {'north': 'n', 'northeast': 'ne', 'east': 'e', 'southeast': 'se', 'south': 's', 'southwest': 'sw', 'west': 'w', 'northwest': 'nw'}[bw], f'd_a_num_{mi}', 'd_a_miles', 'd_a_angels', f'd_a_num_{ang}']
        pic = next((l for l in sp['lines'] if l['clips'] and l['clips'][0] == 'd_a_sentry'), None)
        fo = next((i for i, l in enumerate(sp['lines']) if l['clips'] and 'd_a_fightson' in l['clips']), None)
        pi = sp['lines'].index(pic) if pic else None
        ok("wave 1: Sentry's \"Fight's on\", then the picture call, from SENTRY", fo is not None and pi is not None and fo < pi and pic['who'] == 'SENTRY', [l['text'] for l in sp['lines']])
        ok('the picture call matches the spawn: count, bearing word, miles (rounded to 5, floor 5), angels', pic and pic['clips'] == exp and bw in pic['text'] and sp['pic']['n'] == sp['n'], (pic, exp, round(sp['brg']), round(sp['nm'], 1), round(sp['ft'])))
        # ---- Easy and Hard subtitles ----
        sub = f"(id)=>{{const K={K};K.dfCall(id);const l=K.radioQ().concat(K.VQ.cur?[K.VQ.cur.line]:[]).filter(l=>l.df&&l.clips&&l.clips[0]==='d_w_'+id).pop();return {{sub:l&&l.sub,last:K.DF.lastCall}}}}"
        hd = {i: await pg.evaluate(sub, i) for i in ('six', 'launch')}
        await pg.evaluate(f"()=>{K}.setSkill('rookie')")
        ez = {i: await pg.evaluate(sub, i) for i in ('six', 'launch')}
        await pg.evaluate(f"()=>{K}.setSkill('pilot')")
        ok('Hard: the brevity, prefixed by who says it (none for the cockpit)', hd['six']['sub'] == "VIPER 2: He's on your six!" and hd['launch']['last'] == 'Missile launch', hd)
        ok('Easy: plain English (Enemy behind you!, Missile! Tap FLARES, turn hard!)', ez['six']['sub'] == 'Enemy behind you!' and ez['launch']['last'] == 'Missile! Tap FLARES, turn hard!', ez)
        # ---- in real time: one voice at a time, the cockpit preempts, the kills ----
        # the spontaneous calls (tally, bandit bandit) already made, the air clear, then GUNS on the air and a wingman
        # call queued behind it when the bandit launches
        await pg.evaluate(f"()=>{{const K={K};K.DF.test.hold=true;K.DF.test.wave(3);K.DF.tally=true;K.DF.bbSaid=true;K.radioQ().length=0;}}")
        await pg.evaluate(DRIVE)
        for _ in range(40):
            if await pg.evaluate(f"()=>!{K}.VQ.cur&&!{K}.radioQ().length"): break
            await pg.wait_for_timeout(200)
        await pg.wait_for_timeout(1500)   # and any cockpit line from the subtitle checks above is over
        await pg.evaluate(f"()=>{{const K={K};K.vqLog(true);K.radioLog(true);K.DF.vlog.length=0;K.dfCall('guns');}}")
        for _ in range(20):
            if await pg.evaluate(f"()=>{{const c={K}.VQ.cur;return !!(c&&c.line.clips&&c.line.clips[0]==='d_w_guns')}}"): break
            await pg.wait_for_timeout(100)
        await pg.wait_for_timeout(300)
        await pg.evaluate(f"()=>{{const K={K};K.dfCall('six');K.DF.test.launchAt();}}")
        mid = await pg.evaluate(f"()=>({{q:{K}.radioQ().map(l=>l.clips&&l.clips[0]),vl:{K}.DF.vlog.slice()}})")
        await pg.wait_for_timeout(3500)
        await pg.evaluate(f"()=>{{const K={K},D=K.DF;K.dfKill(D.bandits[1],'test');}}"); await pg.wait_for_timeout(400)
        await pg.evaluate(f"()=>{{const K={K},D=K.DF;K.dfKill(D.bandits[2],'test');}}")
        for _ in range(40):
            if await pg.evaluate(f"()=>!{K}.VQ.cur&&!{K}.radioQ().length&&!{K}.state().crashed"): break
            await pg.wait_for_timeout(200)
        await pg.evaluate(STOP)
        log = await pg.evaluate(f"()=>{K}.vqLog()")
        vl = await pg.evaluate(f"()=>{K}.DF.vlog.slice()")
        ids = [v['id'] for v in vl]
        ck = next((v for v in vl if v['id'] == 'd_c_launch'), None)
        ok('the enemy launch plays the cockpit Missile launch dry, at once, with the wingman call still queued', ck and ck['dry'] and 'd_w_six' in mid['q'] and any(v['id'] == 'd_c_launch' for v in mid['vl']), (mid, ck))
        ok('the wingman and AWACS lines play through the radio filter (not dry)', all(not v['dry'] for v in vl if v['who'] in ('VIPER 2', 'SENTRY')) and any(v['who'] == 'VIPER 2' for v in vl), vl[:6])
        li = {e['text']: i for i, e in enumerate(log)}
        ci = next((i for i, e in enumerate(log) if e['who'] == 'COCKPIT'), None); si = next((i for i, e in enumerate(log) if e['text'] == "He's on your six!"), None)
        ok("the queued He's on your six! plays after the cockpit's Missile launch", ci is not None and si is not None and si > ci and log[si]['a0'] >= log[ci]['a1'] - 0.1, (ci, si, [(e['who'], e['text'][:20]) for e in log]))
        s1i, s2i = (ids.index('d_w_splash_1') if 'd_w_splash_1' in ids else None), (ids.index('d_w_splash_2') if 'd_w_splash_2' in ids else None)
        ok('the kills call Splash one, then Splash two', s1i is not None and s2i is not None and s1i < s2i, ids)
        ok('every voice record closed', all(e['a1'] is not None for e in log), [e['text'][:20] for e in log if e['a1'] is None])
        ok('no two voices overlap (0.1 s allowed for the cut fade)', not overlaps(log, 0.1), overlaps(log, 0.1))
        ok('no console errors', not pg.errs, pg.errs[:3])
        await ctx.close()
        # ---- an iPhone without navigator.audioSession: the card says turn off silent mode ----
        ctx, pg = await ctx_page(b, url, stub=False, ua=IPHONE_UA)
        await pg.evaluate(f"()=>{K}.dfStart()"); await pg.wait_for_timeout(500)
        r = await pg.evaluate(f"()=>{{const s=document.getElementById('dfbSil');return {{on:document.getElementById('dfBrief').classList.contains('on'),sil:!s.hidden&&s.offsetParent!==null,txt:s.textContent,as:'audioSession' in navigator,set:{K}.audioSessionSet}}}}")
        ok('iPhone without navigator.audioSession: the card shows Turn off silent mode, audioSessionSet false', r['on'] and r['sil'] and r['txt'] == 'Turn off silent mode' and not r['as'] and r['set'] is False, r)
        ok('no console errors (iPhone)', not pg.errs, pg.errs[:3])
        await b.close()
    srv.shutdown()
    sys.exit(ok.done('dogfight_voice_check'))

asyncio.run(main())
