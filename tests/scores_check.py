# Leaderboards end to end: the game at http://localhost:8765 (an origin the Worker allows) against
# `wrangler dev` on a fresh local D1, iPhone landscape 844x390. Screenshots: overnight-screenshots/scores.
#  signup with the callsign card after the splash, profanity refused, the dice, the recovery code;
#  the reserved OHRABAH name with the secret and the Creator badge; restore on a new device;
#  a real run with a run token and a ranked end of run badge; a fake score refused and flagged;
#  the offline queue; race the leader (ghost); the daily challenge once a day; rename; fame in the world;
#  the callsign painted on the aircraft.
# Run: .venv/bin/python tests/scores_check.py            (LIVE=https://... to point at a deployed Worker)
import asyncio, os, sys, json, re, subprocess, time, signal, shutil, threading, functools, http.server, socketserver, urllib.request
from playwright.async_api import async_playwright
sys.path.insert(0, os.path.dirname(__file__))
from harness import launch, Checks, IPHONE_15, THREE, ROOT, Quiet

ok = Checks()
K = 'window.__kgeu'
SRV = os.path.join(ROOT, 'server')
SHOTS = os.path.join(ROOT, 'overnight-screenshots', 'scores')
os.makedirs(SHOTS, exist_ok=True)
WORKER = 'http://127.0.0.1:8787'
SECRET = 'dev-ohrabah-secret'

def serve_game(port=8765, root=ROOT):
    h = functools.partial(Quiet, directory=root)
    class Q(socketserver.ThreadingTCPServer):
        allow_reuse_address = True; daemon_threads = True
        def handle_error(self, *a): pass
    srv = Q(('127.0.0.1', port), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv

def start_worker():
    shutil.rmtree(os.path.join(SRV, '.wrangler', 'state'), ignore_errors=True)
    subprocess.run(['npx', 'wrangler', 'd1', 'execute', 'pfs-scores', '--local', '--file=schema.sql'], cwd=SRV, capture_output=True, check=True)
    p = subprocess.Popen(['npx', 'wrangler', 'dev', '--port', '8787', '--ip', '127.0.0.1'], cwd=SRV, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    for _ in range(80):
        try:
            urllib.request.urlopen(WORKER + '/health', timeout=1); return p
        except Exception: time.sleep(0.5)
    raise RuntimeError('wrangler dev did not start')

def sql(q):
    out = subprocess.run(['npx', 'wrangler', 'd1', 'execute', 'pfs-scores', '--local', '--json', '--command', q], cwd=SRV, capture_output=True, text=True).stdout
    return json.loads(out)[0]['results']

async def device(b, storage=None, name=''):
    ctx = await b.new_context(viewport=IPHONE_15, has_touch=True, is_mobile=True, device_scale_factor=2)
    await ctx.grant_permissions(['clipboard-read', 'clipboard-write'], origin='http://localhost:8765')
    pg = await ctx.new_page()
    pg.errs = []
    pg.on('pageerror', lambda e: pg.errs.append(str(e)))
    pg.on('console', lambda m: pg.errs.append(m.text) if m.type == 'error' and 'fonts.g' not in m.text and 'ERR_INTERNET_DISCONNECTED' not in m.text and 'Failed to fetch' not in m.text and not m.text.startswith('Failed to load resource') else None)
    await pg.route('**/three.min.js', lambda r: r.fulfill(body=THREE, content_type='application/javascript'))
    await pg.route('**/fonts.googleapis.com/**', lambda r: r.abort())
    await pg.route('**/fonts.gstatic.com/**', lambda r: r.abort())
    st = {'kgeuLBUrl': WORKER}
    st.update(storage or {})
    await ctx.add_init_script('(()=>{if(sessionStorage.getItem("__seeded"))return;sessionStorage.setItem("__seeded","1");localStorage.clear();'
        + ''.join(f'localStorage.setItem({k!r},{v!r});' for k, v in st.items()) + '})()')
    await pg.goto('http://localhost:8765/index.html')
    await pg.wait_for_function('()=>window.__kgeu&&window.__kgeu.LB', timeout=30000)
    await pg.wait_for_function("()=>{const s=document.getElementById('splash');return !s||s.classList.contains('gone')}", timeout=30000)
    await pg.wait_for_timeout(600)
    return pg

async def shot(pg, name):
    await pg.screenshot(path=os.path.join(SHOTS, name + '.png'))

async def type_name(pg, v):
    await pg.fill('#csIn', '')
    await pg.type('#csIn', v, delay=20)
    await pg.wait_for_function("()=>{const t=document.getElementById('csStat').textContent;return t&&!t.startsWith('Checking')}", timeout=10000)
    return await pg.evaluate("()=>document.getElementById('csStat').textContent")

async def signup(pg, name):
    s = await type_name(pg, name)
    await pg.click('#csGo')
    await pg.wait_for_function("()=>!document.getElementById('csCode').hidden&&document.getElementById('csCode').textContent.length>6", timeout=10000)
    code = await pg.evaluate("()=>document.getElementById('csCode').textContent")
    return s, code

async def fly_arcade(pg, kind, wait_start=9):
    """Start an arcade run from its card path, let the wall clock pass the board minimum, autoland it, wait for the end."""
    if kind != 'daily': await pg.evaluate(f"()=>{K}.pick('cessna')")
    await pg.evaluate(f"()=>{K}.arcStart('{kind}')")
    await pg.wait_for_timeout(wait_start * 1000)
    await pg.evaluate(f"()=>{K}.auto()")
    if await pg.evaluate(f"()=>{{const a={K}.state().ap;return !!a&&a.mode==='orbit'}}"): await pg.evaluate(f"()=>{K}.auto()")   # a Reaper's first tap orbits
    for _ in range(300):
        await pg.evaluate(f"()=>{K}.ff(2)"); await pg.wait_for_timeout(60)
        s = await pg.evaluate(f"()=>{{const s={K}.state();return s.onGround||s.crashed}}")
        if s: break
    await pg.wait_for_timeout(3200)
    return await pg.evaluate("()=>({arc:document.getElementById('arcOv').classList.contains('on'),title:document.getElementById('aTitle').textContent})")

async def badge(pg, timeout=20000):
    await pg.wait_for_function("()=>{const b=document.getElementById('lbBadge');return b&&b.classList.contains('on')}", timeout=timeout)
    return await pg.evaluate("()=>document.getElementById('lbBadge').innerText.replace(/\\s+/g,' ')")

async def main():
    live = os.environ.get('LIVE')
    wk = None if live else start_worker()
    game = serve_game()
    try:
        async with async_playwright() as p:
            b = await launch(p)
            # ---------------- device A: first launch, the callsign card, profanity, dice, signup, recovery code
            A = await device(b)
            vis = await A.evaluate("()=>({cs:document.getElementById('csOv').classList.contains('on'),fun:document.getElementById('funnel').classList.contains('on')})")
            ok('first launch: the callsign card is up after the splash, over the Easy/Hard choice', vis['cs'] and vis['fun'], vis)
            await shot(A, '01_callsign_card')
            st = await type_name(A, 'sh1t')
            ok('profanity (leetspeak) refused by the server', 'not allowed' in st, st)
            ok('input is upper cased as you type', await A.evaluate("()=>document.getElementById('csIn').value") == 'SH1T')
            ok('CLAIM stays disabled for a refused name', await A.evaluate("()=>document.getElementById('csGo').disabled"))
            await shot(A, '02_profanity_refused')
            await A.click('#csDice')
            await A.wait_for_function("()=>/is free|taken/.test(document.getElementById('csStat').textContent)", timeout=10000)
            dv = await A.evaluate("()=>document.getElementById('csIn').value")
            ok('dice rolls a desert/aviation callsign', re.fullmatch(r'[A-Z0-9]{3,12}', dv) is not None, dv)
            ok('dice word from the desert and aviation lists', any(w in dv for w in ['HABOOB','DUST','SIDEWINDER','MESQUITE','SAGUARO','MONSOON','GILA','COYOTE','JAVELINA','OCOTILLO','PALOVERDE','SCORPION','RATTLER','ROADRUNNER','MIRAGE','MESA','CANYON','SONORAN','MOJAVE','TUMBLEWEED','CHOLLA','YUCCA','BUTTE','ARROYO','DUNE','SIROCCO','SANDSTORM','VULTURE','CONDOR','CACTUS','PECCARY','CHUBASCO','SAND','HAWK','VIPER','RAPTOR','TALON','MACH','THUNDER','BOLT','WARTHOG','HORNET','FALCON','EAGLE','STINGER','SABRE','PHANTOM','JAVELIN','ROTOR','JETWASH','VECTOR','APEX','BANDIT','BOGEY','GHOST','TALLY','ROCKET','NOMAD','BURNER','SPLASH','ACE','JET','WING','PROP']), dv)
            await shot(A, '03_dice')
            st, code = await signup(A, 'haboob')
            ok('live check says the name is free', 'is free' in st, st)
            ok('recovery code is 4 words, shown once', re.fullmatch(r'[A-Z]+ [A-Z]+ [A-Z]+ [A-Z]+', code) is not None, code)
            await shot(A, '04_recovery_code')
            await A.click('#csCopy'); await A.wait_for_timeout(300)
            clip = await A.evaluate("()=>navigator.clipboard.readText().catch(()=>'')")
            ok('Copy puts the code on the clipboard', clip == code or 'Copied' in await A.evaluate("()=>document.getElementById('csStat').textContent"), clip)
            await A.click('#csGo'); await A.wait_for_timeout(400)
            me = await A.evaluate(f"()=>({{on:document.getElementById('csOv').classList.contains('on'),P:{K}.LB.P}})")
            ok('card closes, the device holds its callsign and key', not me['on'] and me['P']['cs'] == 'HABOOB' and len(me['P']['key']) == 48, me)
            dbp = sql("SELECT key_hash FROM players WHERE callsign='HABOOB'")
            ok('the server stores a hash, not the device key', dbp and dbp[0]['key_hash'] != me['P']['key'])
            await A.click('#fPilot'); await A.wait_for_timeout(300)
            await A.evaluate(f"()=>{{{K}.openMenu();{K}.nav('sFly')}}"); await A.wait_for_timeout(500)
            fc = await A.evaluate("()=>document.getElementById('flyCs').innerText")
            ok('FLY screen shows the callsign and rank badge', 'HABOOB' in fc and 'Nugget' in fc and await A.evaluate("()=>!!document.querySelector('#flyCs svg.rk')"), fc)
            await shot(A, '05_fly_callsign')
            await A.wait_for_function(f"()=>{K}.LB.E.pool.length>=5", timeout=10000)
            ok('offline token pool filled after signup', True)
            # ---------------- a real run: token at the start, ranked at the end
            r = await fly_arcade(A, 'landing1')
            ok('1 mile landing challenge flown to the results', r['arc'] and 'points' in r['title'], r)
            bt = await badge(A)
            ok('end of run badge: rank and the TOP 10 moment', '#1' in bt and 'of 1' in bt and ('TOP' in bt or '#1 ON THE BOARD' in bt), bt)
            ok('the results sheet carries the board rank line', 'Leaderboard' in await A.evaluate("()=>document.getElementById('aLines').innerText"))
            ok('the badge never pauses the game on its own (the result sheet does)', await A.evaluate("()=>getComputedStyle(document.getElementById('lbBadge')).pointerEvents") in ('auto', 'none'))
            await shot(A, '06_end_of_run_badge')
            row = sql("SELECT board,callsign,mode,score,secs,ac,wx,token FROM scores WHERE callsign='HABOOB'")
            ok('score stored with board, mode, time, aircraft, weather, run token', row and row[0]['board'] == 'arc:landing1' and row[0]['mode'] == 'hard' and row[0]['token'] and row[0]['wx'], row)
            gh = sql("SELECT COUNT(*) n FROM ghosts WHERE board='arc:landing1'")
            ok('its flight path is kept as the leader ghost', gh[0]['n'] == 1, gh)
            # ---------------- the board screen, from the trophy on the card
            await A.evaluate(f"()=>{{document.getElementById('arcOv').classList.remove('on');{K}.openMenu();{K}.nav('sArc')}}"); await A.wait_for_timeout(400)
            await A.click('#arcCards [data-m=landing1] .tro'); await A.wait_for_timeout(300)
            ok('trophy opens the board, not the run', await A.evaluate(f"()=>{K}.curScr()==='sLb'||document.getElementById('sLb').classList.contains('on')") and not await A.evaluate(f"()=>{K}.ARC.on&&!{K}.paused()"))
            await A.click('[data-lbp=all]'); await A.wait_for_timeout(1500)
            rows = await A.evaluate("()=>[...document.querySelectorAll('#lbRowsIn .lbRow')].map(r=>({t:r.innerText.replace(/\\s+/g,' '),me:r.classList.contains('me')}))")
            ok('board lists the run, my row highlighted', rows and rows[0]['me'] and 'HABOOB' in rows[0]['t'], rows)
            ok('my rank line under the board', '#1' in await A.evaluate("()=>document.getElementById('lbMe').innerText"))
            ok('race the leader offered on a race board', not await A.evaluate("()=>document.getElementById('lbRace').hidden"))
            await shot(A, '07_board_all_time')
            n0 = await A.evaluate(f"()=>performance.getEntriesByType('resource').filter(e=>e.name.includes('/board?')).length")
            box = await A.evaluate("()=>{const r=document.getElementById('lbRows').getBoundingClientRect();return [r.x+r.width/2,r.y+10]}")
            await A.mouse.move(box[0], box[1]); await A.mouse.down(); await A.mouse.move(box[0], box[1] + 60, steps=6); await A.mouse.move(box[0], box[1] + 120, steps=6)
            await shot(A, '08_pull_to_refresh'); await A.mouse.up(); await A.wait_for_timeout(1200)
            n1 = await A.evaluate(f"()=>performance.getEntriesByType('resource').filter(e=>e.name.includes('/board?')).length")
            ok('pull to refresh fetches the board again', n1 > n0, (n0, n1))
            await A.click('[data-lbp=today]'); await A.wait_for_timeout(1200)
            ok('one list per board: no Easy/Hard chips in the header', await A.evaluate("()=>!document.querySelector('#sLb [data-lbm]')&&!document.querySelector('#sLb .mh .modeSeg')"))
            chips = await A.evaluate("()=>[...document.querySelectorAll('#lbRowsIn .lbRow, #lbMe .lbRow')].map(r=>{const t=r.querySelector('.modeTag');return t?t.textContent:''})")
            ok('every row carries its EASY or HARD chip (this run was Hard)', chips and all(c == 'HARD' for c in chips), chips)
            # ---------------- race the leader
            await A.click('#lbRace'); await A.wait_for_timeout(2500)
            g = await A.evaluate(f"()=>{{const G={K}.LB.E.ghost;return G?{{cs:G.cs,n:G.path.n,vis:G.m.g.visible,lab:G.m.label.sp.visible,run:!!{K}.ARC.on}}:null}}")
            ok('race the leader: a translucent ghost with the leader callsign flies the run', g and g['cs'] == 'HABOOB' and g['n'] > 10 and g['run'], g)
            p0 = await A.evaluate(f"()=>{K}.LB.E.ghost.m.g.position.toArray()")
            for _ in range(20): await A.evaluate(f"()=>{K}.stepFrame(0.1)")
            await A.evaluate(f"()=>{K}.stepFrame(0,true)")
            p1 = await A.evaluate(f"()=>{K}.LB.E.ghost.m.g.position.toArray()")
            ok('the ghost moves along the leader path', sum((a - c) ** 2 for a, c in zip(p0, p1)) ** 0.5 > 20, (p0, p1))
            ok('the ghost is drawn translucent', await A.evaluate(f"()=>{{let t=true;{K}.LB.E.ghost.m.g.traverse(o=>{{if(o.isMesh&&o.visible&&!(o.material.transparent&&o.material.opacity<0.6))t=false;}});return t}}"))
            await shot(A, '09_race_the_leader')
            # ---------------- a fake score from the browser console is refused and logged
            fake = await A.evaluate("""async()=>{const P=window.__kgeu.LB.P;const r=await fetch('http://127.0.0.1:8787/submit',{method:'POST',headers:{'Content-Type':'application/json'},
                body:JSON.stringify({cs:P.cs,key:P.key,board:'arc:landing1',mode:'hard',score:1500,secs:40,ac:'f16',when:Date.now(),token:'forged.token'})});return [r.status,await r.json()]}""")
            ok('a fake score without a valid token is rejected', fake[0] == 400 and fake[1].get('reason') == 'no valid run token', fake)
            fl = sql("SELECT reason FROM flagged WHERE callsign='HABOOB'")
            ok('the rejection is in the flagged table', any(x['reason'] == 'no valid run token' for x in fl), fl)
            # ---------------- offline: the run still flies, the score waits in the queue, then sends
            await A.evaluate(f"()=>{K}.LB.ghostOff()")
            await A.context.set_offline(True)
            await A.evaluate(f"()=>{K}.setSkill('rookie')")   # this one in Easy: the board then holds HABOOB in both modes
            r = await fly_arcade(A, 'landing1', wait_start=2)
            await A.evaluate(f"()=>{K}.setSkill('pilot')")
            bt = await badge(A)
            q = await A.evaluate(f"()=>{K}.LB.E.Q.length")
            ok('offline: the run is saved in the queue', q == 1 and 'SAVED' in bt, (q, bt))
            await shot(A, '10_offline_saved')
            await A.evaluate(f"()=>{{{K}.openMenu();{K}.LB.lbOpen('arc:landing1')}}"); await A.wait_for_timeout(1500)
            offl = await A.evaluate("()=>document.getElementById('lbRowsIn').innerText")
            await A.click('[data-lbp=week]'); await A.wait_for_timeout(1500)
            offl = await A.evaluate("()=>document.getElementById('lbRowsIn').innerText")
            ok('leaderboard screen shows a clean Offline state', 'Offline' in offl, offl)
            await shot(A, '11_offline_board')
            await A.context.set_offline(False)
            await A.evaluate("()=>window.dispatchEvent(new Event('online'))")
            await A.wait_for_function(f"()=>{K}.LB.E.Q.length===0", timeout=20000)
            n = sql("SELECT COUNT(*) n FROM scores WHERE callsign='HABOOB' AND board='arc:landing1'")
            ok('back online: the queued run is sent and accepted', n[0]['n'] == 2, n)
            # ---------------- one list: a player with runs in both modes shows once, with the better run's chip
            modes = sql("SELECT mode, score FROM scores WHERE callsign='HABOOB' AND board='arc:landing1' ORDER BY score DESC, id ASC")
            ok('HABOOB has an Easy and a Hard run on the 1 mile board', sorted(x['mode'] for x in modes) == ['easy', 'hard'], modes)
            await A.evaluate(f"()=>{{{K}.openMenu();{K}.LB.lbOpen('arc:landing1')}}"); await A.wait_for_timeout(300)
            await A.click('[data-lbp=all]'); await A.wait_for_timeout(1800)   # All time: last fetched before the Easy run was sent (cache is 30 s)
            mr = await A.evaluate("()=>({rows:[...document.querySelectorAll('#lbRowsIn .lbRow')].map(r=>({t:r.innerText.replace(/\\s+/g,' '),m:(r.querySelector('.modeTag')||{}).textContent||''})),tot:document.getElementById('lbTotal').textContent,me:(document.querySelector('#lbMe .modeTag')||{}).textContent||''})")
            best = modes[0]['mode'].upper() if modes else ''
            ok('merged board: HABOOB appears once, with the chip of the better run', len([x for x in mr['rows'] if 'HABOOB' in x['t']]) == 1 and mr['rows'][0]['m'] == best and mr['me'] == best, (best, mr))
            ok('merged board: the total counts the player once', mr['tot'] == '1 pilot', mr['tot'])
            await shot(A, '11b_merged_board')
            # ---------------- the daily challenge: identical spec, one official attempt, then practice
            d1 = await A.evaluate(f"()=>{K}.dailySpec()")
            await A.evaluate(f"()=>{{{K}.openMenu();{K}.nav('sMis')}}"); await A.wait_for_timeout(400)
            first = await A.evaluate("()=>document.querySelector('#misCards .mcard').dataset.m")
            ok('the daily challenge is the first card on MISSIONS', first == 'daily', first)
            cd1 = await A.evaluate("()=>document.querySelector('#misCards .cd').textContent"); await A.wait_for_timeout(1200)
            cd2 = await A.evaluate("()=>document.querySelector('#misCards .cd').textContent")
            ok('with a live countdown to the next one', re.fullmatch(r'\d+:\d\d:\d\d', cd1) and cd1 != cd2, (cd1, cd2))
            await shot(A, '12_missions_daily')
            r = await fly_arcade(A, 'daily')
            bt = await badge(A)
            ok('official daily attempt ranked', '#1' in bt, bt)
            await A.evaluate(f"()=>{K}.arcStart('daily')"); await A.wait_for_timeout(2500)
            pr = await A.evaluate(f"()=>({{p:{K}.ARC.practice,hud:document.getElementById('missT').textContent}})")
            ok('second daily run is practice and says so', pr['p'] and 'Practice' in pr['hud'], pr)
            await shot(A, '13_daily_practice')
            nd = sql("SELECT COUNT(*) n FROM scores WHERE board='daily'")
            ok('one official daily score on the server', nd[0]['n'] == 1, nd)
            # ---------------- device B: the reserved callsign
            B = await device(b)
            st = await type_name(B, 'ohrabah')
            ok('OHRABAH shows as reserved and asks for the secret', 'Reserved' in st and not await B.evaluate("()=>document.getElementById('csSecRow').hidden"), st)
            await B.fill('#csSec', 'wrong-secret'); await B.click('#csGo')
            await B.wait_for_function("()=>/creator secret/.test(document.getElementById('csStat').textContent)", timeout=10000)
            ok('a wrong secret is refused', 'not the creator secret' in await B.evaluate("()=>document.getElementById('csStat').textContent"))
            await shot(B, '14_reserved_callsign')
            await B.fill('#csSec', SECRET if not live else os.environ.get('OHRABAH_SECRET', '')); await B.click('#csGo')
            await B.wait_for_function("()=>!document.getElementById('csCode').hidden", timeout=10000)
            await B.click('#csGo'); await B.click('#fPilot')
            await B.evaluate(f"()=>{{{K}.openMenu();{K}.nav('sFly')}}"); await B.wait_for_timeout(400)
            ok('OHRABAH claimed with the secret and wears the gold Creator badge', await B.evaluate("()=>!!document.querySelector('#flyCs .creator')") and await B.evaluate(f"()=>{K}.LB.P.creator"))
            await shot(B, '15_creator_badge')
            berrs = B.errs; await B.context.close()
            # ---------------- device C: restore HABOOB with the 4 words; device A loses it
            C = await device(b)
            await C.click('#csAlt'); await C.wait_for_timeout(200)
            await C.fill('#csIn', 'HABOOB'); await C.fill('#csCodeIn', 'WRONG CODE WORDS HERE'); await C.click('#csGo')
            await C.wait_for_function("()=>/do not match/.test(document.getElementById('csStat').textContent)", timeout=10000)
            ok('restore with a wrong code refused', True)
            await C.fill('#csCodeIn', code.lower()); await C.click('#csGo')
            await C.wait_for_function(f"()=>{K}.LB.P&&{K}.LB.P.cs==='HABOOB'", timeout=10000)
            ok('restore with the recovery code gives the callsign to the new device', True)
            await shot(C, '16_restored')
            await A.reload(); await A.wait_for_function(f"()=>window.__kgeu&&{K}.LB", timeout=30000); await A.wait_for_timeout(4000)
            ok('the old device is told and let go', await A.evaluate(f"()=>{K}.LB.P===null"))
            # ---------------- rename in Settings: old scores follow
            await C.click('#fPilot'); await C.evaluate(f"()=>{{{K}.openMenu();{K}.nav('sSet')}}"); await C.wait_for_timeout(300)
            await shot(C, '17_settings_callsign')
            await C.click('#oCsCh'); await type_name(C, 'DUSTDEVIL'); await C.click('#csGo')
            await C.wait_for_function(f"()=>{K}.LB.P.cs==='DUSTDEVIL'", timeout=10000)
            rows = sql("SELECT DISTINCT callsign FROM scores WHERE board='arc:landing1'")
            ok('rename: old scores follow the new name', [x['callsign'] for x in rows] == ['DUSTDEVIL'], rows)
            await C.wait_for_timeout(300)
            ok('Settings then says when the next change is allowed', 'Change in 30 days' in await C.evaluate("()=>document.getElementById('oCsCh').textContent"))
            # ---------------- fame in the world, the callsign on the aircraft
            await C.reload(); await C.wait_for_function(f"()=>window.__kgeu&&{K}.LB", timeout=30000); await C.wait_for_timeout(3000)
            fame = await C.evaluate(f"()=>{K}.LB.E.fame")
            ok("fame: today's daily #1 and the top 3 fetched and cached", fame and fame['daily'] and fame['daily']['cs'] == 'DUSTDEVIL' and len(fame['top']) >= 1, fame)
            ok('fame cached for the next launch', await C.evaluate("()=>!!localStorage.getItem('kgeuFame')"))
            await C.evaluate(f"()=>{{{K}.pick('cessna');{K}.start('runway','kgeu')}}")
            await C.evaluate(f"""()=>{{const K={K},s=K.state(),y=K.groundHeight(2745,-1000)+7;s.pos.set(2745,y,-1000);s.vel.set(0,0,0);
                s.quat.setFromEuler(new THREE.Euler(0.05,-Math.PI/2,0,'YXZ'));K.snapCam();K.togglePause();document.getElementById('pauseOv').classList.remove('on');K.stepFrame(1/60);}}""")
            await shot(C, '18_billboard_daily_1')
            await C.evaluate(f"""()=>{{const K={K},s=K.state(),x0=K.wX(840,-352),z0=K.wZ(840,-352),x1=K.wX(840,-398),z1=K.wZ(840,-398),h=Math.atan2(x1-x0,-(z1-z0));
                s.pos.set(x0,K.groundHeight(x0,z0)+6,z0);s.quat.setFromEuler(new THREE.Euler(0.06,-h,0,'YXZ'));K.snapCam();K.stepFrame(1/60);}}""")
            await shot(C, '19_hangar_top_guns')
            dec = await C.evaluate(f"""()=>{{const K={K},out={{}};for(const id of ['f16','cessna','c130','reaper','mq9b','alpha']){{K.pick(id);K.start('runway','kgeu');
                let n=0;K.plane().g.traverse(o=>{{if(o.name==='callsign')n++;}});out[id]=n;}}return out}}""")
            ok('the callsign is painted on both sides of every aircraft', all(v == 2 for v in dec.values()), dec)
            for id, yaw in (('f16', 1.35), ('cessna', 1.75), ('c130', 1.7), ('reaper', 1.7)):
                await C.evaluate(f"""()=>{{const K={K};K.pick('{id}');K.start('runway','kgeu');K.stepFrame(1/60);K.photoOpen();const P=K.PHOTO,s=K.state(),e=new THREE.Euler().setFromQuaternion(s.quat,'YXZ');
                    P.yaw=e.y+{yaw};P.pitch=0.12;P.dist={ {'f16':'6','cessna':'5','c130':'14','reaper':'7'}[id] };K.stepFrame(1/60);}}""")
                await shot(C, f'20_callsign_on_{id}')
                await C.evaluate(f"()=>{K}.photoClose()")
            errs = A.errs + berrs + C.errs
            ok('no page errors', not errs, errs[:4])
            await b.close()
    finally:
        game.shutdown()
        if wk:
            try: os.killpg(wk.pid, signal.SIGTERM)
            except Exception: pass
    return ok.done('scores_check')

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
