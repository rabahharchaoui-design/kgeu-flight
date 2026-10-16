# fix2 item 8: the menu tab bar is centred on the screen with a notch or cutout on either side.
# For each size and inset: every tab screen (opened by its tab, no back button) has its .mtRow centred
# on the screen (|centre - innerWidth/2| <= 2 px) when it fits, else left-aligned at the symmetric inset,
# scrollable, with the selected tab in view; the screen's first block is centred too and starts below the
# bar; a sub screen (Controls help, plain back) and the menu opened from the pause sheet ('Flight' back)
# keep the row clear of #mBack (centred, or moved right just enough). The pause sheet's top row and the two
# cards have the same inset both sides at 844x390 with the notch either side.
# Usage: .venv/bin/python tests/tabbar_check.py [--sizes 844x390,568x320] [--variant left|right|top|android|plain] [--no-pause]
# The insets are overridden the way tests/fix2_tabs_shots.py does it (a later <style> with !important).
import asyncio, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, PLACED, Checks

K = 'window.__kgeu'
def opt(name, d=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else d
SIZES = [tuple(int(v) for v in s.split('x')) for s in opt('--sizes', '844x390,932x430,667x375,568x320,390x844').split(',')]
VARS = opt('--variant')
NOPAUSE = '--no-pause' in sys.argv

CSS = {
    'left': ":root{--saL:47px!important;--saR:0px!important}",
    'right': ":root{--saR:47px!important;--saL:0px!important}",
    'top': ":root{--saT:47px!important;--saL:0px!important;--saR:0px!important}",
    'android': ":root{--saL:32px!important;--saR:0px!important;--saB:24px!important}",   # a cutout one side, a nav bar below
    'plain': ":root{--saL:0px!important;--saR:0px!important}",
}
def variants(w, h):
    v = ['top'] if h > w else ['left', 'right'] + (['android'] if w == 844 else []) + (['plain'] if w == 568 else [])
    return [x for x in v if not VARS or x in VARS.split(',')]

TABS = [('tHome', 'sHome'), ('tFly', 'sFly'), ('tChal', 'sArc'), ('tSch', 'sSchool'), ('tLb', 'sLb'), ('tSet', 'sSet')]

MEASURE = """(scr)=>{const q=s=>document.querySelector(s),R=e=>e.getBoundingClientRect();
  const nav=q('#mTabs'),row=q('#mTabs .mtRow'),bk=q('#mBack'),sel=row.querySelector('.sel'),sc=document.getElementById(scr);
  const nr=R(nav),rr=R(row),br=bk.hidden?null:R(bk),sr=sel?R(sel):null;
  const kids=[...sc.children].filter(e=>e.offsetParent&&e.getBoundingClientRect().height>0&&getComputedStyle(e).position!=='absolute'&&getComputedStyle(e).position!=='fixed');
  const fk=kids.length?R(kids[0]):null;
  return {W:innerWidth,navL:nr.left,navR:innerWidth-nr.right,navB:nr.bottom,rowL:rr.left,rowR:rr.right,sw:row.scrollWidth,cw:row.clientWidth,sl:row.scrollLeft,
    bk:br?[br.left,br.right]:null,sel:sr?[sr.left,sr.right]:null,first:fk?[fk.left,fk.right,fk.top]:null,firstId:kids.length?(kids[0].id||kids[0].className):'',
    padL:getComputedStyle(sc).paddingLeft,padR:getComputedStyle(sc).paddingRight};}"""

def check_row(c, tag, m, back):
    W = m['W']; cen = (m['rowL'] + m['rowR']) / 2; off = cen - W / 2
    c(f'{tag} bar insets equal', abs(m['navL'] - m['navR']) <= 1, f"L {m['navL']:.0f} R {m['navR']:.0f}")
    fits = m['sw'] <= m['cw'] + 1
    if fits:
        if back:
            c(f'{tag} row clear of back', m['rowL'] >= m['bk'][1] + 7, f"back right {m['bk'][1]:.0f} row left {m['rowL']:.0f}")
            ok = abs(off) <= 2 or abs(m['rowL'] - (m['bk'][1] + 8)) <= 1.5
            c(f'{tag} row centred or just clear', ok, f'offset {off:+.1f}')
        else:
            c(f'{tag} row centred', abs(off) <= 2, f'offset {off:+.1f}')
    else:
        start = m['bk'][1] + 8 if back else m['navL']
        c(f'{tag} row scrolls from the inset', abs(m['rowL'] - start) <= 1.5, f"row left {m['rowL']:.0f} want {start:.0f} sw {m['sw']} cw {m['cw']}")
        c(f'{tag} selected tab in view', m['sel'] and m['sel'][0] >= m['rowL'] - 1 and m['sel'][1] <= m['rowR'] + 1, f"sel {m['sel']} row {m['rowL']:.0f}..{m['rowR']:.0f}")
    print(f'      {tag}: centre offset {off:+.1f} px  fits {fits}  ({m["rowL"]:.0f}..{m["rowR"]:.0f} of {W})')
    return off

async def main():
    c = Checks(); offs = {}
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        for (w, h) in SIZES:
            for v in variants(w, h):
                key = f'{w}x{h}_{v}'
                print(f'-- {key}')
                pg = await page(b, url, vp={'width': w, 'height': h}, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3', **PLACED})
                await pg.evaluate("()=>{const r=document.getElementById('rotOk');if(r&&r.offsetParent)r.click();}")
                await pg.add_style_tag(content=CSS[v])
                await pg.evaluate(f"()=>{K}.openMenu()")
                await pg.wait_for_timeout(200)
                worst = 0
                for tid, scr in TABS:
                    await pg.evaluate("(t)=>document.getElementById(t).click()", tid)
                    await pg.wait_for_timeout(200)
                    m = await pg.evaluate(MEASURE, scr)
                    tag = f'{key} {scr}'
                    c(f'{tag} no back button', m['bk'] is None)
                    off = check_row(c, tag, m, False); worst = max(worst, abs(off))
                    if m['first']:
                        c(f'{tag} bar above the content', m['navB'] <= m['first'][2] + 0.5, f"bar bottom {m['navB']:.0f} {m['firstId']} top {m['first'][2]:.0f}")
                        c(f'{tag} content insets equal', m['padL'] == m['padR'], f"{m['padL']} {m['padR']}")
                offs[key] = worst
                # a sub screen: Controls help from Settings (plain back button)
                await pg.evaluate(f"()=>{K}.nav('sHelp')")
                await pg.wait_for_timeout(200)
                m = await pg.evaluate(MEASURE, 'sHelp')
                c(f'{key} sHelp back shown', m['bk'] is not None)
                if m['bk']: check_row(c, f'{key} sHelp', m, True)
                if not NOPAUSE and h <= w:
                    await pg.evaluate(f"()=>{{const K={K};K.pick('cessna');K.pickBase('kgeu');K.start('runway')}}")
                    await pg.wait_for_timeout(600)
                    await pg.evaluate(f"()=>{K}.togglePause()")
                    await pg.wait_for_timeout(400)
                    pz = await pg.evaluate("""()=>{const R=s=>{const e=document.querySelector(s);const r=e.getBoundingClientRect();return [r.left,innerWidth-r.right]};
                        return {top:R('#pauseOv .pzTop'),body:R('#pauseOv .pzBody'),L:R('#pauseOv .pzL'),Rr:R('#pauseOv .pzR')}}""")
                    for k2 in ('top', 'body'):
                        a, z = pz[k2]
                        c(f'{key} pause {k2} row centred', abs(a - z) <= 2, f'left {a:.0f} right {z:.0f}')
                    c(f'{key} pause cards span the inset', abs(pz['L'][0] - pz['Rr'][1]) <= 2, f"left card {pz['L'][0]:.0f} right card {pz['Rr'][1]:.0f}")
                    # Settings from the pause sheet: the menu with the 'Flight' back button
                    await pg.evaluate("()=>document.getElementById('pSet').click()")
                    await pg.wait_for_timeout(300)
                    m = await pg.evaluate(MEASURE, 'sSet')
                    c(f'{key} fromPause back shown', m['bk'] is not None)
                    if m['bk']: check_row(c, f'{key} fromPause sSet', m, True)
                if pg.errs:
                    print('  page errors:', pg.errs[:4])
                await pg.context.close()
        await b.close()
    srv.shutdown()
    print('\nworst tab-row centre offset per size (no back button):')
    for k, o in offs.items(): print(f'  {k}: {o:.1f} px')
    sys.exit(c.done('tabbar_check'))

asyncio.run(main())
