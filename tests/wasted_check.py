# Phone3 item 7: the WASTED crash screen. A crash in free flight (Hard and Easy, and the C-130 and the F-16):
# time runs at about 0.25x for 2.5 s (the sim advances a quarter of the real time), the picture goes black and
# white under a vignette, the explosion plays on, then WASTED in red with a dark outline and a soft drop shadow
# in Saira Condensed 800, held 1.5 s, then the crash card (not before). A tap during it skips to the card.
# Not in a Flight School lesson (the card comes the old way). RETRY from the card flies again in colour.
# The sequence costs no frame time: frame times during it against plain flight. iPhone 844x390.
# Run: .venv/bin/python tests/wasted_check.py
import asyncio, os, sys, time
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, finger, IPHONE_15, ROOT
ok = Checks()
K = 'window.__kgeu'
SHOTS = os.path.join(ROOT, 'overnight-screenshots', 'phone3', 'item7')

ST = """()=>{const K=window.__kgeu,w=document.getElementById('wasted'),t=w.querySelector('.wTxt'),cs=getComputedStyle(t),gl=getComputedStyle(K.R3().renderer.domElement);
  return {on:K.WST.on,wt:+K.WST.t.toFixed(2),body:document.body.classList.contains('wastedOn'),txt:w.classList.contains('txt'),op:+cs.opacity,
    font:cs.fontFamily,weight:cs.fontWeight,color:cs.color,stroke:cs.webkitTextStrokeWidth,strokeC:cs.webkitTextStrokeColor,shadow:cs.textShadow,
    filter:gl.filter,card:document.getElementById('crash').classList.contains('on'),sim:K.crashFx().t,crashed:K.state().crashed}}"""

async def run(pg, frames, dt=0.1):
    for _ in range(frames): await pg.evaluate(f"(d)=>{K}.stepFrame(d,false,false)", dt)

async def main():
    os.makedirs(SHOTS, exist_ok=True)
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        for skill, typ in (('pilot', 'cessna'), ('rookie', 'f16'), ('pilot', 'c130')):
            M = ('Hard ' if skill == 'pilot' else 'Easy ') + typ
            pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': skill, 'kgeuTut': '1', 'kgeuCoach': '3'})
            await pg.evaluate(f"()=>{{{K}.pick('{typ}');{K}.pickBase('kgeu');{K}.start('final');}}"); await pg.wait_for_timeout(400)
            await run(pg, 3)
            await pg.evaluate(f"()=>{K}.crashNow('Test crash.')")
            await run(pg, 1, 0.05)
            s0 = await pg.evaluate(ST)
            await run(pg, 10)   # 1 s of real time
            s1 = await pg.evaluate(ST)
            ok(f'{M}: slow motion, the explosion clock runs about a quarter of real time', s1['on'] and 0.2 <= (s1['sim'] - s0['sim']) / 1.0 <= 0.3, (s0['sim'], s1['sim']))
            await pg.wait_for_timeout(1000)   # the CSS fade is real time
            s1 = await pg.evaluate(ST)
            ok(f'{M}: black and white with a vignette, no word yet, no card', s1['body'] and 'grayscale(1)' in s1['filter'] and not s1['txt'] and not s1['card'], s1)
            if typ == 'cessna': await pg.screenshot(path=os.path.join(SHOTS, f'{skill}_{typ}_1s.png'))
            await run(pg, 16)   # 2.6 s
            await pg.wait_for_timeout(900)
            s2 = await pg.evaluate(ST)
            ok(f'{M}: WASTED at 2.5 s, still no card', s2['txt'] and s2['op'] > 0.95 and not s2['card'], s2)
            ok(f'{M}: red, dark outline, soft drop shadow, Saira Condensed 800',
               'Saira Condensed' in s2['font'] and s2['weight'] == '800' and s2['color'].startswith('rgb(212, 18, 28') and float(s2['stroke'].replace('px', '')) >= 3
               and s2['strokeC'].startswith('rgb(22, 3, 3') and 'px' in s2['shadow'], s2)
            await pg.screenshot(path=os.path.join(SHOTS, f'{skill}_{typ}_wasted.png'))
            await run(pg, 9)    # 3.5 s
            s3 = await pg.evaluate(ST)
            ok(f'{M}: held 1.5 s: still up at 3.5 s', s3['txt'] and not s3['card'], s3)
            await run(pg, 6)    # 4.1 s
            try: await pg.wait_for_function("()=>!/grayscale\\(1\\)/.test(getComputedStyle(window.__kgeu.R3().renderer.domElement).filter)", timeout=5000)
            except Exception: pass
            await pg.wait_for_timeout(1000)
            s4 = await pg.evaluate(ST)
            ok(f'{M}: then the crash card, in colour again', s4['card'] and not s4['on'] and not s4['body'] and 'grayscale(1)' not in s4['filter'], s4)
            await pg.screenshot(path=os.path.join(SHOTS, f'{skill}_{typ}_card.png'))
            await finger(pg, '#cRetry'); await run(pg, 2)
            s5 = await pg.evaluate(ST)
            ok(f'{M}: RETRY flies again, no WASTED left', not s5['crashed'] and not s5['on'] and not s5['body'] and not s5['card'], s5)
            # tap to skip
            await run(pg, 3); await pg.evaluate(f"()=>{K}.crashNow('Test crash.')"); await run(pg, 5)
            await pg.touchscreen.tap(422, 200); await pg.wait_for_timeout(300)
            s6 = await pg.evaluate(ST)
            ok(f'{M}: a tap skips straight to the card', s6['card'] and not s6['on'] and s6['wt'] < 1.0, s6)
            ok(f'{M}: no page errors', not pg.errs, pg.errs[:3])
            await pg.context.close()
        # Flight School: no WASTED
        pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'})
        await pg.evaluate(f"()=>{K}.startLesson('pattern',true)"); await pg.wait_for_timeout(400); await run(pg, 3)
        await pg.evaluate(f"()=>{K}.crashNow('Test crash.')"); await run(pg, 5)
        s = await pg.evaluate(ST)
        ok('lesson: no WASTED, no slow motion', not s['on'] and not s['body'], s)
        await run(pg, 30)
        ok('lesson: the card comes the old way', await pg.evaluate("()=>document.getElementById('crash').classList.contains('on')"))
        # frame cost: real frames (rendered) in plain flight against the WASTED sequence
        await pg.evaluate(f"()=>{{{K}.pick('cessna');{K}.start('final');}}"); await run(pg, 3)
        async def ftime(n=12):
            t0 = time.perf_counter(); await run(pg, n); return (time.perf_counter() - t0) / n
        f0 = await ftime()
        await pg.evaluate(f"()=>{K}.crashNow('Test crash.')")
        f1 = await ftime()
        ok(f'frame time during WASTED within 25% of plain flight ({f1*1000:.0f} ms vs {f0*1000:.0f} ms)', f1 < f0 * 1.25 + 0.01, (f0, f1))
        ok('no page errors', not pg.errs, pg.errs[:3])
        await b.close()
    srv.shutdown()
    sys.exit(ok.done('wasted_check'))

asyncio.run(main())
