# Speeds in knots everywhere: no mph, km/h or m/s in the source or in any visible text
# (HUD in Easy and Hard, the menus, pause sheet, mission and arcade cards, lesson panel,
# result cards, the crash card, the leaderboard screen), and the Easy HUD speed is IAS
# in knots. iPhone landscape. Run: .venv/bin/python tests/units_check.py
import asyncio, os, re, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, IPHONE_15, ROOT
ok = Checks()
K = "window.__kgeu"
BAD = r"\bmph\b|km/h|\bkph\b|\bkmh\b|miles per hour|miles an hour|\bm/s\b"

# the visible text of the page plus the text of every card and sheet, shown or not
TEXT = """()=>document.body.innerText+'\\n'+[...document.querySelectorAll('.overlay,.card,.screen,#crash,#crashTop,#hud')]
  .map(e=>e.textContent).join('\\n')"""

async def scan(pg, where):
    t = await pg.evaluate(TEXT)
    m = [x.group(0) for x in re.finditer(BAD, t, re.I)]
    ok(f'{where}: no mph, km/h or m/s on screen', not m, m[:5])

async def hud_speed(pg):
    return await pg.evaluate(f"()=>({{t:document.getElementById('hIas').textContent,kt:{K}.state().ias*1.943844,l:document.getElementById('lIas').textContent}})")

async def main():
    src = open(os.path.join(ROOT, 'index.html')).read()
    m = [x.group(0) for x in re.finditer(r"\bmph\b|km/h|\bkph\b|miles per hour|miles an hour", src, re.I)]
    ok('index.html has no mph, km/h or miles per hour anywhere', not m, m[:5])
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'rookie', 'kgeuTut': '1'})
        # ---- menus ----
        for s in ('sHome', 'sFly', 'sSchool', 'sArc', 'sSet', 'sHelp', 'sCredits', 'sLb'):
            await pg.evaluate(f"()=>{{{K}.openMenu();{K}.nav('{s}')}}"); await pg.wait_for_timeout(250)
            await scan(pg, s)
        # ---- HUD, Easy then Hard ----
        for skill, name, unit in (('rookie', 'Easy', 'kt'), ('pilot', 'Hard', '')):
            await pg.evaluate(f"()=>{{{K}.setSkill('{skill}');{K}.pick('cessna');{K}.pickBase('kgeu');{K}.start('final')}}")
            await pg.evaluate("()=>{for(let i=0;i<20;i++)window.__kgeu.stepFrame(1/30,false,true)}")
            h = await hud_speed(pg)
            num = re.match(r'\s*(\d+)\s*(\w*)', h['t'])
            ok(f'{name} HUD speed is IAS in knots ({h["t"]!r}, IAS {h["kt"]:.1f} kt, label {h["l"]!r})',
               bool(num) and abs(int(num.group(1)) - h['kt']) <= 1.5 and num.group(2) == unit, h)
            await scan(pg, f'{name} HUD')
            await pg.evaluate(f"()=>{K}.togglePause()"); await pg.wait_for_timeout(200)
            await scan(pg, f'{name} pause sheet')
            await pg.evaluate(f"()=>{K}.togglePause()")
        # ---- landing result card ----
        g = await pg.evaluate(f"""()=>{{const K={K},s=K.state();const e={{type:'touchdown',fpm:180,paved:true,x:K.wX(300,0),z:K.wZ(300,0),
          ias:95/1.943844,bank:0,wdir:10,wkt:3}};s.pos.x=e.x;s.pos.z=e.z;K.onLanding(e);return document.getElementById('landOv').textContent}}""")
        ok('landing card airspeed reads in knots', ' kt' in g, g[:160])
        await scan(pg, 'landing result card')
        # ---- missions ----
        for k in ('range', 'drop'):
            await pg.evaluate(f"()=>{K}.mission('{k}')")
            await pg.evaluate("()=>{for(let i=0;i<30;i++)window.__kgeu.stepFrame(1/30,false,true)}")
            await scan(pg, f'mission {k}')
        # ---- a lesson panel ----
        for les in ('slow', 'steep'):
            await pg.evaluate(f"()=>{K}.startLesson('{les}')"); await pg.wait_for_timeout(300)
            await pg.evaluate("()=>{for(let i=0;i<30;i++)window.__kgeu.stepFrame(1/30,false,true)}")
            await scan(pg, f'lesson {les}')
        # ---- crash card ----
        await pg.evaluate(f"()=>{{{K}.setSkill('rookie');{K}.pick('cessna');{K}.start('final')}}")
        await pg.evaluate("()=>window.__kgeu.stepFrame(1/30,false,true)")
        await pg.evaluate(f"()=>{K}.crashNow('Test crash.')")
        await pg.evaluate("()=>{for(let i=0;i<120;i++)window.__kgeu.stepFrame(1/30,false,true)}")
        await scan(pg, 'crash card')
        ok('no page errors', not pg.errs, pg.errs[:3])
        await b.close()
    sys.exit(ok.done('units_check'))
asyncio.run(main())
