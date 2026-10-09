# The Arsenal: the loadout card between the Red Flag Dogfight's briefing and FIGHT'S ON (item 1), and what each pick puts
# on the jet. More sections join as the items land (the MRM, the multipliers, the balance, the submission).
# Run: .venv/bin/python tests/arsenal_check.py            (writes screenshots to overnight-screenshots/arsenal/)
import asyncio, os, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, finger, IPHONE_15
ok = Checks()
K = "window.__kgeu"
OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'overnight-screenshots', 'arsenal'))
STEP = "(n)=>{const K=window.__kgeu;for(let i=0;i<n;i++)K.stepFrame(0.1,false,false);K.stepFrame(0,true);}"
STORES = f"()=>{{const D={K}.DF;return {{fox:D.fox,mrm:D.mrm|0,rounds:D.rounds,flares:D.flares,lo:D.lo&&D.lo.r,g:D.lo&&D.lo.g,t:D.t,on:D.on,brief:D.brief}}}}"
# every box on the card: in the viewport, no two interactive boxes overlapping, tap targets 44 px or more
FIT = """()=>{const o=document.getElementById('dfLo'),sh=o.querySelector('.sheet').getBoundingClientRect(),W=innerWidth,H=innerHeight;
  const R=e=>{const r=e.getBoundingClientRect();return [r.left,r.top,r.right,r.bottom]};
  const btn=[...o.querySelectorAll('button')].map(R),go=R(document.getElementById('dfbGo'));
  let ov=0;for(let i=0;i<btn.length;i++)for(let j=i+1;j<btn.length;j++){const a=btn[i],b=btn[j];if(a[0]<b[2]-1&&b[0]<a[2]-1&&a[1]<b[3]-1&&b[1]<a[3]-1)ov++;}
  const small=btn.filter(b=>b[2]-b[0]<44||b[3]-b[1]<44).length,off=[...o.querySelectorAll('.sheet *')].map(R).filter(b=>b[2]-b[0]>0&&(b[0]<-0.5||b[1]<-0.5||b[2]>W+0.5||b[3]>H+0.5)).length;
  const clip=[...o.querySelectorAll('.loR .c,.loR .f,.loR b,.loSum,.loG b')].filter(e=>e.scrollWidth>e.clientWidth+1).length;
  return {on:o.classList.contains('on'),sheet:[sh.left,sh.top,sh.right,sh.bottom],ov:ov,small:small,off:off,clip:clip,go:go,scroll:o.scrollHeight>o.clientHeight+1,n:btn.length}}"""

async def open_brief(pg, mode):
    await pg.evaluate(f"()=>{{{K}.setSkill('{mode}');{K}.openMenu();{K}.nav('sArc')}}"); await pg.wait_for_timeout(300)
    await finger(pg, '#arcCards [data-m="dogfight"]'); await pg.wait_for_timeout(600)
    await pg.evaluate(f"()=>{{{K}.DF.test.noBanditFire=true;{K}.DF.test.hold=true;}}")

async def shot(pg, name):
    os.makedirs(OUT, exist_ok=True)
    await pg.screenshot(path=os.path.join(OUT, name), timeout=120000)
    print('  wrote', os.path.join(OUT, name))

async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuType': 'f16'})
        # ---- 1. the card between the briefing and FIGHT'S ON ----
        await open_brief(pg, 'pilot')
        br = await pg.evaluate("()=>{const r=document.getElementById('dfbNext').getBoundingClientRect();return {brief:document.getElementById('dfBrief').classList.contains('on'),lo:document.getElementById('dfLo').classList.contains('on'),txt:document.getElementById('dfbNext').textContent,c:[r.left+r.width/2,r.top+r.height/2]}}")
        ok('the briefing ends in LOADOUT (the card is not up yet)', br['brief'] and not br['lo'] and br['txt'] == 'LOADOUT', br)
        await finger(pg, '#dfbNext'); await pg.wait_for_timeout(300)
        f = await pg.evaluate(FIT)
        s = await pg.evaluate(STORES)
        ok('LOADOUT: the briefing gives way to the loadout card, the sim still held (clock 90)', f['on'] and s['brief'] and s['t'] == 90 and not await pg.evaluate("()=>document.getElementById('dfBrief').classList.contains('on')"), (f['on'], s))
        txt = await pg.inner_text('#dfLo')
        ok('the card: LOADOUT, HARD, the racks (STANDARD, LIGHT, LOW FLARES), the gun (510 and 250 rds), FIGHT\'S ON', all(t in txt for t in ('LOADOUT', 'HARD', 'STANDARD', 'LIGHT', 'LOW FLARES', '510 rds', '250 rds', "FIGHT'S ON")), txt)
        ck = await pg.evaluate("()=>[...document.querySelectorAll('#dfLo [aria-checked=true]')].map(e=>e.dataset.r||e.dataset.g)")
        ok('a new install picks STANDARD and the FULL gun', ck == ['std', 'full'], ck)
        ok('the summary under the jet says today\'s stores: 6 SRM, 30 flares, 510 rds', (await pg.inner_text('#loSum')).replace('\xa0',' ') == '6 SRM · 30 flares · 510 rds', (await pg.inner_text('#loSum')).replace('\xa0',' '))
        ok('the jet drawing shows six missiles on the stations', await pg.evaluate("()=>document.querySelectorAll('#loJet g').length") == 6)
        ok('844x390: the card fits (nothing off screen, no scroll, no overlap, every target 44 px, no clipped text)', not f['off'] and not f['scroll'] and not f['ov'] and not f['small'] and not f['clip'], f)
        gc = [(f['go'][0] + f['go'][2]) / 2, (f['go'][1] + f['go'][3]) / 2]
        ok("FIGHT'S ON sits where LOADOUT was (two taps in one place fly today's fight): within 60 px", abs(gc[0] - br['c'][0]) < 60 and abs(gc[1] - br['c'][1]) < 60, (gc, br['c']))
        await shot(pg, 'a1_card_844.png')
        await finger(pg, '#dfbGo'); await pg.wait_for_timeout(200)
        await pg.evaluate(STEP, 10)
        s = await pg.evaluate(STORES)
        ok("FIGHT'S ON with the defaults: today's fight (6 FOX 2, 510 rounds, 30 flares), the clock runs", s['on'] and not s['brief'] and s['fox'] == 6 and s['rounds'] == 510 and s['flares'] == 30 and s['mrm'] == 0 and s['t'] < 90, s)
        ok('the buttons show the stores', await pg.inner_text('#bFoxN') == 'x6' and await pg.inner_text('#bGunN') == '510' and await pg.inner_text('#bFlrN') == '30')
        # ---- the picks: LIGHT and the HALF gun, kept for the next run ----
        await open_brief(pg, 'pilot'); await finger(pg, '#dfbNext'); await pg.wait_for_timeout(300)
        await finger(pg, '#loRacks [data-r="light"]'); await pg.wait_for_timeout(150)
        await finger(pg, '#loGuns [data-g="half"]'); await pg.wait_for_timeout(150)
        ck = await pg.evaluate("()=>[...document.querySelectorAll('#dfLo [aria-checked=true]')].map(e=>e.dataset.r||e.dataset.g)")
        ok('a tap picks a rack and a gun (one each)', ck == ['light', 'half'], ck)
        ok('the summary and the drawing follow the pick: 4 SRM, 250 rds, four missiles', (await pg.inner_text('#loSum')).replace('\xa0',' ') == '4 SRM · 30 flares · 250 rds' and await pg.evaluate("()=>document.querySelectorAll('#loJet g').length") == 4, (await pg.inner_text('#loSum')).replace('\xa0',' '))
        await shot(pg, 'a1_light_844.png')
        await finger(pg, '#dfbGo'); await pg.wait_for_timeout(200); await pg.evaluate(STEP, 5)
        s = await pg.evaluate(STORES)
        ok('LIGHT with the HALF gun: 4 FOX 2, 250 rounds, 30 flares', s['fox'] == 4 and s['rounds'] == 250 and s['flares'] == 30 and s['lo'] == 'light' and s['g'] == 'half', s)
        kept = await pg.evaluate("()=>localStorage.getItem('kgeuLoadout')")
        ok('the pick is kept (kgeuLoadout)', kept == '{"r":"light","g":"half"}', kept)
        await open_brief(pg, 'pilot'); await finger(pg, '#dfbNext'); await pg.wait_for_timeout(300)
        ck = await pg.evaluate("()=>[...document.querySelectorAll('#dfLo [aria-checked=true]')].map(e=>e.dataset.r||e.dataset.g)")
        ok('the next run opens on the kept pick', ck == ['light', 'half'], ck)
        await finger(pg, '#loRacks [data-r="bold"]'); await finger(pg, '#loGuns [data-g="full"]'); await pg.wait_for_timeout(150)
        await finger(pg, '#dfbGo'); await pg.wait_for_timeout(200); await pg.evaluate(STEP, 5)
        s = await pg.evaluate(STORES)
        ok('LOW FLARES: 6 FOX 2 and only 12 flares', s['fox'] == 6 and s['flares'] == 12 and s['rounds'] == 510, s)
        # ---- Easy: the same racks with Easy's counts ----
        await open_brief(pg, 'rookie'); await finger(pg, '#dfbNext'); await pg.wait_for_timeout(300)
        await finger(pg, '#loRacks [data-r="std"]'); await pg.wait_for_timeout(150)
        txt = await pg.inner_text('#dfLo')
        ok('Easy: the EASY chip, STANDARD is 10 SRM, LIGHT 6 SRM', 'EASY' in txt and '10 SRM' in txt and '6 SRM' in txt, txt)
        await shot(pg, 'a1_card_easy_844.png')
        await finger(pg, '#dfbGo'); await pg.wait_for_timeout(200); await pg.evaluate(STEP, 5)
        s = await pg.evaluate(STORES)
        ok("Easy STANDARD with the full gun: today's Easy fight (10 FOX 2, 510 rounds, 30 flares)", s['fox'] == 10 and s['rounds'] == 510 and s['flares'] == 30, s)
        ok('no console errors (844x390)', not pg.errs, pg.errs[:3])
        await pg.context.close()
        # ---- the small phones ----
        for vp, nm in (({'width': 667, 'height': 375}, '667'), ({'width': 568, 'height': 320}, '568'), ({'width': 932, 'height': 430}, '932')):
            pg = await page(b, url, vp=vp, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuType': 'f16'})
            await open_brief(pg, 'pilot')
            c0 = await pg.evaluate("()=>{const r=document.getElementById('dfbNext').getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2,r.bottom<=innerHeight]}")
            await finger(pg, '#dfbNext'); await pg.wait_for_timeout(300)
            f = await pg.evaluate(FIT)
            ok(f'{nm}: the card fits (nothing off screen, no scroll, no overlap, every target 44 px, no clipped text)', f['on'] and not f['off'] and not f['scroll'] and not f['ov'] and not f['small'] and not f['clip'], f)
            gc = [(f['go'][0] + f['go'][2]) / 2, (f['go'][1] + f['go'][3]) / 2]
            ok(f"{nm}: FIGHT'S ON within 60 px of LOADOUT, 60 px tall or more", c0[2] and abs(gc[0] - c0[0]) < 60 and abs(gc[1] - c0[1]) < 60 and f['go'][3] - f['go'][1] >= 60, (gc, c0, f['go']))
            await shot(pg, f'a1_card_{nm}.png')
            ok(f'no console errors ({nm})', not pg.errs, pg.errs[:3])
            await pg.context.close()
        await b.close()
    srv.shutdown()
    return ok.done('arsenal_check')

if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
