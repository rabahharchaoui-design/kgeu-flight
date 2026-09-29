# Feature 4: first launch funnel and skill level. Run: .venv/bin/python tests/skill_check.py
import asyncio, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, finger
ok = Checks()
K = "window.__kgeu"

async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, storage={})
        vis = await pg.evaluate("()=>document.getElementById('funnel').classList.contains('on')")
        ok('first launch shows the funnel', vis)
        btns = await pg.evaluate("()=>[...document.querySelectorAll('#funnel button')].map(b=>b.querySelector('b').textContent)")
        ok('two big buttons: EASY and HARD', btns == ['EASY', 'HARD'], btns)
        await finger(pg, '#fPilot'); await pg.wait_for_timeout(300)
        ok('choosing saves the skill', await pg.evaluate(f"()=>{K}.skill()") == 'pilot')
        await pg.reload(); await pg.wait_for_function('()=>window.__kgeu'); await pg.wait_for_timeout(400)
        ok('the funnel does not come back once chosen', not await pg.evaluate("()=>document.getElementById('funnel').classList.contains('on')"))
        ok('no Easy flight toggle anywhere', await pg.evaluate("()=>!document.getElementById('oEasy')&&![...document.querySelectorAll('button,label,p,span,b')].some(e=>/Easy flight/.test(e.textContent))"))

        # pilot: real terms, no assists, full phraseology
        await pg.evaluate(f"()=>{{{K}.pick('cessna');{K}.pickBase('kgeu');{K}.start('runway')}}"); await pg.wait_for_timeout(2500)
        lab = await pg.evaluate("()=>['lIas','lAlt','lVs','lHdg'].map(i=>document.getElementById(i).textContent)")
        ok('pilot labels are KIAS ALT VS HDG', lab == ['KIAS', 'ALT', 'VS', 'HDG'], lab)
        ok('pilot flight has no easy flight assists', await pg.evaluate(f"()=>{K}.state().easy") is False)
        atc = await pg.evaluate("()=>document.getElementById('atc').innerText")
        ok('pilot radio is full phraseology with no plain line', 'cleared for takeoff' in atc and 'says:' not in atc, atc)
        await pg.evaluate(f"()=>{{{K}.state().elev=0.6;}}"); await pg.wait_for_timeout(400)
        ok('no auto throttle for pilots', await pg.evaluate(f"()=>{K}.state().throttle") < 0.5)
        await pg.evaluate(f"()=>{{{K}.start('final')}}"); await pg.wait_for_timeout(1500)
        ok('no glowing path for pilots', not await pg.evaluate(f"()=>{K}.GUIDE.on"))
        await pg.evaluate(f"()=>{{while({K}.camMode()!==1){K}.cycleCam()}}"); await pg.wait_for_timeout(600)
        ok('pilot gets the six pack in the cockpit', await pg.evaluate("()=>document.getElementById('sixpack').classList.contains('on')"))

        # switch to Easy (internally 'rookie') from settings
        await pg.evaluate(f"()=>{K}.openMenu('sSet')"); await pg.wait_for_timeout(200)
        await finger(pg, '#sSet [data-skill="rookie"]'); await pg.wait_for_timeout(200)
        ok('settings changes the skill', await pg.evaluate(f"()=>{K}.skill()") == 'rookie')
        await pg.evaluate(f"()=>{{{K}.start('runway')}}"); await pg.wait_for_timeout(2500)
        lab = await pg.evaluate("()=>['lIas','lAlt','lVs','lHdg'].map(i=>document.getElementById(i).textContent)")
        ok('rookie labels are Speed Height Climbing Direction', lab == ['Speed', 'Height', 'Climbing', 'Direction'], lab)
        hdg = await pg.evaluate("()=>document.getElementById('hHdg').textContent")
        ok('direction reads as a compass point', hdg in ['N','NE','E','SE','S','SW','W','NW'], hdg)
        atc = await pg.evaluate("()=>document.getElementById('atc').innerText")
        ok('rookie radio has a plain English subtitle', 'Tower says: you can take off now.' in atc, atc)
        ok('rookie flight has easy flight on', await pg.evaluate(f"()=>{K}.state().easy") is True)
        await pg.evaluate(f"()=>{{{K}.touchIn.active=true;{K}.touchIn.elev=0.7;}}"); await pg.wait_for_timeout(500)
        thr = await pg.evaluate(f"()=>{K}.state().throttle")
        await pg.evaluate(f"()=>{{{K}.touchIn.active=false;{K}.touchIn.elev=0;}}")
        ok('rookie: pulling back on the runway sets full power', thr > 0.95, thr)
        for _ in range(40):
            await pg.evaluate(f"()=>{{const s={K}.state();{K}.touchIn.active=true;{K}.touchIn.elev=s.onGround?0.5:0;{K}.ff(2)}}"); await pg.wait_for_timeout(120)
            if await pg.evaluate(f"()=>{K}.state().agl>160"): break
        await pg.evaluate(f"()=>{{{K}.touchIn.active=false;{K}.touchIn.elev=0;}}"); await pg.wait_for_timeout(400)
        s = await pg.evaluate(f"()=>({{agl:Math.round({K}.state().agl),thr:{K}.state().throttle,crashed:{K}.state().crashed}})")
        ok('rookie: power eases back to climb after takeoff', s['agl'] > 150 and s['thr'] < 0.95 and not s['crashed'], s)
        await pg.evaluate(f"()=>{{{K}.start('final')}}"); await pg.wait_for_timeout(1500)
        g = await pg.evaluate(f"()=>({{on:{K}.GUIDE.on,n:{K}.GUIDE.hoops.filter(h=>h.visible).length,end:{K}.GUIDE.end&&{K}.GUIDE.end.num}})")
        ok('rookie gets the glowing path to runway 1 on final', g['on'] and g['n'] >= 3 and g['end'] == '1', g)
        await pg.evaluate(f"()=>{{while({K}.camMode()!==1){K}.cycleCam()}}"); await pg.wait_for_timeout(600)
        ok('rookie never sees the six pack', not await pg.evaluate("()=>document.getElementById('sixpack').classList.contains('on')"))
        ok('plain English maps traffic and landing calls', await pg.evaluate(f"""()=>{{const P={K}.plainOf,cs={K}.state()&&'x';
          return [P({{who:'Glendale Tower 121.0',kind:'tower',text:'Skyhawk 8401L, traffic 3 o\\'clock, 2 miles, same altitude, a Cessna.'}}),
                  P({{who:'Viper 21',kind:'fighter',text:'Viper 21, bingo.'}})]}}""") ==
           ['Tower says: another plane is nearby, to your right.', 'Other pilots talking. Nothing for you.'])
        ok('no page errors', not pg.errs, pg.errs[:3])
        await b.close()
    sys.exit(ok.done('skill_check'))
asyncio.run(main())
