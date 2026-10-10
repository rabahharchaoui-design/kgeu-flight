# Phone3 item 4 (the layout check's approach pass): below 1,500 ft above the ground or inside 3 nm of a
# runway, no text may sit in the centre third of the screen (the box W/3..2W/3 by H/3..2H/3). Every
# mission, arcade game and lesson (and the free flight finals, both Arizona and a world region) is put on a
# 2 nm final (or flown where it starts, if that is already low), then the worst case goes up at once: a long
# two line tower subtitle, a long toast, a warning, a TCAS climb arrow and a flaps readout. Checked on the mission's first frame (the full card)
# and after 4 s (the chip), Easy and Hard, at 844x390, 568x320, 667x375 and portrait 390x844.
# Text is any visible element with its own text, cut by any overflow-hidden ancestor; the controls
# (buttons, the stick, the throttle scale), the flight readouts in the top left corner (#hud), the results and menu overlays, the six pack and the world
# markers pinned to a place (the drop zone mark, strike target marks) are not messages and are left out.
# Run: .venv/bin/python tests/centre_check.py
import asyncio, os, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, ROOT
ok = Checks()
K = 'window.__kgeu'
SHOTS = os.path.join(ROOT, 'overnight-screenshots', 'phone3', 'item4')

CENTRE = """()=>{const W=innerWidth,H=innerHeight,B=[W/3,H/3,2*W/3,2*H/3],out=[];
  const skip='button,.overlay,#sixpack,#menu,#pauseOv,#stickZone,#thrCol,#dock,#dzMark,#dzArrow,#tgtMarks,#crash,#crashTop,#photoOv,#mapOv,#hud,#rotate';
  const vis=e=>{for(let n=e;n&&n.nodeType===1;n=n.parentElement){const s=getComputedStyle(n);if(s.display==='none'||s.visibility==='hidden'||parseFloat(s.opacity)<0.05)return false;}return true;};
  for(const e of document.body.querySelectorAll('*')){
    if(e.closest(skip))continue;
    const own=[...e.childNodes].filter(n=>n.nodeType===3&&n.textContent.trim()).map(n=>n.textContent.trim()).join(' ');
    if(!own||!vis(e))continue;
    let r=e.getBoundingClientRect(),x0=r.left,y0=r.top,x1=r.right,y1=r.bottom;
    for(let n=e.parentElement;n&&n!==document.body;n=n.parentElement){const s=getComputedStyle(n);
      if(s.overflow!=='visible'||s.overflowY!=='visible'||s.overflowX!=='visible'){const q=n.getBoundingClientRect();x0=Math.max(x0,q.left);y0=Math.max(y0,q.top);x1=Math.min(x1,q.right);y1=Math.min(y1,q.bottom);}}
    if(x1-x0<1||y1-y0<1)continue;
    if(x0<B[2]&&x1>B[0]&&y0<B[3]&&y1>B[1])out.push((e.id?'#'+e.id:e.className||e.tagName)+' "'+own.slice(0,30)+'" '+[x0,y0,x1,y1].map(Math.round).join(','));}
  return out;}"""

WORST = """()=>{const $=id=>document.getElementById(id);
  const a=$('atc');a.innerHTML='<span class="tx"><b>Glendale Tower</b>Skyhawk 8401L, Glendale Tower, wind 050 at 5, runway 1, cleared to land, traffic a Cherokee on the go</span><span class="plain">Tower says: you can land on runway 1, a Cherokee is going around</span>';
  a.classList.add('on','hasPlain');
  const t=$('toast');t.textContent='Landing challenge: Glendale runway 1. Go! Beat the clock and land on the centreline';t.classList.add('on');
  const w=$('warn');w.textContent='SINK RATE';w.classList.add('on');
  const r=$('tcasRA');if(r){r.classList.add('on');const b=r.querySelector('b');if(b)b.textContent='CLIMB';}
  window.__kgeu.sideCfg('FLAPS 30\u00b0',null,'');}"""

STEP = f"(n)=>{{for(let i=0;i<n;i++){K}.stepFrame(1/30,false,true)}}"

MODES = [
    ('3 mi final', f"{K}.pick('cessna');{K}.pickBase('kgeu');{K}.start('final')", None),
    ('1 mi final', f"{K}.pick('f16');{K}.pickBase('kgeu');{K}.start('final1')", None),
    ('runway', f"{K}.pick('cessna');{K}.pickBase('kgeu');{K}.start('runway')", None),
    ('short field (Assault Landing)', f"{K}.pick('c130');{K}.start('short')", None),
    ('dash', f"{K}.pick('f16');{K}.start('runway','luke')", 3704),
    ('airdrop', f"{K}.pick('c130');{K}.start('drop')", None),
    ('landing challenge', f"{K}.pick('cessna');{K}.arcStart('landing')", 3704),
    ('1 mile challenge', f"{K}.pick('f16');{K}.arcStart('landing1')", None),
    ('daily', f"{K}.dailyRegion('az');{K}.arcStart('daily')", 3704),
    ('lesson first flight', f"{K}.startLesson('first');{K}.lesBriefSkip()", None),
    ('lesson pattern', f"{K}.startLesson('pattern',true);{K}.lesBriefSkip()", None),
    ('lesson engine failure', f"{K}.startLesson('engine',true);{K}.lesBriefSkip()", 3704),
    ('lesson slow flight', f"{K}.startLesson('slow',true);{K}.lesBriefSkip()", 3704),
]
VIEWS = [(844, 390), (568, 320), (667, 375), (390, 844)]

async def check(pg, tag, shot=None):
    await pg.evaluate(WORST); await pg.wait_for_timeout(120)
    st = await pg.evaluate(f"()=>({{appr:{K}.appr(),chip:document.getElementById('miss').classList.contains('chip'),miss:document.getElementById('miss').classList.contains('on')}})")
    bad = await pg.evaluate(CENTRE)
    ok(f'{tag}: approach mode on, centre third clear', st['appr'] and not bad, (st, bad[:4]))
    if shot:
        os.makedirs(SHOTS, exist_ok=True); await pg.screenshot(path=os.path.join(SHOTS, shot))
    return st

async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        for skill in ('pilot', 'rookie'):
            M = 'Hard' if skill == 'pilot' else 'Easy'
            for (w, h) in VIEWS:
                pg = await page(b, url, vp={'width': w, 'height': h}, storage={'kgeuOnboard': skill, 'kgeuTut': '1', 'kgeuCoach': '3'})
                await pg.wait_for_function(f"()=>{K}&&{K}.WORLD.ready", timeout=30000)
                await pg.evaluate("()=>document.body.classList.add('portraitok')")
                for name, js, fin in MODES:
                    tag = f'{M} {w}x{h} {name}'
                    await pg.evaluate(f"()=>{{{js}}}"); await pg.wait_for_timeout(150)
                    if fin: await pg.evaluate(f"()=>{K}.toFinal({fin})")
                    await pg.evaluate(STEP, 1)
                    s0 = await check(pg, tag + ', first frame', f'{skill}_{w}x{h}_{name.split()[0]}_0.png' if name in ('short field (Assault Landing)', 'lesson pattern') else None)
                    await pg.evaluate(STEP, 130)
                    s1 = await check(pg, tag + ', after 4 s', f'{skill}_{w}x{h}_{name.split()[0]}_4s.png' if name in ('short field (Assault Landing)', 'landing challenge') else None)
                    if s0['miss']:
                        ok(f'{tag}: mission card in full first, a chip after 3 s', not s0['chip'] and (s1['chip'] or not s1['miss']), (s0, s1))
                ok(f'{M} {w}x{h}: no page errors', not pg.errs, pg.errs[:3])
                await pg.context.close()
        # a world region: its finals and its airport challenge
        pg = await page(b, url, vp={'width': 844, 'height': 390}, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3', 'kgeuRegion': 'rjtt'})
        await pg.wait_for_function(f"()=>{K}&&{K}.WORLD.ready", timeout=30000)
        for name, js, fin in (('rjtt 1 mi final', f"{K}.pick('cessna');{K}.start('final1')", None), ('rjtt airport challenge', f"{K}.pick('alpha');{K}.arcStart('apt')", 3704)):
            await pg.evaluate(f"()=>{{{js}}}"); await pg.wait_for_timeout(150)
            if fin: await pg.evaluate(f"()=>{K}.toFinal({fin})")
            await pg.evaluate(STEP, 130)
            await check(pg, name)
        # and high and far from any runway it is the normal centre column again
        await pg.evaluate(f"()=>{{{K}.pick('cessna');{K}.start('final');{K}.toFinal(15000);const s={K}.state();s.pos.y+=600;}}")
        await pg.evaluate(STEP, 2)
        ok('high and far out: not approach mode', not await pg.evaluate(f"()=>{K}.appr()"))
        ok('rjtt: no page errors', not pg.errs, pg.errs[:3])
        await b.close()
    srv.shutdown()
    sys.exit(ok.done('centre_check'))

asyncio.run(main())
