# Throwaway screenshots for TCAS (item 4.1b, on top of the AI traffic). iPhone 15
# landscape (844x390, device scale 2) except the one portrait shot. The player is
# placed by hand (K.state()) 3,000 ft over the desert west of KGEU, heading north,
# level; traffic is spawned with the 'script' TCAS test state (tfcSpawn('airliner',
# {state:'script', x,z,y,hdg,gs})), which flies straight and level at a fixed
# altitude and speed, same as tests/tcas_check.py's tcasConflict() uses internally.
#
# The geometry for the three-symbol panel shot: an intruder on an exact reciprocal
# line to the player's, offset side-to-side by dx and up/down by dy with both level
# (no relative vertical speed), has a closest-approach miss distance of exactly dx
# and a closest-approach vertical miss of exactly dy (the sideways/vertical offsets
# never close). So: a big altitude split (dy beyond the 850/1200 ft boxes) always
# reads OTHER no matter the range; a small one within the 6 nm/1200 ft box but with
# a big horizontal miss always reads PROXIMATE; and dx=0.4 nm, dy=700 ft (inside the
# 0.5 nm/850 ft TA box, outside the 0.3 nm/600 ft RA box) reads TRAFFIC (TA) and
# stays there, since the RA box never triggers.
#
# Usage: .venv/bin/python tests/world_tcas_shots.py
import asyncio, os
from playwright.async_api import async_playwright
from harness import serve, launch, page, IPHONE_15

OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'overnight-screenshots', 'world', 'tcas'))
K = 'window.__kgeu'

# free flight, player at (x,z), `ft` MSL, heading north, 100 kt, level, no auto traffic;
# flaps retracted and the tower line cleared (both leftovers of start('final')'s approach
# config) and the camera snapped to the new position so the chase view isn't still
# catching up from the old one
PLACE = """([type,skill,x,z,ft])=>{const K=window.__kgeu;K.setSkill(skill);K.pick(type);K.pickBase('kgeu');K.start('final');
  K.TFC.auto=false;K.tfcClear();const s=K.state(),V=100/1.94384,y=(ft-1071)/3.28084+(K.TYPES[type].gear||1.5);
  s.pos.set(x,y,z);s.vel.set(0,0,-V);s.quat.setFromEuler(new THREE.Euler(0,0,0,'YXZ'));if(s.w)s.w.set(0,0,0);s.onGround=false;s.ap=null;s.flapIdx=0;
  document.getElementById('atc').classList.remove('on');K.snapCam();
  for(let i=0;i<3;i++){K.stepFrame(0.1,false,true);s.vel.y=0;}
  return {agl:s.agl,y:s.pos.y};}"""

# the three-symbol trio: a (OTHER, hollow diamond, 2 nm east / 2,000 ft above), b (PROXIMATE,
# filled diamond, 1.5 nm west / 400 ft above, parallel so it never closes), c (TRAFFIC, amber
# circle, a reciprocal intruder 0.4 nm right / 700 ft above the player's own track)
SPAWN_TRIO = """()=>{const K=window.__kgeu,s=K.state();const FT=0.3048,NM=1852,KT=0.514444;
  const px=s.pos.x,pz=s.pos.z,py=s.pos.y,Vp=100*KT,Vi=250*KT;
  const mk=(dx,dz,dy,hdg,gs)=>K.tfcSpawn('airliner',{state:'script',x:px+dx,z:pz+dz,y:py+dy,hdg:hdg,gs:gs});
  return {a:mk(2*NM,0,2000*FT,0,Vp),b:mk(-1.5*NM,0,400*FT,0,Vp),c:mk(0.4*NM,-3601,700*FT,Math.PI,Vi)};}"""

# n frames of 0.1 s, held at 100 kt north, level unless following an active RA (climb/descend
# at ~1,800 fpm) -- pins vx and vz too (not just vy), the way tests/tcas_check.py's FLY does;
# with no stick input at all the sim will otherwise let the aircraft roll/yaw off slowly
FLY = """([n,follow])=>{const K=window.__kgeu,s=K.state(),T=K.TCAS,V=100/1.94384;
  for(let i=0;i<n;i++){const S=T.state();s.vel.set(0,follow&&S.ra?(S.sense==='climb'?9.2:-9.2):0,-V);K.stepFrame(0.1,false,true);}
  return T.state();}"""


async def settle(pg, n=5):
    await pg.evaluate("(n)=>{const K=window.__kgeu;for(let i=0;i<n;i++)K.stepFrame(1/60);}", n)


async def shot(pg, name):
    path = os.path.join(OUT, name)
    await pg.screenshot(path=path, timeout=120000)
    print('  wrote', path)


async def fly_until(pg, pred, step=5, cap=700):
    """Advance in small bursts (follow=True) until pred() is true or the frame cap is hit."""
    n = 0
    while n < cap:
        await pg.evaluate(FLY, [step, True])
        n += step
        if await pg.evaluate(pred):
            return True
    return False


async def main():
    os.makedirs(OUT, exist_ok=True)
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'})

        # a: panel_hard.png -- Hard, Cessna, 3,000 ft west of KGEU, the three-symbol trio
        await pg.evaluate(PLACE, ['cessna', 'pilot', -12000, 0, 3000])
        trio = await pg.evaluate(SPAWN_TRIO)
        print('  trio spawned', trio)
        await pg.evaluate(FLY, [10, False])
        lv = await pg.evaluate(f"()=>{K}.TCAS.levels().map(l=>({{t:l.type,lv:l.lv,level:l.level,relAlt:l.relAlt,range:l.range}}))")
        print('  panel_hard levels:', lv)
        await settle(pg)
        await shot(pg, 'panel_hard.png')

        # b: ra_hard.png / ra_hard_cockpit.png -- Hard, the scripted head-on, flown into the RA
        await pg.evaluate(PLACE, ['cessna', 'pilot', -12000, 0, 3000])
        await pg.evaluate(f"()=>{K}.TCAS.tcasConflict('headon')")
        got_ra = await fly_until(pg, f"()=>{K}.TCAS.state().ra")
        print('  ra_hard: got RA ->', got_ra, await pg.evaluate(f"()=>{K}.TCAS.state()"))
        await settle(pg)
        await shot(pg, 'ra_hard.png')
        # cockpit camera: cycleCam once (chase -> cockpit) for the six pack VSI arcs
        await pg.evaluate(f"()=>{K}.cycleCam()")
        await settle(pg, 8)
        still_ra = await pg.evaluate(f"()=>{K}.TCAS.state().ra")
        print('  ra_hard_cockpit: still in RA ->', still_ra)
        await shot(pg, 'ra_hard_cockpit.png')
        await pg.evaluate(f"()=>{K}.cycleCam()")  # back to chase, tidy

        # c: ra_easy.png -- Easy (rookie), same conflict, the big arrow
        await pg.evaluate(PLACE, ['cessna', 'rookie', -12000, 0, 3000])
        await pg.evaluate(f"()=>{K}.TCAS.tcasConflict('headon')")
        got_arrow = await fly_until(pg, "()=>document.getElementById('tcasRA').classList.contains('on')")
        print('  ra_easy: arrow on ->', got_arrow, await pg.evaluate("()=>document.getElementById('tcasRA').textContent.trim()"))
        await settle(pg)
        await shot(pg, 'ra_easy.png')

        # d: minimap_symbols.png -- normal flight view, the trio on the mini map
        await pg.evaluate(PLACE, ['cessna', 'pilot', -12000, 0, 3000])
        await pg.evaluate(SPAWN_TRIO)
        await pg.evaluate(FLY, [10, False])
        await settle(pg)
        await shot(pg, 'minimap_symbols.png')

        # e: fullmap_symbols.png -- full map open, centred on the player, the trio visible
        await pg.evaluate(f"""()=>{{const K={K};K.fmOpen();K.FM.cx=K.state().pos.x;K.FM.cz=K.state().pos.z;K.FM.scale=0.02;K.fmFlush();}}""")
        await pg.wait_for_timeout(250)
        await shot(pg, 'fullmap_symbols.png')
        await pg.evaluate(f"()=>{K}.fmClose()")

        # f: settings_tcas.png -- the Settings screen, TCAS toggle row
        await pg.evaluate(f"()=>{K}.openMenu('sSet')")
        await pg.wait_for_timeout(250)
        await shot(pg, 'settings_tcas.png')

        await pg.context.close()

        # g: portrait_panel.png -- 390x844 portrait, Hard, in flight (dismiss the "turn your
        # phone sideways" prompt the way lb_merge_check.py does: add body.portraitok)
        pg2 = await page(b, url, vp={'width': 390, 'height': 844}, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'})
        await pg2.evaluate("()=>document.body.classList.add('portraitok')")
        await pg2.evaluate(PLACE, ['cessna', 'pilot', -12000, 0, 3000])
        await pg2.evaluate(SPAWN_TRIO)
        await pg2.evaluate(FLY, [10, False])
        await settle(pg2)
        await shot(pg2, 'portrait_panel.png')
        await pg2.context.close()

        await b.close()
    srv.shutdown()


asyncio.run(main())
