# In place upgrade from the live version before leaderboards (git tag prescores) to this one,
# the way a home screen install sees it: one persistent browser profile, one origin
# (http://localhost:8765), the files underneath swapped between two launches.
#  - every localStorage key the old version wrote (settings, lesson progress, local bests,
#    records, strike best, mode) is still there, byte for byte, and still shows in the menus
#  - the callsign card comes up on the first launch of the new version (no Easy/Hard funnel
#    again), and once a callsign is picked it stays gone on the next launch
#  - the app name, icons and start_url in manifest.json did not change; there is no service
#    worker holding an old copy, and version.json is served for the reload check
# Needs a prescores worktree: git worktree add /tmp/pre prescores (made here if missing).
# Run: .venv/bin/python tests/upgrade_check.py
import asyncio, os, sys, json, subprocess, shutil, tempfile, threading, functools, http.server, socketserver, signal
from playwright.async_api import async_playwright
sys.path.insert(0, os.path.dirname(__file__))
from harness import Checks, IPHONE_15, THREE, ROOT, Quiet
from scores_check import start_worker, WORKER, SHOTS

ok = Checks()
K = 'window.__kgeu'
OLD = '/tmp/pre'
if not os.path.exists(os.path.join(OLD, 'index.html')):
    subprocess.run(['git', 'worktree', 'add', OLD, 'prescores'], cwd=ROOT, check=True)

class Swap:
    root = OLD
def serve():
    class H(Quiet):
        def __init__(self, *a, **k): super().__init__(*a, directory=Swap.root, **k)
        def end_headers(self):
            self.send_header('Cache-Control', 'max-age=600')      # what GitHub Pages sends
            super().end_headers()
    class Q(socketserver.ThreadingTCPServer):
        allow_reuse_address = True; daemon_threads = True
        def handle_error(self, *a): pass
    srv = Q(('127.0.0.1', 8765), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv

async def open_app(ctx):
    pg = await ctx.new_page()
    pg.errs = []
    pg.on('pageerror', lambda e: pg.errs.append(str(e)))
    await pg.goto('http://localhost:8765/')
    await pg.wait_for_function('()=>window.__kgeu', timeout=30000)
    await pg.wait_for_function("()=>{const s=document.getElementById('splash');return !s||s.classList.contains('gone')}", timeout=30000)
    await pg.wait_for_timeout(2500)
    return pg

async def main():
    wk = start_worker()
    srv = serve()
    prof = tempfile.mkdtemp(prefix='pfs-upgrade-')
    try:
        async with async_playwright() as p:
            ctx = await p.chromium.launch_persistent_context(prof, viewport=IPHONE_15, has_touch=True, is_mobile=True, device_scale_factor=2,
                args=['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader'])
            await ctx.route('**/three.min.js', lambda r: r.fulfill(body=THREE, content_type='application/javascript'))
            await ctx.route('**/fonts.googleapis.com/**', lambda r: r.abort())
            await ctx.route('**/fonts.gstatic.com/**', lambda r: r.abort())
            # ---- the old version: first launch, pick Hard, fly and set things the way a player would
            Swap.root = OLD
            pg = await open_app(ctx)
            ok('old version: no leaderboard code in it', await pg.evaluate(f"()=>!{K}.LB"))
            await pg.click('#fPilot'); await pg.wait_for_timeout(300)
            await pg.evaluate(f"""()=>{{const K={K};
                localStorage.setItem('kgeuLBUrl','{WORKER}');         // test only: point the new version at the local Worker
                K.setStickSens(3);K.setRadioVol(0.4);K.setMusicVol(0.3);K.pickBase('luke');K.pickPos('ramp');K.pick('f16');
                K.scRecord('arc:landing',{{pts:777,secs:151,letter:'A',stars:3,ac:'Cessna 172'}});
                K.scRecord('cessna',{{letter:'A',pts:94,fpm:85,where:'Glendale 1'}});
                K.achGrant('greaser');
                localStorage.setItem('kgeuSchool',JSON.stringify({{'cessna:first':'A','cessna:steep':'B','alpha:slow':'C'}}));
                localStorage.setItem('kgeuStrikeBest',JSON.stringify({{hits:3,avg:6,t:88,mode:'hard'}}));
                localStorage.setItem('kgeuTut','1');}}""")
            before = await pg.evaluate("()=>Object.fromEntries(Object.keys(localStorage).map(k=>[k,localStorage.getItem(k)]))")
            ok('old version wrote its data', all(k in before for k in ['kgeuOnboard', 'kgeuScores', 'kgeuSchool', 'kgeuStickSens', 'kgeuRadioVol', 'kgeuType', 'kgeuBase', 'kgeuStrikeBest']), sorted(before))
            await pg.close()
            # ---- the new version goes live; the player reopens the app
            Swap.root = ROOT
            pg = await open_app(ctx)
            ok('reopen loads the new version', await pg.evaluate(f"()=>!!{K}.LB"))
            after = await pg.evaluate("()=>Object.fromEntries(Object.keys(localStorage).map(k=>[k,localStorage.getItem(k)]))")
            changed = [k for k in before if after.get(k) != before[k]]
            ok('every old localStorage key kept byte for byte', not changed, changed)
            vis = await pg.evaluate("()=>({cs:document.getElementById('csOv').classList.contains('on'),fun:document.getElementById('funnel').classList.contains('on')})")
            ok('the callsign card shows on the first launch after the upgrade, the Easy/Hard choice does not', vis == {'cs': True, 'fun': False}, vis)
            await pg.screenshot(path=os.path.join(SHOTS, '21_upgrade_callsign_card.png'))
            await pg.fill('#csIn', 'MESQUITE')
            await pg.wait_for_function("()=>/is free/.test(document.getElementById('csStat').textContent)", timeout=10000)
            await pg.click('#csGo'); await pg.wait_for_function("()=>!document.getElementById('csCode').hidden", timeout=10000); await pg.click('#csGo')
            # the old data still drives the menus
            await pg.evaluate(f"()=>{{{K}.openMenu();{K}.nav('sArc')}}"); await pg.wait_for_timeout(300)
            em = await pg.evaluate("()=>document.querySelector('#arcCards [data-m=landing] .sc em').textContent")
            ok('local best still on its card', '777 pts' in em, em)
            await pg.evaluate(f"()=>{K}.nav('sSchool')"); await pg.wait_for_timeout(300)
            sch = await pg.evaluate("()=>[...document.querySelectorAll('#school .lrow')].map(r=>r.className.includes('done'))")
            ok('lesson progress still ticked', sch[:2] == [True, True], sch)
            pr = await pg.evaluate(f"()=>{K}.prefs()")
            ok('saved aircraft, base and start kept', pr.get('type') == 'f16' and pr.get('base') == 'luke' and pr.get('pos') == 'ramp', pr)
            ok('settings kept (stick, radio volume, mode)', await pg.evaluate(f"()=>({K}.TOUCH.sens===3&&Math.abs({K}.RADIO.vol-0.4)<1e-6&&localStorage.getItem('kgeuOnboard')==='pilot')"))
            await pg.close()
            pg = await open_app(ctx)
            vis = await pg.evaluate(f"()=>({{cs:document.getElementById('csOv').classList.contains('on'),P:{K}.LB.P&&{K}.LB.P.cs}})")
            ok('next launch: callsign kept, no card', vis == {'cs': False, 'P': 'MESQUITE'}, vis)
            after2 = await pg.evaluate("()=>Object.fromEntries(Object.keys(localStorage).map(k=>[k,localStorage.getItem(k)]))")
            ok('old data still intact after the callsign', all(after2.get(k) == before[k] for k in before if k != 'kgeuScores') and json.loads(after2['kgeuScores'])['best'] == json.loads(before['kgeuScores'])['best'])
            ok('no service worker holds an old copy', await pg.evaluate("()=>navigator.serviceWorker?navigator.serviceWorker.getRegistrations().then(r=>r.length===0):true"))
            v = await pg.evaluate("()=>fetch('version.json',{cache:'no-store'}).then(r=>r.json())")
            ok('version.json served and matches the build', v.get('v') == await pg.evaluate("()=>document.documentElement.innerHTML.match(/APP_VER='([^']+)'/)[1]"), v)
            ok('no page errors', not pg.errs, pg.errs[:3])
            await ctx.close()
        old = json.load(open(os.path.join(OLD, 'manifest.json'))); new = json.load(open(os.path.join(ROOT, 'manifest.json')))
        ok('manifest: same name, short name, icons and start_url', all(old[k] == new[k] for k in ['name', 'short_name', 'icons', 'start_url', 'scope']))
        ok('same icon files', all(open(os.path.join(OLD, i['src']), 'rb').read() == open(os.path.join(ROOT, i['src']), 'rb').read() for i in new['icons']))
        oh = open(os.path.join(OLD, 'index.html')).read(); nh = open(os.path.join(ROOT, 'index.html')).read()
        import re
        tags = lambda h: sorted(re.findall(r'<(?:link rel="(?:manifest|apple-touch-icon|icon)"|meta name="apple-mobile-web-app-title")[^>]*>', h))
        ok('home screen tags (manifest link, apple touch icon, app title) unchanged', tags(oh) == tags(nh), tags(nh))
        ok('page title unchanged', re.search(r'<title>(.*?)</title>', oh).group(1) == re.search(r'<title>(.*?)</title>', nh).group(1))
    finally:
        srv.shutdown(); shutil.rmtree(prof, ignore_errors=True)
        try: os.killpg(wk.pid, signal.SIGTERM)
        except Exception: pass
    return ok.done('upgrade_check')

sys.exit(asyncio.run(main()))
