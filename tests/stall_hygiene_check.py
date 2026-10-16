# Fix2 item 1: Stutter log hygiene. A gap over STALL.thr that is not a freeze is never logged, only counted in
# STALL.skip: hidden (the page hidden in the gap or the first frame back), paused (paused at the gap's start and still
# paused) and idle (an 'outside' gap while not flying: the menu up). A gap that starts paused and ends running is logged
# with 'resume'. In flight a stall inside the frame callback (__kgeu.stallSpin) is logged as before.
# Cases: A in flight stallSpin(400) logged; B paused busy loop skipped (paused); C the resume gap; D menu busy loop
# skipped (idle); E hidden busy loop skipped (hidden); F the Stutter log's #bStallSkip line and the Copy JSON's skip;
# G the skip counters survive a reload. Run: .venv/bin/python tests/stall_hygiene_check.py
import asyncio, json, os, sys
from playwright.async_api import async_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import serve, launch, page, Checks, finger, IPHONE_15

ok = Checks()
K = 'window.__kgeu'
BASE = {'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3', 'kgeuTOD': 'day'}
BUSY = "const e=performance.now()+400;while(performance.now()<e);"
FRAMES = "()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(()=>requestAnimationFrame(r))))"
HID = "(v)=>{if(v)Object.defineProperty(Document.prototype,'hidden',{configurable:true,get(){return true;}});else delete Document.prototype.hidden;}"


async def stalls(pg):
    return await pg.evaluate(f"()=>{K}.stalls()")


def big(s, n0, ms=390):
    return [r for r in s['log'][n0:] if r['gap'] >= ms]


async def run(b, url):
    pg = await page(b, url, vp=IPHONE_15, storage=BASE)
    if os.environ.get('DBG'): pg.on('console', lambda m: print('       ', m.text) if '[stall]' in m.text else None)
    await pg.evaluate(f"()=>{{const r=document.getElementById('rotOk');if(r&&r.offsetParent)r.click();const K={K};K.pick('f16');K.pickBase('kgeu');K.start('runway');}}")
    await pg.wait_for_timeout(3000)
    await pg.evaluate(f"()=>{K}.stallsThr(200)")
    ok('flying', await pg.evaluate(f"()=>{K}.running()&&!{K}.paused()"))

    # A: an in-frame stall in flight
    s0 = await stalls(pg)
    await pg.evaluate(f"()=>{K}.stallSpin(400)"); await pg.evaluate(FRAMES)
    s1 = await stalls(pg)
    sp = [r for r in s1['log'][len(s0['log']):] if r['tick'] >= 390]
    ok('A: in-flight stallSpin(400) logged, count up', len(sp) == 1 and s1['count'] > s0['count'], [r['tags'] for r in sp])
    ok('A: no hidden or resume tag', sp and not ({'hidden', 'resume', 'outside'} & set(sp[0]['tags'])), sp and sp[0]['tags'])

    # B: paused, the main thread blocked
    await finger(pg, '#bPause'); await pg.wait_for_timeout(600)
    ok('B: paused', await pg.evaluate(f"()=>{K}.paused()"))
    s0 = await stalls(pg)
    await pg.evaluate(f"()=>{{{BUSY}}}"); await pg.evaluate(FRAMES)
    s1 = await stalls(pg)
    ok('B: paused gap not logged', len(s1['log']) == len(s0['log']) and s1['count'] == s0['count'], len(s1['log']) - len(s0['log']))
    ok('B: skip.paused up', s1['skip']['paused'] > s0['skip']['paused'], s1['skip'])

    # C: the resume gap
    # the snapshot in the same task as the busy loop and the click: no paused headless frame (~300 ms) slips between
    s0 = await pg.evaluate(f"()=>{{const s={K}.stalls();{BUSY}document.getElementById('pResume').click();return s;}}")
    await pg.evaluate(FRAMES)
    s1 = await stalls(pg)
    nb = s1['log'][len(s0['log']):][:1]
    ok('C: running again', await pg.evaluate(f"()=>!{K}.paused()"))
    ok('C: the resume gap is not counted as paused', s1['skip']['paused'] == s0['skip']['paused'], s1['skip'])
    ok('C: if logged, tagged resume', all('resume' in r['tags'] for r in nb), [r['tags'] for r in nb])
    print('       resume gap logged:', bool(nb), nb[0]['tags'] if nb else '')

    # D: the menu, the phone idle
    await pg.evaluate(f"()=>{K}.openMenu()"); await pg.wait_for_timeout(800)
    s0 = await stalls(pg)
    await pg.evaluate(f"()=>{{{BUSY}}}"); await pg.evaluate(FRAMES)
    s1 = await stalls(pg)
    ok('D: menu gap not logged', not big(s1, len(s0['log'])), [r['tags'] for r in big(s1, len(s0['log']))])
    ok('D: skip.idle up', s1['skip']['idle'] > s0['skip']['idle'], s1['skip'])

    # E: hidden
    s0 = s1
    await pg.evaluate(HID, True)
    await pg.evaluate(f"()=>{{document.dispatchEvent(new Event('visibilitychange'));{BUSY}}}")
    await pg.evaluate(HID, False)
    await pg.evaluate("()=>document.dispatchEvent(new Event('visibilitychange'))"); await pg.evaluate(FRAMES)
    s1 = await stalls(pg)
    ok('E: hidden gap not logged', not big(s1, len(s0['log'])), [r['tags'] for r in big(s1, len(s0['log']))])
    ok('E: skip.hidden up', s1['skip']['hidden'] > s0['skip']['hidden'], s1['skip'])
    ok('E: no hidden entry anywhere in the log', not any('hidden' in r['tags'] for r in s1['log']))

    # F: the Stutter log screen and the Copy JSON
    await pg.evaluate(f"()=>{{{K}.openMenu('sSet');}}"); await pg.wait_for_timeout(300)
    await pg.evaluate("()=>document.getElementById('bStalls').click()"); await pg.wait_for_timeout(400)
    t = await pg.evaluate("()=>{const e=document.getElementById('bStallSkip');return e&&e.offsetParent&&!e.hidden?e.textContent:null}")
    ok('F: #bStallSkip shown with hidden, paused, idle', bool(t) and all(w in t for w in ('hidden', 'paused', 'idle')), t)
    await pg.screenshot(path='/tmp/stall_hygiene_F.png')
    j = json.loads(await pg.evaluate(f"()=>{K}.stallsJSON()"))
    ok('F: Copy JSON carries skip', isinstance(j.get('skip'), dict) and set(j['skip']) == {'hidden', 'paused', 'idle', 'worst'}, j.get('skip'))
    ok('F: Copy JSON log has no hidden entries', not any('hidden' in r['tags'] for r in j['log'] + j['prev']))

    # G: the skip counters survive a reload
    await pg.wait_for_timeout(2500)
    before = (await stalls(pg))['skipAll']
    await pg.reload(); await pg.wait_for_function('()=>window.__kgeu', timeout=30000); await pg.wait_for_timeout(500)
    after = (await stalls(pg))['skipAll']
    ok('G: skip summary survives a reload', all(after[k] >= before[k] for k in ('hidden', 'paused', 'idle')), (before, after))
    ok('no page errors', not pg.errs, pg.errs[:3])


async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        await run(b, url)
        await b.close()
    srv.shutdown()
    sys.exit(ok.done('stall_hygiene_check'))

asyncio.run(main())
