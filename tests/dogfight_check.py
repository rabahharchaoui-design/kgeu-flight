# Red Flag Dogfight (5.1): the arcade card starts it, the F-16 airborne over the Goldwater Range at
# 15,000 ft, wave 1's bandit flies (above 6,000 ft, inside the arena), the four waves of 1, 2, 3 and 4
# killed through the test hook end in a win with 10 kills on the results card, a round clock running
# out ends the run, the dogfight music is forced during the run and released after, the map icon.
# Run: .venv/bin/python tests/dogfight_check.py
import asyncio, math, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, finger, IPHONE_15
ok = Checks()
K = "window.__kgeu"
STEP = "(n)=>{const K=window.__kgeu;for(let i=0;i<n;i++)K.stepFrame(0.1,false,true);K.stepFrame(0,true);}"

async def step(pg, secs):
    await pg.evaluate(STEP, int(round(secs * 10)))

async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuType': 'cessna'})
        await pg.evaluate(f"()=>{{{K}.openMenu();{K}.nav('sArc')}}"); await pg.wait_for_timeout(300)
        card = await pg.evaluate("()=>{const c=document.querySelector('#arcCards [data-m=dogfight]');return c&&{soon:!!c.querySelector('.soon'),stars:!!c.querySelector('.stars'),txt:c.innerText}}")
        ok('the Red Flag Dogfight card no longer says Coming soon', card and not card['soon'] and card['stars'] and 'Coming soon' not in card['txt'], card)
        await finger(pg, '#arcCards [data-m="dogfight"]'); await pg.wait_for_timeout(600)
        await pg.evaluate(f"()=>{{{K}.DF.test.noBanditFire=true;}}")   # 5.3: the bandits' missiles stay off here (dogfight_defense_check)
        await finger(pg, '#dfbGo'); await pg.wait_for_timeout(200)     # 5.4: the briefing card's FIGHT'S ON starts the run
        s = await pg.evaluate(f"""()=>{{const K={K},s=K.state(),D=K.DF;return {{on:D.on,menu:document.getElementById('menu').classList.contains('on'),type:s.type,ground:s.onGround,gear:s.gearDown,
          ft:(s.pos.y-1.5)*3.28084+1071,kt:s.ias*1.943844,dc:Math.hypot(s.pos.x-D.C.x,s.pos.z-D.C.z)/1852,n:D.bandits.length,wave:D.wave,t:D.t,
          hud:document.getElementById('missT').textContent,forced:K.music().forced}}}}""")
        ok('the card starts the dogfight: an F-16, airborne, gear up', s['on'] and not s['menu'] and s['type'] == 'f16' and not s['ground'] and not s['gear'], s)
        ok('at about 15,000 ft and 400 kt, inside the arena near DF.C', abs(s['ft'] - 15000) < 300 and abs(s['kt'] - 400) < 25 and s['dc'] < 12, s)
        ok('wave 1 of 4: one bandit, a 90 s clock on the mission HUD', s['n'] == 1 and s['wave'] == 1 and 89 < s['t'] <= 90 and s['hud'].startswith('WAVE 1/4') and '1:30' in s['hud'], s)
        ok('MUSIC.forced is dogfight.m4a during the run', s['forced'] == 'dogfight.m4a', s['forced'])
        g = await pg.evaluate(f"""()=>{{const K={K},s=K.state(),b=K.DF.bandits[0],e=new THREE.Euler().setFromQuaternion(s.quat,'YXZ'),h=-e.y,
          br=Math.atan2(b.p.x-s.pos.x,-(b.p.z-s.pos.z)),d=Math.atan2(Math.sin(br-h),Math.cos(br-h));
          return {{off:Math.abs(d)*57.3,nm:Math.hypot(b.p.x-s.pos.x,b.p.z-s.pos.z)/1852,ft:(b.p.y-1.5)*3.28084+1071,keys:['p','v','alive','state','hp'].every(k=>k in b)}}}}""")
        ok('the wave 1 bandit spawns in front, 3 to 5 nm out, 12,000 to 18,000 ft, with {p, v, alive, state, hp}',
           g['off'] < 20 and 2.9 < g['nm'] < 5.1 and 11900 < g['ft'] < 18100 and g['keys'], g)
        # 30 sim seconds: it flies, stays above 6,000 ft and inside the arena
        tr = []
        for _ in range(30):
            await step(pg, 1)
            tr.append(await pg.evaluate(f"()=>{{const D={K}.DF,b=D.bandits[0];return [b.p.x,b.p.z,(b.p.y-1.5)*3.28084+1071,Math.hypot(b.p.x-D.C.x,b.p.z-D.C.z),b.state,b.alive]}}"))
        moved = sum(math.hypot(tr[i][0] - tr[i - 1][0], tr[i][1] - tr[i - 1][1]) for i in range(1, len(tr)))
        ok('over 30 s the bandit moves, stays above 6,000 ft and inside the arena', moved > 3000 and min(t[2] for t in tr) >= 5999 and max(t[3] for t in tr) <= 12 * 1852 and all(t[5] for t in tr),
           {'moved_m': round(moved), 'minFt': round(min(t[2] for t in tr)), 'maxNm': round(max(t[3] for t in tr) / 1852, 1), 'states': sorted(set(t[4] for t in tr))})
        # pushed into a dive near the floor, it pulls out above 6,000 ft
        await pg.evaluate(f"()=>{{const b={K}.DF.bandits[0];b.p.y=(6600-1071)/3.28084+1.5;b.gam=-0.5;b.state='EVADE';b.st=0;}}")
        lo = 1e9
        for _ in range(6):
            await step(pg, 1); lo = min(lo, await pg.evaluate(f"()=>({K}.DF.bandits[0].p.y-1.5)*3.28084+1071"))
        ok('a bandit diving at 6,600 ft never goes below 6,000 ft', lo >= 5999, round(lo))
        ok('the wave clock runs down with the sim', await pg.evaluate(f"()=>{K}.DF.t<55&&{K}.DF.t>45"), await pg.evaluate(f"()=>{K}.DF.t"))
        # kill through the four waves with the test hook
        counts = []
        for w in range(1, 5):
            n = await pg.evaluate(f"()=>{K}.DF.bandits.length")
            counts.append(n)
            await pg.evaluate(f"()=>{{const D={K}.DF;D.bandits.slice().forEach(b=>{K}.dfKill(b,'test'));}}")
            if w < 4:
                await step(pg, 2)
                mid = await pg.evaluate(f"()=>({{wave:{K}.DF.wave,hud:document.getElementById('missT').textContent,falling:{K}.DF.pool.some(b=>b.fall)}})")
                if w == 1: ok('after a wave: a breather, the HUD says CLEAR, the dead bandit falls', mid['wave'] == 1 and 'CLEAR' in mid['hud'] and mid['falling'], mid)
                await step(pg, 3)
        ok('the waves are 1, 2, 3 and 4 bandits', counts == [1, 2, 3, 4], counts)
        await step(pg, 4); await pg.wait_for_timeout(300)
        r = await pg.evaluate(f"""()=>{{const D={K}.DF;return {{won:D.won,kills:D.kills,bank:D.bank.length,on:document.getElementById('arcOv').classList.contains('on'),
          title:document.getElementById('aTitle').textContent,lines:document.getElementById('aLines').innerText,best:{K}.SCORE.best['arc:dogfight'],forced:{K}.music().forced}}}}""")
        ok('all four waves cleared: a win, 10 kills, four banked rounds', r['won'] and r['kills'] == 10 and r['bank'] == 4, {k: r[k] for k in ('won', 'kills', 'bank')})
        ok('the results card shows Red Flag Dogfight with 10 kills', r['on'] and 'Red Flag Dogfight' in r['title'] and '10 of 10' in r['lines'] and 'Waves cleared' in r['lines'], (r['title'], r['lines']))
        ok('the best is saved under the arcade records', r['best'] and r['best']['pts'] == 1000 and r['best']['kills'] == 10, r['best'])
        ok('the music is still forced on the results card', r['forced'] == 'dogfight.m4a', r['forced'])
        await finger(pg, '#aHub'); await pg.wait_for_timeout(400)
        m = await pg.evaluate(f"()=>({{menu:document.getElementById('menu').classList.contains('on'),forced:{K}.music().forced,live:{K}.DF.live,vis:{K}.DF.pool.some(b=>b.g.visible)}})")
        ok('MAIN MENU: MUSIC.forced back to null, the bandits gone', m['menu'] and m['forced'] is None and not m['live'] and not m['vis'], m)
        await pg.evaluate(f"()=>{K}.nav('sArc')"); await pg.wait_for_timeout(300)
        em = await pg.evaluate("()=>document.querySelector('#arcCards [data-m=dogfight] .sc').innerText")
        ok('the arcade card shows the best', '1000 pts' in em.replace(',', '') and '10 kills' in em, em)
        # a round clock running out ends the run; Try again starts a new one
        await finger(pg, '#arcCards [data-m="dogfight"]'); await pg.wait_for_timeout(500)
        await finger(pg, '#dfbGo'); await pg.wait_for_timeout(200)
        await pg.evaluate(f"()=>{{{K}.DF.t=1.5;}}"); await step(pg, 4); await pg.wait_for_timeout(300)
        r = await pg.evaluate(f"()=>({{on:{K}.DF.on,done:{K}.DF.done,why:{K}.DF.why,won:{K}.DF.won,card:document.getElementById('arcOv').classList.contains('on'),title:document.getElementById('aTitle').textContent}})")
        ok('the wave clock at 0 ends the run with the card', not r['on'] and r['done'] and r['why'] == 'time' and not r['won'] and r['card'] and 'out of time' in r['title'], r)
        await finger(pg, '#aRetry'); await pg.wait_for_timeout(500)
        await finger(pg, '#dfbGo'); await pg.wait_for_timeout(200)
        r = await pg.evaluate(f"()=>({{on:{K}.DF.on,wave:{K}.DF.wave,n:{K}.DF.bandits.length,kills:{K}.DF.kills,forced:{K}.music().forced,card:document.getElementById('arcOv').classList.contains('on')}})")
        ok('Try again restarts the dogfight at wave 1', r['on'] and r['wave'] == 1 and r['n'] == 1 and r['kills'] == 0 and r['forced'] == 'dogfight.m4a' and not r['card'], r)
        # three hits end it (5.3 brings the bandits' weapons; dfHit is the hook)
        await pg.evaluate(f"()=>{{{K}.dfHit();{K}.dfHit();{K}.dfHit();}}"); await step(pg, 2)
        ok('three hits end the run', await pg.evaluate(f"()=>!{K}.DF.on&&{K}.DF.why==='hits'&&{K}.DF.hits===3"))
        await pg.evaluate(f"()=>{K}.openMenu()"); await pg.wait_for_timeout(200)
        ok('back at the menu MUSIC.forced is null', await pg.evaluate(f"()=>{K}.music().forced===null"))
        # the map: the dogfight icon over the Goldwater Range, in the legend, and a tap sets a waypoint
        await pg.evaluate(f"()=>{{{K}.pick('cessna');{K}.pickBase('kgeu');{K}.start('runway')}}"); await pg.wait_for_timeout(800)
        await pg.evaluate(f"()=>{{{K}.fmOpen();{K}.FM.cx={K}.DF.C.x;{K}.FM.cz={K}.DF.C.z;{K}.FM.scale=0.02;{K}.fmFlush();}}"); await pg.wait_for_timeout(300)
        mp = await pg.evaluate(f"""()=>{{const L={K}.LBL(),P=L.placed,d=P.find(p=>p.kind==='dogfight'),t=P.find(p=>p.kind==='terrain'&&Math.abs((p.box[0]+p.box[2])/2-innerWidth/2)<40&&p.box[2]-p.box[0]>110);
          return {{icon:!!d,at:d?[(d.box[0]+d.box[2])/2,(d.box[1]+d.box[3])/2]:null,leg:[...document.querySelectorAll('#mapLegL .lrow')].map(b=>b.dataset.kind),terrain:!!t,kinds:[...new Set(P.map(p=>p.kind))]}}}}""")
        ok('the full map has the Red Flag Dogfight icon at DF.C, a legend row and the range name', mp['icon'] and 'dogfight' in mp['leg'] and mp['terrain'], mp)
        if mp['at']:
            await pg.touchscreen.tap(mp["at"][0], mp["at"][1]); await pg.wait_for_timeout(400)
            dd = await pg.evaluate(f"()=>{K}.dest()")
            ok('tapping it sets a waypoint', dd and dd.get('name') == 'Red Flag Dogfight', dd)
        ok('no console errors', not pg.errs, pg.errs[:3])
        await b.close()
    sys.exit(ok.done('dogfight_check'))
asyncio.run(main())
