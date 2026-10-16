# Fix2 item 7: every control in Settings can be tapped. The footer (Made by @OhRabah, the map,
# runway and terrain credits, the Add to Home Screen tip) used to sit below the rows' scroll box,
# which clipped the sixth row (Bugs: Report a bug, My tickets, Stutter log) under it at 844x390 and
# 667x375, so a tap at #bBug's centre landed on .setFoot. Now the footer scrolls with the rows,
# under the last one, and takes no taps itself (only its YouTube link does).
# For every visible button, input and link in #sSet at 568x320, 667x375, 844x390, 932x430 and
# portrait 390x844: scroll it into view (the grid scrolls at 568 and portrait), then
# document.elementsFromPoint at its centre must resolve to the control or a descendant first.
# At 667, 844 and 932 the six rows must also fit with no scrolling and clear the footer and the
# bottom fade. Shots: overnight-screenshots/fix2/item7/settings_<w>x<h>.png (--shots).
# Run: .venv/bin/python -u tests/settings_tap_check.py [--size 844x390] [--shots]
import asyncio, os, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, PLACED
ok = Checks()
OUT = os.path.join(os.path.dirname(__file__), '..', 'overnight-screenshots', 'fix2', 'item7')
SIZES = [(568, 320), (667, 375), (844, 390), (932, 430), (390, 844)]
TAP = """async()=>{const g=document.querySelector('#sSet .setGrid'),f=document.querySelector('#sSet .setFoot');
  const nm=e=>e?(e.id?'#'+e.id:(e.className&&typeof e.className==='string'?'.'+e.className.split(' ')[0]:e.tagName)):'null';
  const bad=[];let n=0;
  for(const b of document.querySelectorAll('#sSet button, #sSet input, #sSet a')){
    if(!b.offsetParent||getComputedStyle(b).visibility==='hidden')continue;n++;
    b.scrollIntoView({block:'center'});await new Promise(r=>requestAnimationFrame(()=>r()));
    const r=b.getBoundingClientRect(),hit=document.elementsFromPoint(r.x+r.width/2,r.y+r.height/2)[0];
    if(!hit||!(hit===b||b.contains(hit)))bad.push(nm(b)+' -> '+nm(hit));}
  g.scrollTop=0;await new Promise(r=>requestAnimationFrame(()=>r()));
  const G=g.getBoundingClientRect(),F=f.getBoundingClientRect(),rows=[...document.querySelectorAll('#sSet .srow')].map(e=>e.getBoundingClientRect());
  return {n,bad,below:rows.filter(q=>q.bottom>G.bottom-4).length,overFoot:rows.filter(q=>q.bottom>F.top+0.5&&q.top<F.bottom-0.5).length,
    footPE:getComputedStyle(f).pointerEvents,linkPE:getComputedStyle(f.querySelector('.credit')).pointerEvents};}"""

async def main():
    sizes = SIZES
    if '--size' in sys.argv:
        sizes = [tuple(map(int, sys.argv[sys.argv.index('--size') + 1].split('x')))]
    shots = '--shots' in sys.argv
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        for w, h in sizes:
            tag = f'{w}x{h}'
            pg = await page(b, url, vp={'width': w, 'height': h},
                            storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3', **PLACED})
            await pg.evaluate("()=>{const r=document.getElementById('rotOk');if(r&&r.offsetParent)r.click();}")
            await pg.evaluate("()=>window.__kgeu.openMenu('sSet')"); await pg.wait_for_timeout(400)
            r = await pg.evaluate(TAP)
            ok(f'{tag}: every Settings control ({r["n"]}) is the top element at its own centre', not r['bad'] and r['n'] >= 25, r['bad'][:6])
            ok(f'{tag}: the footer takes no taps, its YouTube link does', r['footPE'] == 'none' and r['linkPE'] == 'auto', (r['footPE'], r['linkPE']))
            ok(f'{tag}: no row sits under the footer', r['overFoot'] == 0, r['overFoot'])
            if (w, h) in ((667, 375), (844, 390), (932, 430)):
                ok(f'{tag}: all six rows show with no scrolling, clear of the bottom fade', r['below'] == 0, r['below'])
            if shots:
                await pg.screenshot(path=os.path.join(OUT, f'settings_{tag}.png'))
            ok(f'{tag}: no console errors', not pg.errs, pg.errs[:3])
            await pg.context.close()
        await b.close()
    return ok.done('settings_tap_check')

if __name__ == '__main__':
    raise SystemExit(asyncio.run(main()))
