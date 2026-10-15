# fix2 before/after shots: every menu tab (Home, Fly, Challenges, Flight school,
# Boards, Settings) plus the pause menu, at several sizes with a simulated notch.
# The game reads env(safe-area-inset-*) into --saL/--saR/--saT/--saB at :root (index.html
# top of <style>); we override with a later <style> tag of higher source order so the
# !important wins the tie. notch-left puts the inset on the left (home button side),
# notch-right mirrors it; portrait uses a top inset only.
# Usage: .venv/bin/python tests/fix2_tabs_shots.py <outdir> [--only screen1,screen2]
#        [--variant 844x390_notchleft|844x390_notchright|932x430_notchleft|932x430_notchright|568x320_plain|390x844_notchtop|pause_notchleft|pause_notchright]
# One variant per run keeps each Bash call under the 2-minute cap. Writes
# <outdir>/tabs_<screen>_<WxH>_<notch>.png and tabs_pause_<WxH>_<notch>.png
import asyncio, os, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, IPHONE_15, PLACED

K = 'window.__kgeu'
args = [a for a in sys.argv[1:] if not a.startswith('--')]
OUT = os.path.abspath(args[0] if args else 'overnight-screenshots/fix2/before/tabs')
ONLY = None
if '--only' in sys.argv:
    ONLY = sys.argv[sys.argv.index('--only') + 1].split(',')
VARIANT = None
if '--variant' in sys.argv:
    VARIANT = sys.argv[sys.argv.index('--variant') + 1]

SCREENS = [('sHome', 'home'), ('sFly', 'fly'), ('sArc', 'challenges'), ('sSchool', 'flightschool'), ('sLb', 'boards'), ('sSet', 'settings')]
if ONLY:
    SCREENS = [s for s in SCREENS if s[1] in ONLY]

NOTCH_LEFT = ":root{--saL:47px!important;--saR:0px!important}"
NOTCH_RIGHT = ":root{--saR:47px!important;--saL:0px!important}"
NOTCH_TOP = ":root{--saT:47px!important}"

SIZE_BY_W = {844: IPHONE_15, 932: {'width': 932, 'height': 430}, 568: {'width': 568, 'height': 320}, 390: {'width': 390, 'height': 844}}

# (variant key, vp, css-or-None, name suffix)
ALL_VARIANTS = {
    '844x390_notchleft': (SIZE_BY_W[844], NOTCH_LEFT, 'notchleft'),
    '844x390_notchright': (SIZE_BY_W[844], NOTCH_RIGHT, 'notchright'),
    '932x430_notchleft': (SIZE_BY_W[932], NOTCH_LEFT, 'notchleft'),
    '932x430_notchright': (SIZE_BY_W[932], NOTCH_RIGHT, 'notchright'),
    '568x320_plain': (SIZE_BY_W[568], None, 'plain'),
    '390x844_notchtop': (SIZE_BY_W[390], NOTCH_TOP, 'notchtop'),
    'pause_notchleft': (SIZE_BY_W[844], NOTCH_LEFT, 'notchleft'),
    'pause_notchright': (SIZE_BY_W[844], NOTCH_RIGHT, 'notchright'),
}
VARIANTS = {VARIANT: ALL_VARIANTS[VARIANT]} if VARIANT else ALL_VARIANTS


async def inject_notch(pg, css):
    if css:
        await pg.add_style_tag(content=css)


async def shot(pg, name):
    await pg.wait_for_timeout(300)
    path = os.path.join(OUT, name)
    await pg.screenshot(path=path)
    print('  wrote', path)


async def open_screen(pg, scr):
    await pg.evaluate(f"(s)=>{{const K={K};K.openMenu();K.nav(s)}}", scr)
    await pg.wait_for_timeout(250)


async def main():
    os.makedirs(OUT, exist_ok=True)
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        for key, (vp, css, suffix) in VARIANTS.items():
            pg = await page(b, url, vp=vp, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3', **PLACED})
            await pg.evaluate("()=>{const r=document.getElementById('rotOk');if(r&&r.offsetParent)r.click();}")
            await inject_notch(pg, css)
            if key.startswith('pause'):
                await pg.evaluate(f"()=>{{const K={K};K.pick('cessna');K.pickBase('kgeu');K.start('runway')}}")
                await pg.wait_for_timeout(600)
                await pg.evaluate(f"()=>{K}.togglePause()")
                await shot(pg, f'tabs_pause_{vp["width"]}x{vp["height"]}_{suffix}.png')
            else:
                for scr, label in SCREENS:
                    await open_screen(pg, scr)
                    await shot(pg, f'tabs_{label}_{vp["width"]}x{vp["height"]}_{suffix}.png')
            if pg.errs:
                print(f'  page errors ({key}):', pg.errs[:5])
            await pg.context.close()
        await b.close()
    srv.shutdown()

asyncio.run(main())
