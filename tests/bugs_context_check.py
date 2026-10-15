# Bugs1 item 6: the report's auto context and the one-time prompt. bugContext() carries every key (the phone, the game's
# state, fps, gfx, the console ring), the ring keeps the last 20 console errors and warnings plus uncaught errors and
# rejections with keys and tokens cut out; after an uncaught error (past the first 5 s) or a long stall in flight a small
# banner asks "Something broke. Report it?" once a session: REPORT pauses through the pause path (the screenshot) and
# opens the form with Crash or freeze (an error) or Screen or graphics (a stall) picked; it hides by itself after 8 s and
# never shows in the menu. Clear of the pause button, the stick zone and the throttle at 844x390, 568x320 and 390x844.
# Screenshots: overnight-screenshots/bugs1/item6/. Run: .venv/bin/python tests/bugs_context_check.py [--part N]
# (1 context and ring, 2 the error prompt at three sizes and the send, 3 menu, stall prompt, auto hide)
import asyncio, os, sys
from playwright.async_api import async_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import serve, launch, page, Checks, ROOT, finger, IPHONE_15
from ui1_mock import Mock

ok = Checks()
K = 'window.__kgeu'
SHOTS = os.path.join(ROOT, 'overnight-screenshots', 'bugs1', 'item6')
os.makedirs(SHOTS, exist_ok=True)
BASE = {'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3', 'kgeuTOD': 'day'}
PART = int(sys.argv[sys.argv.index('--part') + 1]) if '--part' in sys.argv else 0
INJ = ('boom', 'hmm', 'ring ', '[hex]', 'key=', 'token=', 'status of 4')   # the test's own console lines
KEYS = ['app', 'device', 'screen', 'os', 'browser', 'gfx', 'fps', 'ac', 'mode', 'region', 'base', 'tod', 'scr', 'running',
        'paused', 'up', 'online', 'lang', 'mem', 'cs', 'errors']


def errs(pg):
    return [e for e in pg.errs if not any(k in e for k in INJ)]


async def wait_for(pg, js, ms=6000):
    for _ in range(ms // 100):
        if await pg.evaluate(js): return True
        await pg.wait_for_timeout(100)
    return False


async def fly(pg):
    await pg.evaluate(f"()=>{{const r=document.getElementById('rotOk');if(r&&r.offsetParent)r.click();const K={K};K.pick('f16');K.pickBase('kgeu');K.start('runway');}}")
    await pg.wait_for_timeout(1500)


async def past5(pg):
    await wait_for(pg, '()=>performance.now()>5200', 12000)


SHOWN = f"()=>{K}.bugAskShown()"
GEOM = """()=>{const R=id=>{const e=document.getElementById(id);if(!e)return null;const q=e.getBoundingClientRect();
    if(!q.width||!q.height||getComputedStyle(e).display==='none')return null;return {l:q.left,t:q.top,r:q.right,b:q.bottom};};
  const a=R('bugAsk'),g=R('bugAskGo'),x=R('bugAskX'),bad=[],W=innerWidth,H=innerHeight;
  const hit=(p,q)=>p&&q&&p.l<q.r-0.5&&q.l<p.r-0.5&&p.t<q.b-0.5&&q.t<p.b-0.5;
  ['bPause','stickZone','thr','thrCol'].forEach(id=>{if(hit(a,R(id)))bad.push('covers #'+id);});
  if(a.l<-0.5||a.t<-0.5||a.r>W+0.5||a.b>H+0.5)bad.push('outside the viewport');
  const vis=getComputedStyle(document.getElementById('bugAsk'));
  return {bad:bad,go:g&&{w:g.r-g.l,h:g.b-g.t},x:x&&{w:x.r-x.l,h:x.b-x.t},txt:document.querySelector('#bugAsk span').textContent,
    op:+vis.opacity,vis:vis.visibility,a:a}}"""


async def part1(b, url):
    m = Mock()
    st = dict(BASE); st.update(m.storage())
    pg = await page(b, url, vp=IPHONE_15, storage=st, pre=m.install)
    menu = await pg.evaluate(f'()=>{K}.bugContext()')
    ok('(1) in the menu: scr is the menu screen, fps null, running false', menu['scr'].startswith('s') and menu['fps'] is None and menu['running'] is False, (menu['scr'], menu['fps']))
    await fly(pg)
    await wait_for(pg, f'()=>{K}.fpsStats().n>3', 8000)
    c = await pg.evaluate(f'()=>{K}.bugContext()')
    ok('(1) every key is there', all(k in c for k in KEYS), [k for k in KEYS if k not in c])
    ok('(1) F-16 at Glendale by day: ac f16, region az, a base, tod day, scr free, running',
       c['ac'] == 'f16' and c['region'] == 'az' and bool(c['base']) and c['tod'] == 'day' and c['scr'] == 'free' and c['running'] is True and c['paused'] is False,
       {k: c[k] for k in ('ac', 'region', 'base', 'tod', 'scr', 'running', 'paused')})
    ok('(1) fps numbers', isinstance(c['fps'], dict) and isinstance(c['fps'].get('avg'), (int, float)) and isinstance(c['fps'].get('low1'), (int, float)), c['fps'])
    ok('(1) gfx tier and scale', isinstance(c['gfx'], dict) and bool(c['gfx'].get('tier')) and isinstance(c['gfx'].get('scale'), (int, float)), c['gfx'])
    ok('(1) device, os, browser non-empty strings; app the version; screen WxH@dpr', all(isinstance(c[k], str) and c[k] for k in ('device', 'os', 'browser', 'app'))
       and c['screen'].startswith('844x390@') and 'landscape' in c['screen'] and 'PWA no' in c['screen'], {k: c[k] for k in ('device', 'os', 'browser', 'app', 'screen')})
    ok('(1) cs, online, up, mode, errors an array', c['cs'] == 'ACEPILOT' and c['online'] is True and isinstance(c['up'], int) and c['mode'] in ('easy', 'hard') and isinstance(c['errors'], list),
       {k: c[k] for k in ('cs', 'online', 'up', 'mode')})
    ok('(1) every string at most 120 chars', all(len(v) <= 120 for v in c.values() if isinstance(v, str)))
    # the device guess on iPhone and Android user agents
    g = await pg.evaluate("""()=>{const K=window.__kgeu,o={};const set=(ua,w,h,d,mtp)=>{Object.defineProperty(navigator,'userAgent',{value:ua,configurable:true});
        Object.defineProperty(screen,'width',{value:w,configurable:true});Object.defineProperty(screen,'height',{value:h,configurable:true});
        Object.defineProperty(window,'devicePixelRatio',{value:d,configurable:true});Object.defineProperty(navigator,'maxTouchPoints',{value:mtp||5,configurable:true});
        const c=K.bugContext();return [c.device,c.os,c.browser];};
      o.i15=set('Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1',393,852,3);
      o.se=set('Mozilla/5.0 (iPhone; CPU iPhone OS 16_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Mobile/15E148 Safari/604.1',375,667,2);
      o.odd=set('Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148',401,873,3);
      o.and=set('Mozilla/5.0 (Linux; Android 14; Pixel 8 Build/UD1A.230803.041) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.43 Mobile Safari/537.36',412,915,2.6);
      o.ipad=set('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',820,1180,2,5);
      return o;}""")
    ok('(1) iPhone 393x852@3 iOS 17.4 Safari', g['i15'] == ['iPhone 14 Pro/15/16 class', 'iOS 17.4', 'Safari 17.4'], g['i15'])
    ok('(1) iPhone 375x667@2: iPhone SE class', g['se'][0] == 'iPhone SE class' and g['se'][1] == 'iOS 16.1', g['se'])
    ok('(1) an unknown iPhone: iPhone WxH, WebView without Safari', g['odd'] == ['iPhone 401x873', 'iOS 18.0', 'WebView'], g['odd'])
    ok('(1) Android: the model, Android 14, Chrome', g['and'] == ['Pixel 8', 'Android 14', 'Chrome 120.0.6099.43'], g['and'])
    ok('(1) an iPad as a Mac with touch: iPad', g['ipad'][0] == 'iPad' and g['ipad'][1] == 'iPadOS 17.2', g['ipad'])
    await pg.reload(); await pg.wait_for_function('()=>window.__kgeu&&window.__kgeu.bugLog', timeout=30000)
    await pg.wait_for_timeout(500)
    # the ring
    await pg.evaluate("()=>{console.error('boom');console.warn('hmm');setTimeout(()=>{throw new Error('kaboom')},0);}")
    await pg.wait_for_timeout(300)
    L = await pg.evaluate(f'()=>{K}.bugLog()')
    find = lambda k, s: any(e['k'] == k and s in e['m'] for e in L)
    ok('(1) the ring: boom (error), hmm (warn), kaboom (uncaught)', find('error', 'boom') and find('warn', 'hmm') and find('uncaught', 'kaboom'), [(e['k'], e['m'][:40]) for e in L][-4:])
    ok('(1) each entry {t, k, m}, m at most 300', all(set(e) == {'t', 'k', 'm'} and len(e['m']) <= 300 for e in L))
    await pg.evaluate("()=>{for(let i=0;i<25;i++)console.error('ring '+i+' '+'x'.repeat(400))}")
    L = await pg.evaluate(f'()=>{K}.bugLog()')
    ok('(1) 25 more errors: the ring keeps 20, the newest last, cut to 300', len(L) == 20 and L[-1]['m'].startswith('ring 24') and all(len(e['m']) <= 300 for e in L), (len(L), L[-1]['m'][:12]))
    await pg.evaluate("()=>console.error('key=abcdef0123456789 token=x.y and https://pfs.test/x?key=zz&a=1')")
    e = (await pg.evaluate(f'()=>{K}.bugLog()'))[-1]['m']
    ok('(1) the key strip: no key, no token, no query string', 'abcdef0123456789' not in e and 'x.y' not in e and 'zz' not in e and 'a=1' not in e, e)
    await pg.evaluate("()=>{Promise.reject(new Error('boomp'));}")
    await pg.wait_for_timeout(300)
    L = await pg.evaluate(f'()=>{K}.bugLog()')
    ok('(1) an unhandled rejection is kept as promise', any(x['k'] == 'promise' and 'boomp' in x['m'] for x in L), L[-1])
    c = await pg.evaluate(f'()=>{K}.bugContext()')
    import json
    n = len(json.dumps(c, separators=(',', ':'), ensure_ascii=False))
    ok('(1) the context with a full ring stays under 6,000 chars', n < 6000 and len(c['errors']) >= 1, (n, len(c['errors'])))
    ok('(1) no console errors from the game', not errs(pg), errs(pg)[:3])
    await pg.context.close()


async def part2(b, url):
    for W, H, name in [(844, 390, 'prompt_844.png'), (568, 320, 'prompt_568.png'), (390, 844, 'prompt_390p.png')]:
        m = Mock()
        st = dict(BASE); st.update(m.storage())
        pg = await page(b, url, vp={'width': W, 'height': H}, storage=st, pre=m.install)
        tag = f'{W}x{H}'
        await fly(pg); await past5(pg)
        ok(f'(2) {tag}: not asked yet', not await pg.evaluate(f'()=>{K}.bugAsked()'))
        await pg.evaluate("()=>setTimeout(()=>{throw new Error('kaboom')},0)")
        await pg.wait_for_timeout(700)
        ok(f'(2) {tag}: the uncaught error shows the banner, asked', await pg.evaluate(SHOWN) and await pg.evaluate(f'()=>{K}.bugAsked()'))
        g = await pg.evaluate(GEOM)
        ok(f'(2) {tag}: the text, opacity 1, visible', g['txt'] == 'Something broke. Report it?' and g['op'] > 0.99 and g['vis'] == 'visible', g)
        ok(f'(2) {tag}: REPORT and the dismiss at least 44 px', g['go']['h'] >= 43.5 and g['go']['w'] >= 43.5 and g['x']['h'] >= 43.5 and g['x']['w'] >= 43.5, (g['go'], g['x']))
        ok(f'(2) {tag}: inside the viewport, clear of the pause button, the stick zone and the throttle', not g['bad'], (g['bad'], g['a']))
        hit = await pg.evaluate("()=>{const e=document.getElementById('bugAskGo'),q=e.getBoundingClientRect(),h=document.elementFromPoint(q.x+q.width/2,q.y+q.height/2);return e===h||e.contains(h)}")
        ok(f'(2) {tag}: REPORT is on top where it is', hit)
        await pg.screenshot(path=os.path.join(SHOTS, name))
        await finger(pg, '#bugAskGo')
        await wait_for(pg, f'()=>{K}.bugState().open', 3000)
        await wait_for(pg, f'()=>!!{K}.bugShot()', 6000)
        s = await pg.evaluate(f'()=>{K}.bugState()')
        ok(f'(2) {tag}: REPORT paused the flight, the form opens with Crash or freeze, empty text, the screenshot taken',
           await pg.evaluate(f'()=>{K}.paused()') and s['open'] and s['cat'] == 'crash' and s['text'] == '' and await pg.evaluate(f'()=>!!{K}.bugShot()') and s['hasShot'], s)
        ok(f'(2) {tag}: the banner went', not await pg.evaluate(SHOWN))
        if W == 844:
            await finger(pg, '#bugTx'); await pg.wait_for_timeout(150)
            await pg.keyboard.type('It froze'); await pg.wait_for_timeout(200)
            await finger(pg, '#bugSend')
            await wait_for(pg, f'()=>!{K}.bugState().open')
            r = m.reports[0] if m.reports else {}
            cx = r.get('context') or {}
            ok('(2) the sent report: category crash, context errors carry kaboom, scr free',
               r.get('category') == 'crash' and any('kaboom' in e.get('m', '') for e in cx.get('errors', [])) and cx.get('scr') == 'free', (r.get('category'), cx.get('scr'), [e.get('m', '')[:30] for e in cx.get('errors', [])]))
        else:
            await pg.evaluate(f'()=>{K}.bugClose()'); await pg.wait_for_timeout(300)
        await finger(pg, '#pResume'); await pg.wait_for_timeout(400)
        await pg.evaluate("()=>setTimeout(()=>{throw new Error('kaboom again')},0)")
        await pg.wait_for_timeout(600)
        ok(f'(2) {tag}: a second error shows no second banner', not await pg.evaluate(SHOWN) and await pg.evaluate(f'()=>{K}.bugAsked()'))
        ok(f'(2) {tag}: no console errors from the game', not errs(pg), errs(pg)[:3])
        await pg.context.close()


async def part3(b, url):
    m = Mock()
    st = dict(BASE); st.update(m.storage())
    pg = await page(b, url, vp=IPHONE_15, storage=st, pre=m.install)
    await past5(pg)
    r = await pg.evaluate(f"()=>{K}.bugAsk('error')")
    ok('(3) in the menu: bugAsk shows nothing and asked stays false', r is False and not await pg.evaluate(SHOWN) and not await pg.evaluate(f'()=>{K}.bugAsked()'))
    await fly(pg)
    await finger(pg, '#bPause'); await pg.wait_for_timeout(600)
    ok('(3) on the pause sheet: nothing either', await pg.evaluate(f"()=>{K}.bugAsk('stall')") is False and not await pg.evaluate(f'()=>{K}.bugAsked()'))
    await finger(pg, '#pResume'); await pg.wait_for_timeout(400)
    ok('(3) in flight: bugAsk(stall) shows the banner', await pg.evaluate(f"()=>{K}.bugAsk('stall')") is True and await pg.evaluate(SHOWN))
    await pg.wait_for_timeout(400)
    await finger(pg, '#bugAskGo')
    await wait_for(pg, f'()=>{K}.bugState().open', 3000)
    s = await pg.evaluate(f'()=>{K}.bugState()')
    ok('(3) REPORT after a stall: the form with Screen or graphics, paused', s['open'] and s['cat'] == 'graphics' and await pg.evaluate(f'()=>{K}.paused()'), s)
    ok('(3) no console errors from the game', not errs(pg), errs(pg)[:3])
    await pg.context.close()
    # the auto hide, and the dismiss
    pg = await page(b, url, vp=IPHONE_15, storage=st, pre=m.install)
    await fly(pg); await past5(pg)
    await pg.evaluate(f"()=>{K}.bugAsk('stall')")
    await pg.wait_for_timeout(6000)
    on6 = await pg.evaluate(SHOWN)
    await pg.wait_for_timeout(3000)
    g = await pg.evaluate(GEOM)
    ok('(3) the banner holds at 6 s and has gone by itself at 9 s', on6 and not await pg.evaluate(SHOWN) and g['vis'] == 'hidden', (on6, g['vis'], g['op']))
    ok('(3) no console errors from the game', not errs(pg), errs(pg)[:3])
    await pg.context.close()
    pg = await page(b, url, vp=IPHONE_15, storage=st, pre=m.install)
    await fly(pg); await past5(pg)
    await pg.evaluate(f"()=>{K}.bugAsk('error')"); await pg.wait_for_timeout(400)
    await finger(pg, '#bugAskX'); await pg.wait_for_timeout(500)
    ok('(3) the dismiss hides it, the flight keeps going', not await pg.evaluate(SHOWN) and not await pg.evaluate(f'()=>{K}.paused()') and not await pg.evaluate(f'()=>{K}.bugState().open'))
    await pg.context.close()


async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        for i, f in enumerate([part1, part2, part3], 1):
            if PART in (0, i): await f(b, url)
        await b.close()
    sys.exit(ok.done('bugs_context_check' + (f' part {PART}' if PART else '')))

asyncio.run(main())
