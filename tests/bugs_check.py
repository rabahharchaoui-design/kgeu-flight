# Bugs1 item 5: the bug report form. The pause sheet's bug button and Settings > Report a bug open one sheet (#bugOv);
# the screenshot is the frame at the pause (bugShot), SEND posts to the fake Worker's /report (ui1_mock Mock), a 429
# keeps the sheet, no connection queues the report (kgeuBugQ) and it goes on 'online', a guest sends a 48 hex key of
# its own and no callsign. Break-ui: every target 44 px and inside the screen, the textarea at 16 px, SEND reachable,
# at 568x320, 844x390 and 390x844. Screenshots: overnight-screenshots/bugs1/item5/.
# Run: .venv/bin/python tests/bugs_check.py [--part N]   (1 pause and send, 2 settings, 429 and queue, 3 guest, 4 break-ui)
import asyncio, os, sys, base64, struct, re
from playwright.async_api import async_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import serve, launch, page, Checks, ROOT, finger, IPHONE_15
from ui1_mock import Mock

ok = Checks()
K = 'window.__kgeu'
SHOTS = os.path.join(ROOT, 'overnight-screenshots', 'bugs1', 'item5')
os.makedirs(SHOTS, exist_ok=True)
BASE = {'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'}
PART = int(sys.argv[sys.argv.index('--part') + 1]) if '--part' in sys.argv else 0
STATE = f'()=>{K}.bugState()'
TOAST = "()=>document.getElementById('toast').textContent"


def jpeg_size(url):
    """(bytes, width, height) of a data:image/jpeg URL, from its SOF marker"""
    raw = base64.b64decode(url.split(',', 1)[1])
    i = 2
    while i < len(raw) - 9:
        if raw[i] != 0xFF: i += 1; continue
        m = raw[i + 1]
        if m in (0xC0, 0xC1, 0xC2):
            h, w = struct.unpack('>HH', raw[i + 5:i + 9]); return len(raw), w, h
        i += 2 + struct.unpack('>H', raw[i + 2:i + 4])[0]
    return len(raw), 0, 0


def errs(pg):   # the 429 and 400 the test asks for show as a failed resource in the console
    return [e for e in pg.errs if 'status of 429' not in e and 'status of 400' not in e]


async def wait_for(pg, js, ms=6000):
    for _ in range(ms // 100):
        if await pg.evaluate(js): return True
        await pg.wait_for_timeout(100)
    return False


async def fly(pg):
    await pg.evaluate(f"()=>{{const r=document.getElementById('rotOk');if(r&&r.offsetParent)r.click();const K={K};K.pick('f16');K.pickBase('kgeu');K.start('runway');}}")
    await pg.wait_for_timeout(1500)


async def pick_and_type(pg, text):
    await finger(pg, '#bugCats .chip[data-cat="controls"]'); await pg.wait_for_timeout(150)
    await finger(pg, '#bugTx'); await pg.wait_for_timeout(150)
    await pg.keyboard.type(text); await pg.wait_for_timeout(150)


async def part1(b, url):
    m = Mock()
    st = dict(BASE); st.update(m.storage())
    pg = await page(b, url, vp=IPHONE_15, storage=st, pre=m.install)
    await fly(pg)
    ok('(1) no screenshot before any pause', await pg.evaluate(f'()=>{K}.bugShot()===null'))
    await finger(pg, '#bPause'); await pg.wait_for_timeout(900)
    r = await pg.evaluate("()=>{const e=document.getElementById('pBug');const q=e.getBoundingClientRect();return {w:q.width,h:q.height,lbl:e.getAttribute('aria-label'),txt:e.textContent,vis:getComputedStyle(e.querySelector('.bgL')).display!=='none'}}")
    ok('(1) the pause sheet has the bug button, at least 44x44, labelled', r['w'] >= 43.5 and r['h'] >= 43.5 and r['lbl'] == 'Report a bug' and '\U0001F41E' in r['txt'], r)
    ok('(1) at 844 wide the button reads Report beside the glyph', r['vis'], r)
    await pg.screenshot(path=os.path.join(SHOTS, 'pause_button.png'))
    shot = await pg.evaluate(f'()=>{K}.bugShot()')
    ok('(1) pausing took a screenshot: a data:image/jpeg URL', bool(shot) and shot['url'].startswith('data:image/jpeg;base64,'), shot and shot['url'][:40])
    if shot:
        n, w, h = jpeg_size(shot['url'])
        ok('(1) the screenshot is under 300 KB and at most 960 px each way', n < 300 * 1024 and 0 < w <= 960 and 0 < h <= 960, (n, w, h))
    await finger(pg, '#pBug'); await pg.wait_for_timeout(500)
    s = await pg.evaluate(STATE)
    ok('(1) the bug button opens the sheet, Annoying preselected, no category', s['open'] and s['cat'] is None and s['sev'] == 'annoying', s)
    ok('(1) SEND starts disabled', await pg.evaluate("()=>document.getElementById('bugSend').disabled"))
    ok('(1) the thumbnail shows the pause frame, the toggle reads Screenshot: On',
       await pg.evaluate("()=>{const i=document.getElementById('bugImg'),t=document.getElementById('bugShotT');return !i.hidden&&i.src.startsWith('data:image/jpeg')&&!t.hidden&&t.textContent==='Screenshot: On'}"))
    await finger(pg, '#bugCats .chip[data-cat="controls"]'); await pg.wait_for_timeout(150)
    ok('(1) a category alone does not enable SEND', await pg.evaluate("()=>document.getElementById('bugSend').disabled"))
    await finger(pg, '#bugTx'); await pg.wait_for_timeout(150)
    await pg.keyboard.type('Stick drifts!'); await pg.wait_for_timeout(200)
    ok('(1) Controls and text enable SEND', await pg.evaluate("()=>!document.getElementById('bugSend').disabled"))
    await pg.screenshot(path=os.path.join(SHOTS, 'form_844.png'))
    await finger(pg, '#bugSend')
    await wait_for(pg, f"()=>!{K}.bugState().open")
    ok('(1) the Worker got one report', len(m.reports) == 1, len(m.reports))
    if m.reports:
        r = m.reports[0]
        ok('(1) category controls, severity annoying, the text, the screenshot, the key, the callsign',
           r.get('category') == 'controls' and r.get('severity') == 'annoying' and r.get('text') == 'Stick drifts!' and str(r.get('shot', '')).startswith('data:image/jpeg')
           and r.get('key') == 'k' * 48 and r.get('cs') == 'ACEPILOT', {k: (v if k != 'shot' else str(v)[:30]) for k, v in r.items()})
        ok('(1) the context carries the version and the screen', isinstance(r.get('context'), dict) and r['context'].get('app') and re.match(r'^\d+x\d+@', r['context'].get('screen', '')), r.get('context'))
    t = await pg.evaluate(TOAST)
    ok('(1) the toast reads Ticket #7 sent', t == 'Ticket #7 sent ✅', t)
    s = await pg.evaluate(STATE)
    ok('(1) the sheet closed, text and category cleared', not s['open'] and s['text'] == '' and s['cat'] is None, s)
    # the toggle off sends no shot
    await finger(pg, '#pBug'); await pg.wait_for_timeout(500)
    await pick_and_type(pg, 'Second one')
    await finger(pg, '#bugShotT'); await pg.wait_for_timeout(150)
    tg = await pg.evaluate("()=>document.getElementById('bugShotT').textContent")
    ok('(1) the toggle reads Screenshot: Off', tg == 'Screenshot: Off', tg)
    await finger(pg, '#bugSend')
    await wait_for(pg, "()=>document.getElementById('toast').textContent.includes('#8')")
    ok('(1) toggled off: the report goes without the screenshot', len(m.reports) == 2 and 'shot' not in m.reports[1], len(m.reports))
    # Settings during a paused flight: the pause frame is reused
    sh0 = (await pg.evaluate(f'()=>{K}.bugShot()'))['at']
    await pg.evaluate(f"()=>{{{K}.openMenu();{K}.nav('sSet');{K}.bugOpen('settings')}}"); await pg.wait_for_timeout(500)
    s = await pg.evaluate(STATE)
    ok('(1) Settings during a paused flight reuses the pause frame', s['open'] and s['hasShot'] and (await pg.evaluate(f'()=>{K}.bugShot()'))['at'] == sh0, s)
    await pg.evaluate(f'()=>{K}.bugClose()')
    ok('(1) no console errors', not errs(pg), errs(pg)[:3])
    await pg.context.close()


async def part2(b, url):
    m = Mock()
    st = dict(BASE); st.update(m.storage())
    pg = await page(b, url, vp=IPHONE_15, storage=st, pre=m.install)
    await pg.evaluate(f"()=>{{{K}.openMenu();{K}.nav('sSet');}}"); await pg.wait_for_timeout(600)
    await pg.evaluate("()=>document.getElementById('bBug').scrollIntoView({block:'center'})"); await pg.wait_for_timeout(300)
    r = await pg.evaluate("()=>{const e=document.getElementById('bBug');const q=e.getBoundingClientRect();return {w:q.width,h:q.height,txt:e.textContent.trim(),row:e.closest('.srow').firstElementChild.textContent,chev:!!e.querySelector('.chev')}}")
    ok('(2) Settings has the Report a bug row (Bugs, the chevron, 44 px)', r['txt'] == 'Report a bug' and r['row'] == 'Bugs' and r['chev'] and r['h'] >= 43.5, r)
    await finger(pg, '#bBug'); await pg.wait_for_timeout(500)
    s = await pg.evaluate(STATE)
    th = await pg.evaluate("()=>({img:!document.getElementById('bugImg').hidden,tog:!document.getElementById('bugShotT').hidden,no:document.getElementById('bugNo').textContent,noVis:!!document.getElementById('bugNo').offsetParent})")
    ok('(2) from the menu with no flight: the sheet opens, no thumbnail, the toggle hidden', s['open'] and not th['img'] and not th['tog'] and th['no'] == 'No screenshot in the menu' and th['noVis'], (s, th))
    await pg.screenshot(path=os.path.join(SHOTS, 'form_settings.png'))
    await finger(pg, '#bugTx'); await pg.wait_for_timeout(150)
    await pg.keyboard.insert_text('x' * 1200); await pg.wait_for_timeout(200)
    n = await pg.evaluate("()=>document.getElementById('bugTx').value.length")
    c = await pg.evaluate("()=>{const e=document.getElementById('bugN');return {t:e.textContent,v:!e.hidden}}")
    ok('(2) a 1,200 character paste is kept at 1,000, the counter reads 1000 / 1000', n == 1000 and c['v'] and c['t'] == '1000 / 1000', (n, c))
    fs = await pg.evaluate("()=>parseFloat(getComputedStyle(document.getElementById('bugTx')).fontSize)")
    ok('(2) the textarea is 16 px (iOS never zooms)', fs >= 16, fs)
    await pg.evaluate("()=>{const t=document.getElementById('bugTx');t.value='';t.dispatchEvent(new Event('input'))}")
    # a 429 keeps the sheet
    m.extra['report'] = {'status': 429, 'body': {'error': 'rate'}}
    await pick_and_type(pg, 'Limit test')
    await finger(pg, '#bugSend'); await pg.wait_for_timeout(1200)
    s = await pg.evaluate(STATE); t = await pg.evaluate(TOAST)
    ok('(2) a 429: the sheet stays, the toast says the daily limit', s['open'] and t == 'Daily report limit reached, try again tomorrow' and s['text'] == 'Limit test', (s, t))
    tip = await pg.evaluate("()=>{const e=document.getElementById('bugTip');return e.classList.contains('on')&&e.textContent}")
    ok('(2) the message shows above the menu too (bugTip)', tip == 'Daily report limit reached, try again tomorrow', tip)
    m.extra.pop('report')
    # a 400 keeps the sheet with the reason
    m.extra['report'] = {'status': 400, 'body': {'error': 'bad', 'reason': 'text length 0, 1 to 1000'}}
    await finger(pg, '#bugSend'); await pg.wait_for_timeout(1200)
    s = await pg.evaluate(STATE); t = await pg.evaluate(TOAST)
    ok('(2) a 400: the sheet stays, Not sent: <reason>', s['open'] and t == 'Not sent: text length 0, 1 to 1000', (s, t))
    m.extra.pop('report')
    await finger(pg, '#bugSend')
    await wait_for(pg, f"()=>!{K}.bugState().open")
    t = await pg.evaluate(TOAST)
    ok('(2) from Settings with no flight: sent with no screenshot, Ticket #7', t == 'Ticket #7 sent ✅' and 'shot' not in m.reports[-1], (t, len(m.reports)))
    # no connection: queued, then sent on 'online'
    n0 = len(m.reports)
    m.offline = True
    await pg.evaluate("()=>document.getElementById('bBug').scrollIntoView({block:'center'})"); await pg.wait_for_timeout(300)
    await finger(pg, '#bBug'); await pg.wait_for_timeout(500)
    await pick_and_type(pg, 'Queued one')
    await finger(pg, '#bugSend')
    await wait_for(pg, f"()=>!{K}.bugState().open")
    s = await pg.evaluate(STATE); t = await pg.evaluate(TOAST)
    ok('(2) no connection: queued (1), the sheet closed, Saved, sends when you are back online', s['queued'] == 1 and not s['open'] and t == 'Saved, sends when you are back online', (s, t))
    m.offline = False
    await pg.evaluate("()=>dispatchEvent(new Event('online'))")
    await wait_for(pg, f"()=>{K}.bugState().queued===0")
    t = await pg.evaluate(TOAST)
    ok('(2) back online: the queue drains, Queued report sent: ticket #8', len(m.reports) == n0 + 1 and t == 'Queued report sent: ticket #8' and (await pg.evaluate(STATE))['queued'] == 0, (len(m.reports) - n0, t))
    if len(m.reports) > n0: ok('(2) the queued report kept its text', m.reports[-1].get('text') == 'Queued one', m.reports[-1].get('text'))
    ok('(2) no console errors', not errs(pg), errs(pg)[:3])
    await pg.context.close()


async def part3(b, url):
    m = Mock(cs=None)
    st = dict(BASE); st.update(m.storage())
    pg = await page(b, url, vp=IPHONE_15, storage=st, pre=m.install)
    await pg.wait_for_timeout(600)
    keys = []
    for i in range(2):
        await pg.evaluate(f"()=>{K}.bugOpen('settings')"); await pg.wait_for_timeout(400)
        await pick_and_type(pg, 'Guest report %d' % i)
        await finger(pg, '#bugSend')
        await wait_for(pg, f"()=>!{K}.bugState().open")
        await pg.wait_for_timeout(200)
    ok('(3) a guest sent two reports', len(m.reports) == 2, len(m.reports))
    if len(m.reports) == 2:
        k0, k1 = m.reports[0].get('key'), m.reports[1].get('key')
        ok('(3) a guest sends no callsign', 'cs' not in m.reports[0] and 'cs' not in m.reports[1], [r.get('cs') for r in m.reports])
        ok('(3) a guest sends a 48 hex key, the same on the second report', bool(re.fullmatch(r'[0-9a-f]{48}', k0 or '')) and k0 == k1, (k0, k1))
        ok('(3) the key is kept in kgeuBugKey', await pg.evaluate("()=>localStorage.getItem('kgeuBugKey')") == k0)
    ok('(3) no console errors', not errs(pg), errs(pg)[:3])
    await pg.context.close()


AUDIT = """()=>{const ov=document.getElementById('bugOv'),sh=ov.querySelector('.sheet'),W=innerWidth,H=innerHeight,bad=[];
  const bs=[...ov.querySelectorAll('button')].filter(b=>b.offsetParent);
  bs.forEach(b=>{const r=b.getBoundingClientRect(),id=b.id||b.dataset.cat||b.dataset.sev||b.textContent.trim().slice(0,12);
    if(r.height<43.5||r.width<43.5)bad.push('small '+id+' '+Math.round(r.width)+'x'+Math.round(r.height));
    if(r.left<-0.5||r.right>W+0.5)bad.push('off sideways '+id);
    if(b.scrollWidth>b.clientWidth+1)bad.push('text cut '+id);});
  const q=sh.getBoundingClientRect();if(q.top<-0.5||q.bottom>H+0.5||q.left<-0.5||q.right>W+0.5)bad.push('sheet outside the screen');
  const tx=document.getElementById('bugTx');
  return {bad:bad,n:bs.length,fs:parseFloat(getComputedStyle(tx).fontSize),sh:sh.scrollHeight,ch:sh.clientHeight,oy:getComputedStyle(sh).overflowY,ob:getComputedStyle(sh).overscrollBehaviorY,
    cols:getComputedStyle(sh).gridTemplateColumns.split(' ').length}}"""
REACH = """()=>{const sh=document.querySelector('#bugOv .sheet'),s=document.getElementById('bugSend');s.scrollIntoView({block:'nearest'});
  const r=s.getBoundingClientRect(),q=sh.getBoundingClientRect();return r.top>=q.top-0.5&&r.bottom<=q.bottom+0.5&&r.bottom<=innerHeight+0.5}"""


async def part4(b, url):
    m = Mock()
    for W, H, name in [(568, 320, 'form_568.png'), (844, 390, None), (390, 844, 'form_390p.png')]:
        st = dict(BASE); st.update(m.storage())
        pg = await page(b, url, vp={'width': W, 'height': H}, storage=st, pre=m.install)
        await fly(pg)
        await finger(pg, '#bPause'); await pg.wait_for_timeout(900)
        a0 = await pg.evaluate("()=>{const e=document.getElementById('pBug'),q=e.getBoundingClientRect();return {w:q.width,h:q.height,in:q.right<=innerWidth+0.5&&q.bottom<=innerHeight+0.5}}")
        tag = f'{W}x{H}'
        ok(f'(4) {tag}: the bug button is 44 px and on screen', a0['w'] >= 43.5 and a0['h'] >= 43.5 and a0['in'], a0)
        await finger(pg, '#pBug'); await pg.wait_for_timeout(500)
        await pg.evaluate("()=>{document.querySelector('#bugCats .chip[data-cat=\"graphics\"]').click();const t=document.getElementById('bugTx');t.value='The runway lights flicker at dusk when I turn final over the city.';t.dispatchEvent(new Event('input'))}")
        await pg.wait_for_timeout(250)
        a = await pg.evaluate(AUDIT)
        ok(f'(4) {tag}: every button and chip 44 px, inside the screen, no text cut', not a['bad'] and a['n'] >= 14, (a['bad'][:6], a['n']))
        ok(f'(4) {tag}: the textarea at 16 px or more', a['fs'] >= 16, a['fs'])
        ok(f'(4) {tag}: the sheet fits or scrolls inside itself (contain)', (a['sh'] <= a['ch'] + 1) or (a['oy'] in ('auto', 'scroll') and a['ob'] == 'contain'), a)
        ok(f'(4) {tag}: {"one column" if H > W else "two columns"}', a['cols'] == (1 if H > W else 2), a['cols'])
        if name: await pg.screenshot(path=os.path.join(SHOTS, name))
        ok(f'(4) {tag}: SEND reachable', await pg.evaluate(REACH))
        if W == 568: await pg.screenshot(path=os.path.join(SHOTS, 'form_568_scrolled.png'))
        ok(f'(4) {tag}: no console errors', not errs(pg), errs(pg)[:3])
        await pg.context.close()


async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        for i, f in enumerate([part1, part2, part3, part4], 1):
            if PART in (0, i): await f(b, url)
        await b.close()
    sys.exit(ok.done('bugs_check' + (f' part {PART}' if PART else '')))

asyncio.run(main())
