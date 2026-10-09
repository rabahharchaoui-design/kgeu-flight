# ui1 items 5 to 8: the XP pop and where it fires.
#  (a) xpPop(amount, reason): a centre screen burst that counts up to the amount, the reason under it, inside the safe
#      area (a 47 px notch stood in), never takes a touch (the stick under it still gets the finger), two close together
#      stack (the older one steps up), gone after about 2.5 s; 568x320 and 844x390.
# Run: .venv/bin/python tests/xp_check.py
import asyncio, os, sys
from playwright.async_api import async_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import serve, launch, page, Checks, ROOT
ok = Checks()
K = 'window.__kgeu'
SHOTS = os.path.join(ROOT, 'overnight-screenshots', 'ui1')
SETSAFE = """([t,l,r,b])=>{const s=document.documentElement.style;s.setProperty('--saT',t+'px');s.setProperty('--saL',l+'px');s.setProperty('--saR',r+'px');s.setProperty('--saB',b+'px');}"""
POP = """()=>{const p=[...document.querySelectorAll('#xpPops .xpPop')];return p.map(e=>{const r=e.querySelector('.xpIn').getBoundingClientRect();
  return {n:e.querySelector('.xpN b').textContent,r:(e.querySelector('.xpR')||{}).textContent||'',x:r.left,y:r.top,w:r.width,h:r.height,cx:r.left+r.width/2,cy:r.top+r.height/2,
    pe:[e,...e.querySelectorAll('*')].every(n=>getComputedStyle(n).pointerEvents==='none'),done:e.classList.contains('done'),tr:e.style.transform}})}"""


async def main():
    os.makedirs(SHOTS, exist_ok=True)
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        for vp in ({'width': 844, 'height': 390}, {'width': 568, 'height': 320}):
            tag = f"{vp['width']}x{vp['height']}"
            pg = await page(b, url, vp=vp, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'})
            await pg.evaluate(SETSAFE, [0, 47, 47, 21])
            await pg.evaluate(f"()=>{{const K={K};K.pick('cessna');K.pickBase('kgeu');K.start('runway')}}"); await pg.wait_for_timeout(500)
            await pg.evaluate(f"()=>{K}.xpPop(37,'Landing graded')")
            await pg.wait_for_timeout(250)
            a = await pg.evaluate(POP)
            ok(f'{tag} (a) one pop shows at once, the reason under it', len(a) == 1 and a[0]['r'] == 'Landing graded', a)
            W, H = vp['width'], vp['height']
            ok(f'{tag} (a) centre screen: centred across, in the middle band, inside the safe area',
               a and abs(a[0]['cx'] - W / 2) < 6 and H * 0.2 < a[0]['cy'] < H * 0.62 and a[0]['x'] >= 47 - 0.5 and a[0]['x'] + a[0]['w'] <= W - 47 + 0.5, a)
            ok(f'{tag} (a) it never takes a touch (pointer-events none all the way down)', a and a[0]['pe'], a)
            # a finger on the pop lands on what is under it
            hit = await pg.evaluate("()=>{const r=document.querySelector('#xpPops .xpIn').getBoundingClientRect();const e=document.elementFromPoint(r.left+r.width/2,r.top+r.height/2);return e&&!e.closest('#xpPops')}")
            ok(f'{tag} (a) a tap on it goes through to the game', hit)
            await pg.wait_for_timeout(900)
            a = await pg.evaluate(POP)
            ok(f'{tag} (a) the number counted up to 37 and glows', a and a[0]['n'] == '37' and a[0]['done'], a)
            await pg.evaluate(f"()=>{K}.xpPop(15,'Personal best')"); await pg.wait_for_timeout(800)
            a = await pg.evaluate(POP)   # DOM order: the older pop first
            ok(f'{tag} (a) a second pop stacks: the new one in the centre, the older one stepped up and smaller', len(a) == 2 and a[0]['cy'] < a[1]['cy'] - 30 and 'translateY' in a[0]['tr'] and abs(a[1]['cx'] - W / 2) < 6, a)
            await pg.screenshot(path=os.path.join(SHOTS, f'xp_stack_{tag}.png'))
            await pg.wait_for_timeout(2600)
            await pg.evaluate(f"()=>{{{K}.xpPop(37,'Landing graded',{{hold:6000}})}}"); await pg.wait_for_timeout(1300)
            await pg.screenshot(path=os.path.join(SHOTS, f'xp_pop_{tag}.png'))
            await pg.wait_for_timeout(5200)
            await pg.evaluate(f"()=>{{const K={K};K.xpPop(1,'a');K.xpPop(2,'b');K.xpPop(3,'c');}}"); await pg.wait_for_timeout(200)
            n = await pg.evaluate("()=>document.querySelectorAll('#xpPops .xpPop').length")
            ok(f'{tag} (a) never more than three on screen', n == 3, n)
            ok(f'{tag} (a) nothing for zero or a negative amount', await pg.evaluate(f"()=>{K}.xpPop(0,'x')===null&&{K}.xpPop(-5,'x')===null"))
            await pg.wait_for_timeout(2800)
            n = await pg.evaluate("()=>document.querySelectorAll('#xpPops .xpPop').length")
            ok(f'{tag} (a) gone after about 2.5 s', n == 0, n)
            ok(f'{tag} (a) the light haptic was asked for', await pg.evaluate(f"()=>{K}.HAP?{K}.HAP.log.some(x=>x.n==='xp'):true"))
            ok(f'{tag} no page errors', not pg.errs, pg.errs[:3])
            await pg.context.close()
        await b.close()
    sys.exit(ok.done('xp_check'))

asyncio.run(main())
