# Leaderboards, one list per board: no Easy/Hard tabs, every row (and my row) carries an EASY or
# HARD chip next to the score, and the chip fits without wrapping or overflow on small iPhones in
# landscape and portrait. The Worker is stubbed (no wrangler), long callsigns and big scores.
# Screenshots: overnight-screenshots/phone2/item3.
# Run: .venv/bin/python tests/lb_merge_check.py
import asyncio, os, sys, json
from playwright.async_api import async_playwright
sys.path.insert(0, os.path.dirname(__file__))
from harness import launch, page, serve, Checks, ROOT

ok = Checks()
SHOTS = os.path.join(ROOT, 'overnight-screenshots', 'phone2', 'item3')
os.makedirs(SHOTS, exist_ok=True)
WK = 'http://lb.test'
ME = 'SIDEWINDER77'
NAMES = ['TUMBLEWEED12', 'OHRABAH', 'DUSTDEVIL', ME, 'ROADRUNNER99', 'MESQUITE', 'HABOOB', 'SAGUARO', 'PALOVERDE7', 'MONSOON']
ROWS = [{'r': i + 1, 'cs': n, 'score': 1500 - i * 37, 'secs': 60 + i, 'ac': ['f16', 'cessna', 'c130', 'reaper', 'alpha'][i % 5],
         'mode': 'easy' if i % 3 == 1 else 'hard', 'xp': 20000 - i * 1900, 'rank': ['Top Gun', 'Weapons School', 'Instructor Pilot', 'Flight Lead', 'Wingman', 'Nugget'][min(5, i // 2)],
         'creator': n == 'OHRABAH', 'when': 0} for i, n in enumerate(NAMES)]
MEROW = dict(ROWS[3]); MEROW.pop('secs'); MEROW.pop('ac'); MEROW.pop('when')
BOARD = {'board': 'daily', 'mode': 'all', 'period': 'today', 'dir': 1, 'total': 1234, 'rows': ROWS, 'me': MEROW, 'ghost': {'score': 1500, 'ac': 'f16', 'cs': NAMES[0]}, 'now': 0, 'day': 20260930}
VIEWS = [('844x390', {'width': 844, 'height': 390}), ('667x375', {'width': 667, 'height': 375}), ('568x320', {'width': 568, 'height': 320}),
         ('390x844_portrait', {'width': 390, 'height': 844}), ('375x667_portrait', {'width': 375, 'height': 667})]
CORS = {'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Headers': 'Content-Type', 'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'}
seen = []

async def worker(route):
    req = route.request; path = req.url[len(WK):].split('?')[0]
    seen.append(req.url)
    if req.method == 'OPTIONS': return await route.fulfill(status=204, headers=CORS)
    body = {'/health': {'ok': True}, '/me': {'cs': ME, 'xp': 5000, 'creator': False}, '/pool': {'tokens': []},
            '/fame': {'day': 20260930, 'daily': None, 'top': []}, '/board': BOARD, '/ghost': {'ghost': None}}.get(path, {})
    await route.fulfill(status=200, headers=CORS, content_type='application/json', body=json.dumps(body))

FIT = """()=>{const out=[];document.querySelectorAll('#lbRowsIn .lbRow, #lbMe .lbRow').forEach(r=>{const R=r.getBoundingClientRect(),t=r.querySelector('.modeTag'),s=r.querySelector('.s');
  if(!t){out.push({cs:r.innerText.slice(0,14),none:true});return;}const T=t.getBoundingClientRect(),S=s.getBoundingClientRect();
  out.push({cs:(r.querySelector('.c span')||{}).textContent,m:t.textContent,h:Math.round(R.height),th:Math.round(T.height),
    inside:T.left>=R.left-0.5&&T.right<=R.right+0.5&&S.right<=R.right+0.5,nowrap:t.scrollWidth<=t.clientWidth+0.5&&T.height<20,
    next:T.right<=S.left+0.5&&S.left-T.right<=10,rowfit:r.scrollWidth<=r.clientWidth+0.5,me:r.parentElement.id==='lbMe'});});return out}"""

async def main():
    srv, url = serve()
    try:
        async with async_playwright() as p:
            b = await launch(p)
            for name, vp in VIEWS:
                seen.clear()
                ctx_storage = {'kgeuLBUrl': WK, 'kgeuLB': json.dumps({'cs': ME, 'key': 'a' * 48, 'xp': 5000}), 'kgeuOnboard': 'pilot', 'kgeuTut': '1'}
                pg = await page(b, url, vp=vp, storage=ctx_storage)   # boot's /health to lb.test fails; the board route is stubbed below
                await pg.context.route(WK + '/**', worker)
                if vp['height'] > vp['width']: await pg.evaluate("()=>document.body.classList.add('portraitok')")   # Play in portrait anyway
                await pg.evaluate("()=>{window.__kgeu.openMenu();window.__kgeu.LB.lbOpen('daily','easy')}")
                await pg.wait_for_function("()=>document.querySelectorAll('#lbRowsIn .lbRow').length>=10", timeout=10000)
                await pg.wait_for_timeout(400)
                ok(name + ': a merged board: no EASY/HARD chip in the bar (ui1: only the dogfight has one)', await pg.evaluate("()=>document.getElementById('lbMode').hidden&&!document.querySelector('#sLb [data-lbm]')"))
                ok(name + ': Today / This week / All time kept', await pg.evaluate("()=>[...document.querySelectorAll('#sLb [data-lbp]')].map(b=>b.getAttribute('aria-label')).join('|')") == 'Today|This week|All time')
                bu = [u for u in seen if '/board?' in u]
                ok(name + ': the board is fetched with no mode', bu and all('&m=' not in u and '?m=' not in u for u in bu), bu[-1:])
                f = await pg.evaluate(FIT)
                want = [r['mode'].upper() for r in ROWS] + [MEROW['mode'].upper()]
                ok(name + ': every row and my row carry the chip of their run', [x.get('m') for x in f] == want, [x.get('m') for x in f])
                bad = [x for x in f if not (x.get('inside') and x.get('nowrap') and x.get('next') and x.get('rowfit') and x.get('h', 99) <= 58)]
                ok(name + ': the chip sits right next to the score, one line, inside the row', not bad, bad[:3])
                await pg.screenshot(path=os.path.join(SHOTS, 'lb_' + name + '.png'))
                ok(name + ': no page errors', not pg.errs, pg.errs[:3])
                await pg.context.close()
            await b.close()
    finally:
        srv.shutdown()
    return ok.done('lb_merge_check')

if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
