# Bugs1 item 7: My tickets. Settings > Bugs has a second link, My tickets (#bTickets, 'My tickets · N' from the last
# fetch cached in kgeuBugMine), opening #sTickets: one row per ticket (number, category, date, the text's first line
# cut with an ellipsis, Open or ✓ Fixed in <version>), fetched from the fake Worker's GET /reports/mine (ui1_mock Mock)
# at most once a minute; offline shows the cache with 'Offline, last checked'; an empty list says so; a guest asks with
# its kgeuBugKey, a callsign with E.P.key; with LB off the link toasts. Break-ui at 568x320, 844x390 and 390x844.
# Screenshots: overnight-screenshots/bugs1/item7/.
# Run: .venv/bin/python tests/bugs_tickets_check.py [--part N]   (1 list, cache, offline; 2 empty, keys, LB off; 3 break-ui)
import asyncio, os, sys, re, json
from datetime import datetime
from playwright.async_api import async_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import serve, launch, page, Checks, ROOT, finger, IPHONE_15
from ui1_mock import Mock

ok = Checks()
K = 'window.__kgeu'
SHOTS = os.path.join(ROOT, 'overnight-screenshots', 'bugs1', 'item7')
os.makedirs(SHOTS, exist_ok=True)
BASE = {'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'}
PART = int(sys.argv[sys.argv.index('--part') + 1]) if '--part' in sys.argv else 0
ms = lambda *a: int(datetime(*a).timestamp() * 1000)
LONG = 'The throttle slider jumps to full when I drag it fast near the brake button on top'[:80]
TICKETS = [   # newest first, the Worker's order
    {'id': 12, 'created': ms(2026, 10, 14, 12), 'category': 'controls', 'severity': 'broken', 'text': LONG, 'issue': 3, 'status': 'open', 'fixed_in': None},
    {'id': 9, 'created': ms(2026, 10, 12, 9), 'category': 'graphics', 'severity': 'annoying', 'text': 'Runway lights flicker\nat dusk', 'issue': 2, 'status': 'fixed', 'fixed_in': '2026-10-15-bugfix'},
    {'id': 4, 'created': ms(2026, 10, 9, 18), 'category': 'sound', 'severity': 'annoying', 'text': 'No engine sound', 'issue': None, 'status': 'open', 'fixed_in': None},
]
ROWS = """()=>[...document.querySelectorAll('#tkList li.tixRow')].map(li=>{const r=li.getBoundingClientRect(),t=li.querySelector('.tkT'),s=li.querySelector('.tkS');
  return {n:li.querySelector('.tkM b').textContent,cat:li.querySelector('.tkM span').textContent,date:li.querySelector('.tkD').textContent,text:t.textContent,
    h:r.height,sw:li.scrollWidth,cw:li.clientWidth,tsw:t.scrollWidth,tcw:t.clientWidth,ell:getComputedStyle(t).textOverflow,ws:getComputedStyle(t).whiteSpace,th:t.getBoundingClientRect().height,
    st:s.textContent.trim(),fixed:li.classList.contains('fixed'),check:!!s.querySelector('i')&&getComputedStyle(s.querySelector('i')).color,chip:s.querySelector('em')&&s.querySelector('em').textContent,
    act:getComputedStyle(li).cursor}})"""
LABEL = "()=>document.getElementById('bTicketsT').textContent"
MSG = "()=>{const m=document.querySelector('#tkList li.tkMsg');return m?m.textContent:null}"
NOTE = "()=>{const n=document.getElementById('tkNote');return n.hidden?null:n.textContent}"


async def wait_for(pg, js, t=6000):
    for _ in range(t // 100):
        if await pg.evaluate(js): return True
        await pg.wait_for_timeout(100)
    return False


async def settings(pg):
    await pg.evaluate("()=>{const r=document.getElementById('rotOk');if(r&&r.offsetParent)r.click();}")
    await pg.evaluate(f"()=>{{{K}.openMenu();{K}.nav('sSet',true);}}"); await pg.wait_for_timeout(500)
    await pg.evaluate("()=>document.getElementById('bTickets').scrollIntoView({block:'center'})"); await pg.wait_for_timeout(300)


async def open_tickets(pg):
    await settings(pg)
    await finger(pg, '#bTickets'); await pg.wait_for_timeout(300)
    await wait_for(pg, f"()=>!{K}.tixState().busy")
    await pg.wait_for_timeout(200)


async def part1(b, url):
    m = Mock(); m.extra['mine'] = TICKETS
    st = dict(BASE); st.update(m.storage())
    pg = await page(b, url, vp=IPHONE_15, storage=st, pre=m.install)
    await settings(pg)
    ok('(1) before any fetch the row reads My tickets', await pg.evaluate(LABEL) == 'My tickets', await pg.evaluate(LABEL))
    await open_tickets(pg)
    ok('(1) one request on open', len(m.mine) == 1, m.mine)
    ok('(1) the screen is My tickets', await pg.evaluate("()=>document.querySelector('#menu .scr.on').id==='sTickets'&&document.querySelector('#sTickets .mh h2').textContent==='My tickets'"))
    rows = await pg.evaluate(ROWS)
    ok('(1) three rows, newest first, the right numbers', [r['n'] for r in rows] == ['#12', '#9', '#4'], [r['n'] for r in rows])
    ok('(1) the category labels', [r['cat'] for r in rows] == ['Controls', 'Screen or graphics', 'Sound'], [r['cat'] for r in rows])
    ok('(1) the dates', [r['date'] for r in rows] == ['Oct 14', 'Oct 12', 'Oct 9'], [r['date'] for r in rows])
    if len(rows) == 3:
        f = rows[1]
        ok('(1) the fixed row: a green check and the version in a chip', f['fixed'] and f['check'] == 'rgb(63, 143, 79)' and f['chip'] == '2026-10-15-bugfix' and 'Fixed in' in f['st'], f)
        ok('(1) the fixed row shows only the first line of its text', f['text'] == 'Runway lights flicker', f['text'])
        ok('(1) the open rows say Open in a chip', rows[0]['chip'] == 'Open' and rows[2]['chip'] == 'Open', (rows[0]['st'], rows[2]['st']))
        L = rows[0]
        ok('(1) the long text: one line, an ellipsis where it does not fit (cut checked at 568 and 390 in part 3)', L['ell'] == 'ellipsis' and L['ws'] == 'nowrap' and L['th'] < 22, L)
        ok('(1) no row overflows (scrollWidth equals clientWidth)', all(r['sw'] == r['cw'] for r in rows), [(r['sw'], r['cw']) for r in rows])
        ok('(1) every row at least 44 px, no pointer cursor', all(r['h'] >= 43.5 and r['act'] != 'pointer' for r in rows), [r['h'] for r in rows])
    await finger(pg, '#tkList li.tixRow'); await pg.wait_for_timeout(300)
    tip = await pg.evaluate("()=>document.getElementById('bugTip').textContent")
    ok('(1) a tap on a row shows its full text', LONG in tip and tip.startswith('#12'), tip)
    await pg.screenshot(path=os.path.join(SHOTS, 'tickets_844.png'))
    await pg.evaluate(f"()=>{K}.nav('sSet',true)"); await pg.wait_for_timeout(400)
    await pg.evaluate("()=>{document.getElementById('bugTip').classList.remove('on');document.getElementById('bTickets').scrollIntoView({block:'center'})}"); await pg.wait_for_timeout(400)
    ok('(1) the Settings row reads My tickets · 3', await pg.evaluate(LABEL) == 'My tickets · 3', await pg.evaluate(LABEL))
    await pg.screenshot(path=os.path.join(SHOTS, 'settings_bugs_row.png'))
    await finger(pg, '#bTickets'); await pg.wait_for_timeout(800)
    ok('(1) a second open within 60 s makes no request and shows the list', len(m.mine) == 1 and len(await pg.evaluate(ROWS)) == 3, m.mine)
    # a minute later with no connection: the cache and the Offline line
    await pg.evaluate("()=>{const c=JSON.parse(localStorage.getItem('kgeuBugMine'));c.at-=120e3;localStorage.setItem('kgeuBugMine',JSON.stringify(c));}")
    m.offline = True
    await pg.evaluate(f"()=>{K}.nav('sSet',true)"); await pg.wait_for_timeout(300)
    await open_tickets(pg)
    note = await pg.evaluate(NOTE)
    ok('(1) offline: the cached list with Offline, last checked <time>', len(await pg.evaluate(ROWS)) == 3 and bool(note) and re.match(r'Offline, last checked \d{1,2}:\d\d [AP]M$', note), note)
    await pg.screenshot(path=os.path.join(SHOTS, 'tickets_offline.png'))
    errs = [e for e in pg.errs if 'ERR_FAILED' not in e]
    ok('(1) no console errors', not errs, errs[:3])
    await pg.context.close()
    # no cache and no connection
    m2 = Mock(offline=True)
    st = dict(BASE); st.update(m2.storage())
    pg = await page(b, url, vp=IPHONE_15, storage=st, pre=m2.install)
    await open_tickets(pg)
    ok('(1) no cache, offline: My tickets need a connection', await pg.evaluate(MSG) == 'My tickets need a connection', await pg.evaluate(MSG))
    await pg.context.close()


async def part2(b, url):
    m = Mock()   # a callsign: E.P.key
    st = dict(BASE); st.update(m.storage())
    pg = await page(b, url, vp=IPHONE_15, storage=st, pre=m.install)
    await open_tickets(pg)
    ok('(2) the callsign asks with E.P.key and its callsign', m.mine and m.mine[0][1] == 'k' * 48 and m.mine[0][2] == 'ACEPILOT' and m.mine[0][0] == 'GET', m.mine)
    ok('(2) the empty state', await pg.evaluate(MSG) == 'No tickets yet. Report a bug and it shows up here.', await pg.evaluate(MSG))
    await pg.evaluate(f"()=>{K}.nav('sSet',true)"); await pg.wait_for_timeout(300)
    ok('(2) no tickets: the row reads My tickets', await pg.evaluate(LABEL) == 'My tickets', await pg.evaluate(LABEL))
    await pg.evaluate(f"()=>{K}.nav('sTickets')"); await pg.wait_for_timeout(300)
    await pg.screenshot(path=os.path.join(SHOTS, 'tickets_empty.png'))
    ok('(2) no console errors', not pg.errs, pg.errs[:3])
    await pg.context.close()
    g = Mock(cs=None)   # a guest: kgeuBugKey
    st = dict(BASE); st.update(g.storage()); st['kgeuBugKey'] = 'ab' * 24
    pg = await page(b, url, vp=IPHONE_15, storage=st, pre=g.install)
    await pg.evaluate(f"()=>{K}.tixOpen()"); await pg.wait_for_timeout(400)
    await wait_for(pg, f"()=>!{K}.tixState().busy")
    ok('(2) a guest asks with kgeuBugKey and no callsign', g.mine and g.mine[0][1] == 'ab' * 24 and g.mine[0][2] == '', g.mine)
    ok('(2) guest: no console errors', not pg.errs, pg.errs[:3])
    await pg.context.close()
    # LB off on this origin (no kgeuLBUrl, 127.0.0.1 is not a game origin)
    pg = await page(b, url, vp=IPHONE_15, storage=dict(BASE))
    await settings(pg)
    ok('(2) LB off: the row says My tickets', await pg.evaluate(LABEL) == 'My tickets')
    await finger(pg, '#bTickets'); await pg.wait_for_timeout(300)
    r = await pg.evaluate("()=>({tip:document.getElementById('bugTip').textContent,scr:document.querySelector('#menu .scr.on').id})")
    ok('(2) LB off: a tap toasts Tickets need the online game and stays in Settings', r['tip'] == 'Tickets need the online game' and r['scr'] == 'sSet', r)
    ok('(2) LB off: no console errors', not pg.errs, pg.errs[:3])
    await pg.context.close()


AUDIT = """()=>{const s=document.getElementById('sTickets'),ul=document.getElementById('tkList'),W=innerWidth,H=innerHeight,bad=[];
  const q=ul.getBoundingClientRect();if(q.left<-0.5||q.right>W+0.5||q.bottom>H+0.5)bad.push('list outside the screen '+JSON.stringify([q.left,q.right,q.bottom]));
  if(s.scrollWidth>s.clientWidth+1)bad.push('screen scrolls sideways');
  const h=s.querySelector('.mh').getBoundingClientRect();if(h.bottom>q.top+0.5)bad.push('header over the list');
  [...ul.querySelectorAll('li.tixRow')].forEach((li,i)=>{const r=li.getBoundingClientRect();if(r.height<43.5)bad.push('row '+i+' '+r.height);if(li.scrollWidth>li.clientWidth)bad.push('row '+i+' overflows');
    li.querySelectorAll('.tkM b,.tkS em,.tkS i').forEach(e=>{const x=e.getBoundingClientRect();if(x.right>r.right+0.5||x.left<r.left-0.5)bad.push('row '+i+' '+e.tagName+' clipped');});});
  const bk=document.getElementById('mBack'),b=bk.getBoundingClientRect(),hit=document.elementFromPoint(b.x+b.width/2,b.y+b.height/2);
  const back=!bk.hidden&&b.width>=43.5&&b.height>=43.5&&b.top>=0&&b.left>=0&&b.right<=W&&!!hit&&bk.contains(hit);
  return {bad:bad,back:back,sh:ul.scrollHeight,ch:ul.clientHeight,oy:getComputedStyle(ul).overflowY}}"""


async def part3(b, url):
    many = TICKETS + [dict(TICKETS[i % 3], id=30 - i, created=ms(2026, 9, 20 - i, 10)) for i in range(9)]
    for W, H, name in [(568, 320, 'tickets_568.png'), (844, 390, None), (390, 844, 'tickets_390p.png')]:
        m = Mock(); m.extra['mine'] = many
        st = dict(BASE); st.update(m.storage())
        pg = await page(b, url, vp={'width': W, 'height': H}, storage=st, pre=m.install)
        await open_tickets(pg)
        tag = f'{W}x{H}'
        a = await pg.evaluate(AUDIT)
        ok(f'{tag}: nothing clipped, rows 44 px, no overflow', not a['bad'], a['bad'][:5])
        ok(f'{tag}: the back button reachable', a['back'], a)
        ok(f'{tag}: the list scrolls inside itself', a['sh'] <= a['ch'] + 1 or a['oy'] in ('auto', 'scroll'), a)
        L = (await pg.evaluate(ROWS))[0]
        if H > W: ok(f'{tag}: the long text is cut on one line with an ellipsis', L['tsw'] > L['tcw'] and L['th'] < 22 and L['ell'] == 'ellipsis', L)
        if name: await pg.screenshot(path=os.path.join(SHOTS, name))
        await finger(pg, '#mBack'); await pg.wait_for_timeout(400)
        ok(f'{tag}: back goes to Settings', await pg.evaluate("()=>document.querySelector('#menu .scr.on').id") == 'sSet')
        ok(f'{tag}: no console errors', not pg.errs, pg.errs[:3])
        await pg.context.close()


async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        for i, f in enumerate([part1, part2, part3], 1):
            if PART in (0, i): await f(b, url)
        await b.close()
    sys.exit(ok.done('bugs_tickets_check' + (f' part {PART}' if PART else '')))

asyncio.run(main())
