# Feature 7: the maps. Mini map heading up in a corner; tap it for a full north up
# map over the paused game with every airport and landmark; pinch and drag; tap a
# runway end to set a destination; HUD distance, bearing, time; the guide path near
# the runway; clear it with one tap. Run: .venv/bin/python tests/map_check.py
import asyncio, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, finger
ok = Checks()
K = "window.__kgeu"
async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        for skill in ('pilot', 'rookie'):
            pg = await page(b, url, storage={'kgeuOnboard': skill, 'kgeuTut': '1'})
            await pg.evaluate(f"()=>{{{K}.pick('cessna');{K}.pickBase('kgeu');{K}.start('final')}}"); await pg.wait_for_timeout(1200)
            m = await pg.evaluate("()=>{const r=document.getElementById('map').getBoundingClientRect();return [r.x,r.y,r.width,r.height]}")
            ok(f'{skill}: mini map sits in the top left corner', m[0] < 20 and m[1] < 20 and m[2] >= 88, m)
            await finger(pg, '#map'); await pg.wait_for_timeout(500)
            s = await pg.evaluate(f"()=>({{on:document.getElementById('mapOv').classList.contains('on'),paused:{K}.paused()}})")
            ok(f'{skill}: tapping the mini map opens the full map and pauses', s == {'on': True, 'paused': True}, s)
            if skill == 'pilot':
                vis = await pg.evaluate(f"""()=>{{const W=innerWidth,H=innerHeight,P={K}.fmP,inb=([x,y])=>x>0&&y>0&&x<W&&y<H;
                  return {{kgeu:inb(P(0,0)),luke:inb(P({K}.LUKE.x,{K}.LUKE.z)),phx:inb(P({K}.SKY_HARBOR.x,{K}.SKY_HARBOR.z))}}}}""")
                ok('full map opens with Glendale, Luke and Sky Harbor all on screen', all(vis.values()), vis)
                sc0 = await pg.evaluate(f"()=>{K}.FM.scale")
                await finger(pg, '#mapIn'); await pg.wait_for_timeout(200)
                ok('zoom in works', await pg.evaluate(f"()=>{K}.FM.scale") > sc0 * 1.4)
                # pinch out with two fingers
                await pg.evaluate("""()=>{const c=document.getElementById('fmap'),W=innerWidth/2,H=innerHeight/2,ev=(t,id,x)=>c.dispatchEvent(new PointerEvent(t,{pointerId:id,clientX:x,clientY:H,bubbles:true}));
                  ev('pointerdown',1,W-40);ev('pointerdown',2,W+40);for(let i=1;i<=5;i++){ev('pointermove',1,W-40-i*20);ev('pointermove',2,W+40+i*20);}ev('pointerup',1,W-140);ev('pointerup',2,W+140);}""")
                sc1 = await pg.evaluate(f"()=>{K}.FM.scale")
                ok('pinch zooms', sc1 > sc0 * 1.4 * 1.8, f'{sc0:.4f} -> {sc1:.4f}')
                c0 = await pg.evaluate(f"()=>{K}.FM.cx")
                await pg.evaluate("""()=>{const c=document.getElementById('fmap'),ev=(t,x)=>c.dispatchEvent(new PointerEvent(t,{pointerId:5,clientX:x,clientY:200,bubbles:true}));
                  ev('pointerdown',300);for(let i=1;i<=5;i++)ev('pointermove',300+i*20);ev('pointerup',400);}""")
                ok('drag pans', await pg.evaluate(f"()=>{K}.FM.cx") < c0 - 1, '')
                ok('no destination set by a drag', await pg.evaluate(f"()=>{K}.dest()") is None)
                await pg.evaluate(f"()=>{K}.fmClose()"); await pg.evaluate(f"()=>{K}.fmOpen()"); await pg.wait_for_timeout(200)
            # tap the Luke 21R threshold on the map
            end = await pg.evaluate(f"()=>{{const e={K}.RWY_ENDS.find(e=>e.num==='21R');const q={K}.fmP(e.x,e.z);return q}}")
            await pg.touchscreen.tap(end[0], end[1]); await pg.wait_for_timeout(300)
            d = await pg.evaluate(f"()=>{K}.dest()")
            ok(f'{skill}: tapping a runway end sets the destination', d == {'apt': 'Luke AFB', 'num': '21R'}, d)
            await finger(pg, '#mapX'); await pg.wait_for_timeout(700)
            ok(f'{skill}: closing the map resumes', not await pg.evaluate(f"()=>{K}.paused()"))
            txt = await pg.evaluate("()=>document.getElementById('hDest').hidden?null:document.getElementById('dTxt').innerText")
            if skill == 'pilot':
                ok('pilot HUD: distance in nm, bearing, time', txt and 'nm' in txt and '°' in txt and ':' in txt, txt)
            else:
                ok('rookie HUD: plain miles and minutes', txt and 'Luke AFB runway 21R' in txt and 'mi' in txt, txt)
                big = await pg.evaluate("()=>document.getElementById('dArrow').getBoundingClientRect().width")
                ok('rookie gets a big arrow', big >= 36, big)
            # guide path appears near the destination
            await pg.evaluate(f"""()=>{{const K={K},e=K.RWY_ENDS.find(e=>e.num==='21R'),s=K.state();s.pos.x=e.x-Math.sin(e.h)*6000;s.pos.z=e.z+Math.cos(e.h)*6000;
              s.pos.y=350;s.vel.set(Math.sin(e.h)*50,0,-Math.cos(e.h)*50);s.quat.setFromAxisAngle(new THREE.Vector3(0,1,0),-e.h);}}""")
            await pg.wait_for_timeout(900)
            g = await pg.evaluate(f"()=>({{on:{K}.GUIDE.on,end:{K}.GUIDE.end&&{K}.GUIDE.end.num}})")
            ok(f'{skill}: the glowing guide path shows near the destination', g == {'on': True, 'end': '21R'}, g)
            await finger(pg, '#hDest'); await pg.wait_for_timeout(300)
            ok(f'{skill}: one tap clears the destination', await pg.evaluate(f"()=>{K}.dest()") is None and await pg.evaluate("()=>document.getElementById('hDest').hidden"))
            ok(f'{skill}: no page errors', not pg.errs, pg.errs[:3])
            await pg.context.close()
        await b.close()
    sys.exit(ok.done('map_check'))
asyncio.run(main())
