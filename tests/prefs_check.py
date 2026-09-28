# Bug 1: menu choices must never reset each other, and all of them survive a reload.
# Picks every aircraft, then every time of day and base against each one, and
# confirms the aircraft never changes. Run: .venv/bin/python tests/prefs_check.py
import asyncio, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks

TYPES = ['f16', 'reaper', 'mq9b', 'cessna', 'c130', 'alpha']
TODS = ['day', 'sunset', 'night']
BASES = ['kgeu', 'luke']
ok = Checks()

async def tap(pg, sel):
    await pg.evaluate("(s)=>document.querySelector(s).click()", sel)
    await pg.wait_for_timeout(40)

async def prefs(pg):
    return await pg.evaluate("()=>window.__kgeu.prefs()")

async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, storage={'kgeuOnboard': 'rookie', 'kgeuTut': '1'})
        await pg.evaluate("()=>window.__kgeu.openFly&&window.__kgeu.openFly()")
        bad = []
        for t in TYPES:
            await tap(pg, f'.pick[data-t="{t}"]')
            for tod in TODS:
                await tap(pg, f'.pick[data-tod="{tod}"]')
                pr = await prefs(pg)
                if pr['type'] != t or pr['tod'] != tod: bad.append(f'{t} after {tod}: {pr}')
            for base in BASES:
                await tap(pg, f'.pick[data-b="{base}"]')
                pr = await prefs(pg)
                if pr['type'] != t or pr['base'] != base: bad.append(f'{t} after {base}: {pr}')
            for pos in ['runway', 'ramp', 'final']:
                if await pg.query_selector(f'.pick[data-pos="{pos}"]'):
                    await tap(pg, f'.pick[data-pos="{pos}"]')
                    pr = await prefs(pg)
                    if pr['type'] != t or pr.get('pos') != pos: bad.append(f'{t} after {pos}: {pr}')
        ok('aircraft never changes when time of day, base or start position is picked', not bad, '; '.join(bad[:4]))

        # changing the aircraft must not move the base or the time of day
        await tap(pg, '.pick[data-b="luke"]'); await tap(pg, '.pick[data-tod="night"]')
        for t in TYPES:
            await tap(pg, f'.pick[data-t="{t}"]')
            pr = await prefs(pg)
            ok(f'picking {t} keeps Luke and night', pr['base'] == 'luke' and pr['tod'] == 'night', pr)

        # the highlighted chips match the state
        sel = await pg.evaluate("""()=>[...document.querySelectorAll('.pick.sel')].map(e=>e.dataset.t||e.dataset.tod||e.dataset.b||e.dataset.pos).sort().join(',')""")
        ok('highlighted chips are one per row', all(x in sel for x in ['alpha', 'night', 'luke']), sel)

        # a mission borrows an aircraft without changing the saved pick
        await tap(pg, '.pick[data-t="f16"]')
        await pg.evaluate("()=>window.__kgeu.mission('drop')")
        await pg.wait_for_timeout(500)
        pr = await prefs(pg)
        ok('a C-130 mission leaves the saved aircraft on the F-16', pr['type'] == 'f16', pr)

        # everything survives a reload
        await pg.evaluate("()=>{window.__kgeu.pickBase('kgeu');window.__kgeu.setTOD('sunset');window.__kgeu.pick('mq9b');}")
        await pg.reload(); await pg.wait_for_function('()=>window.__kgeu'); await pg.wait_for_timeout(500)
        pr = await prefs(pg)
        ok('aircraft, base and time of day persist across a reload',
           pr['type'] == 'mq9b' and pr['base'] == 'kgeu' and pr['tod'] == 'sunset', pr)
        ok('no page errors', not pg.errs, pg.errs[:3])
        await b.close()
    sys.exit(ok.done('prefs_check'))

asyncio.run(main())
