# The game's boards (LB.board in index.html) and the Worker's (server/src/boards.js) in step: the same ids, the same
# direction (higher or lower is better) and the same single mode (the dogfight's Easy and Hard boards); the dogfight
# daily rule the same on both sides (the next 60 days).
# Usage: .venv/bin/python tests/lb_boards_check.py
import asyncio, sys, os, json, subprocess
from playwright.async_api import async_playwright
sys.path.insert(0, os.path.dirname(__file__))
from harness import serve, launch, page, Checks, ROOT, IPHONE_15

ok = Checks()
K = 'window.__kgeu'
NODE = """import('%s').then(m=>{const o={};for(const k in m.BOARDS)o[k]={dir:m.BOARDS[k].dir,mode:m.BOARDS[k].mode||null};
  const d=[];for(let i=0;i<60;i++){const t=Date.UTC(2026,9,1+i);d.push(m.dfDay(t+43200e3));}console.log(JSON.stringify({b:o,d}));})""" % os.path.join(ROOT, 'server/src/boards.js')


async def main():
    srv = json.loads(subprocess.check_output(['node', '--input-type=module', '-e', NODE], text=True))
    s, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1'})
        # tasking item 1: the Taskings boards are device boards (local: the Worker does not know task: ids), left out here
        loc = await pg.evaluate(f"()=>Object.keys({K}.LB.BOARDS).filter(k=>{K}.LB.BOARDS[k].local)")
        # school1 item 9: and the nine lessons the Worker does not know (lesson:climbs and the rest), ranked on the device
        want = ['task:' + t for t in ('overwatch', 'lifeline', 'shepherd', 'finder')] + ['lesson:' + t for t in ('climbs', 'ground', 'landings', 'solo', 'short', 'soft', 'xwind', 'emerg', 'hood')]
        ok('the device boards are the four Taskings and the nine new lessons, none of them on the server', sorted(loc) == sorted(want) and not [k for k in loc if k in srv['b']], loc)
        g = await pg.evaluate(f"()=>{{const B={K}.LB.BOARDS,o={{}};for(const k in B)if(!B[k].local)o[k]={{dir:B[k].dir,mode:B[k].mode||null}};return o}}")
        gd = await pg.evaluate(f"()=>{{const d=[];for(let i=0;i<60;i++){{const t=new Date(Date.UTC(2026,9,1+i));d.push({K}.dfDayOf(t.getUTCFullYear()*10000+(t.getUTCMonth()+1)*100+t.getUTCDate()));}}return d}}")
        ok('every game board is on the server', not [k for k in g if k not in srv['b']], [k for k in g if k not in srv['b']])
        ok('every server board is in the game', not [k for k in srv['b'] if k not in g], [k for k in srv['b'] if k not in g])
        diff = [(k, g[k], srv['b'][k]) for k in g if k in srv['b'] and g[k] != srv['b'][k]]
        ok('same direction and mode on both sides', not diff, diff)
        ok('the eight dogfight boards, Easy and Hard single mode', sorted(k for k in g if k.startswith('df:')) == sorted(f'df:{a}:{m}' for a in ('score', 'kills', 'clear', 'guns') for m in ('easy', 'hard'))
           and all(g[k]['mode'] == k.split(':')[2] for k in g if k.startswith('df:')), [k for k in g if k.startswith('df:')])
        ok('the dogfight daily rule agrees (60 days, one in five)', gd == srv['d'] and sum(gd) == 12, (gd, srv['d']))
        ok('no console errors', not pg.errs, pg.errs[:3])
        await b.close()
    sys.exit(ok.done('lb_boards_check'))

asyncio.run(main())
