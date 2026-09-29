# The deployed game against the deployed Worker, on a fresh device profile: the callsign card
# after the splash, a real signup, a 1 mile landing challenge flown by autoland and ranked with
# its run token, the board showing it, then every trace of the test player deleted from D1.
# Run: .venv/bin/python tests/live_scores_check.py
import asyncio, os, sys, json, re, secrets, subprocess
from playwright.async_api import async_playwright
sys.path.insert(0, os.path.dirname(__file__))
from harness import launch, Checks, IPHONE_15, ROOT

ok = Checks()
URL = 'https://rabahharchaoui-design.github.io/kgeu-flight/'
K = 'window.__kgeu'
SHOTS = os.path.join(ROOT, 'overnight-screenshots', 'scores')
CS = 'ZZQA' + secrets.token_hex(3).upper()

def sql(q):
    out = subprocess.run(['npx', 'wrangler', 'd1', 'execute', 'pfs-scores', '--remote', '--json', '--command', q], cwd=os.path.join(ROOT, 'server'), capture_output=True, text=True).stdout
    return json.loads(out)[0]['results']

async def main():
    try:
        async with async_playwright() as p:
            b = await launch(p)
            ctx = await b.new_context(viewport=IPHONE_15, has_touch=True, is_mobile=True, device_scale_factor=2)
            pg = await ctx.new_page(); errs = []
            pg.on('pageerror', lambda e: errs.append(str(e)))
            await pg.goto(URL + '?fresh=' + secrets.token_hex(3))
            await pg.wait_for_function(f'()=>window.__kgeu&&{K}.LB', timeout=60000)
            await pg.wait_for_function("()=>document.getElementById('csOv').classList.contains('on')", timeout=20000)
            ok('fresh device on the live site: callsign card after the splash', True)
            await pg.fill('#csIn', CS)
            await pg.wait_for_function("()=>/is free/.test(document.getElementById('csStat').textContent)", timeout=15000)
            await pg.click('#csGo')
            await pg.wait_for_function("()=>!document.getElementById('csCode').hidden", timeout=15000)
            code = await pg.evaluate("()=>document.getElementById('csCode').textContent")
            ok('live signup gives a 4 word recovery code', re.fullmatch(r'[A-Z]+ [A-Z]+ [A-Z]+ [A-Z]+', code) is not None, code)
            await pg.screenshot(path=os.path.join(SHOTS, '27_live_recovery_code.png'))
            await pg.click('#csGo'); await pg.click('#fPilot')
            await pg.wait_for_function(f"()=>{K}.LB.E.pool.length>=5", timeout=15000)
            await pg.evaluate(f"()=>{{{K}.pick('cessna');{K}.arcStart('landing1')}}")
            await pg.wait_for_timeout(11000)
            await pg.evaluate(f"()=>{K}.auto()")
            for _ in range(300):
                await pg.evaluate(f"()=>{K}.ff(2)"); await pg.wait_for_timeout(60)
                if await pg.evaluate(f"()=>{{const s={K}.state();return s.onGround||s.crashed}}"): break
            await pg.wait_for_function("()=>{const b=document.getElementById('lbBadge');return b&&b.classList.contains('on')}", timeout=30000)
            bt = await pg.evaluate("()=>document.getElementById('lbBadge').innerText.replace(/\\s+/g,' ')")
            ok('live run ranked with its run token', bt.startswith('#'), bt)
            await pg.screenshot(path=os.path.join(SHOTS, '28_live_ranked_run.png'))
            await pg.evaluate(f"()=>{{{K}.openMenu();{K}.LB.lbOpen('arc:landing1','hard')}}"); await pg.wait_for_timeout(500)
            await pg.click('[data-lbp=today]'); await pg.wait_for_timeout(2500)
            rows = await pg.evaluate("()=>document.getElementById('lbRowsIn').innerText")
            ok('the live board lists the run', CS in rows, rows[:200])
            await pg.screenshot(path=os.path.join(SHOTS, '29_live_board.png'))
            ok('no page errors', not errs, errs[:3])
            await b.close()
    finally:
        ids = sql(f"SELECT id FROM players WHERE callsign='{CS}'")
        if ids:
            i = ids[0]['id']
            sql(f"DELETE FROM ghosts WHERE player_id={i}; DELETE FROM scores WHERE player_id={i}; DELETE FROM tokens WHERE player_id={i}; DELETE FROM players WHERE id={i}; DELETE FROM flagged WHERE callsign='{CS}'")
        left = sql(f"SELECT (SELECT COUNT(*) FROM players WHERE callsign='{CS}') p, (SELECT COUNT(*) FROM scores WHERE callsign='{CS}') s")
        ok('test player removed from the live database', left[0]['p'] == 0 and left[0]['s'] == 0, left)
    return ok.done('live_scores_check')

sys.exit(asyncio.run(main()))
