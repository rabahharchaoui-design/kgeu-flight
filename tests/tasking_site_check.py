# Overwatch2 item 1: the OVERWATCH compound out in the desert, reached by a dirt track. 60 seeds rolled (taskStop, then
# taskStart with TASK.test.noBrief): every site passes owSiteOK, 1.5 km from every divided highway and 1 km from every
# road of any kind, 9 to 16 km from Luke on a bearing of 205 to 350; at least 25 of them more than 600 m apart; two
# terrain classes or more; every track ends on a real road (within 10 m of one) and no step of it is steeper than 12
# percent; the track ribbon under 2,000 triangles; the briefing names the ground; the map's DEST is the compound; tqLL
# agrees with geoLL; the roll, the validator and the track inside 60 ms; the slot list (built off the frame) holds 25 or more. The hand picked fallback passes owSiteOK. Then
# one run flown to the compound: the shader program count before taskStart and after 30 s in the ball view with the
# track in view must not rise. Prints the site table. Run: .venv/bin/python -u tests/tasking_site_check.py
import asyncio, json, re, time
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, finger
ok = Checks()
K = 'window.__kgeu'
STEP = "(n)=>{for(let i=0;i<n;i++)window.__kgeu.stepFrame(0.1,false,true)}"
async def adv(pg, sec): await pg.evaluate(STEP, int(sec * 10))
async def until(pg, cond, maxs=300, step=1):
    for _ in range(int(maxs / step)):
        await adv(pg, step)
        if await pg.evaluate(cond): return True
    return False
SHOW = f"()=>{{const a={K}.task().ask;return !!(a&&a.shown)}}"
ROLL = """(sd)=>{const K=window.__kgeu;K.taskStop();const t0=performance.now();K.taskStart('overwatch',{seed:sd});const ms=performance.now()-t0,d=K.TASK.d;
  if(!d||!d.route)return null;
  const G=K.groundHeight,P=d.route;let mg=0;for(let i=0;i+1<P.length;i++){const L=Math.hypot(P[i+1].x-P[i].x,P[i+1].z-P[i].z);if(L>0.5)mg=Math.max(mg,Math.abs(G(P[i+1].x,P[i+1].z)-G(P[i].x,P[i].z))/L);}
  const e=P[P.length-1],I=K.owSiteInfo(d.c.x,d.c.z),E=K.owSiteInfo(e.x,e.z),ll=K.geoLL(d.c.x,d.c.z),t=K.tkLL(d.c.x,d.c.z);
  return {sd:sd,x:d.c.x,z:d.c.z,ok:K.owSiteOK(d.c.x,d.c.z),terr:d.terrain,h:I.h,road:I.nearestRoad,kind:I.nearestRoadKind,div:I.nearestDivided,
    len:d.routeLen,endRoad:E.nearestRoad,endKind:d.roadEnd.kind,mg:mg,tris:d.track.geometry.index.count/3,ms:d.ms,start:ms,dist:d.dist,brg:d.brg,tries:d.tries,
    sit:K.TASKS.overwatch.brief(d).sit,dest:K.dest(),ll:ll,tq:t,trackOn:K.TASK.objs.includes(d.track)}}"""
def mins(s):   # 'N33°31.2′ W112°22.5′' -> [33.52, 112.375]
    m = re.findall(r'(\d+)°(\d+\.\d)', s); return [int(a) + float(b) / 60 for a, b in m]

async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp={'width': 844, 'height': 390}, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'})
        for _ in range(120):
            if await pg.evaluate(f"()=>{K}.mapdReady()"): break
            await pg.wait_for_timeout(500)
        for _ in range(120):
            sl = await pg.evaluate(f"()=>{K}.owSlots()")
            if sl['n']: break
            await pg.wait_for_timeout(500)
        print('  slots (sites 650 m apart in the ring):', sl['n'], ' built off the frame in', sl['ms'], 'ms of 4 ms slices')
        ok('the slots are built, at least 25 of them', (sl['n'] or 0) >= 25, sl)
        fb = await pg.evaluate(f"()=>{{const K={K},f=K.owFallback;return [K.owSiteOK(f.x,f.z),K.owRoadPt(f.x,f.z),K.owSiteInfo(f.x,f.z)]}}")
        ok('the hand picked fallback site passes owSiteOK and has a road for its track', fb[0] is None and fb[1] is not None, fb)
        await pg.evaluate(f"()=>{{{K}.TASK.test.noBrief=true}}")
        rows = []
        for sd in range(1, 61):
            r = await pg.evaluate(ROLL, sd)
            rows.append(r)
        good = [r for r in rows if r]
        ok('60 seeds roll 60 taskings', len(good) == 60, len(good))
        print(' seed terrain     h(m)  road(m) kind      divided(m)  track(m)  tries  roll+track(ms)')
        for r in good:
            print(f" {r['sd']:4d} {r['terr']:10s} {r['h']:6.1f} {r['road']:7d}  {str(r['kind']):9s} {r['div']:8d}  {r['len']:8d}  {r['tries']:5d}  {r['ms']['roll']+r['ms']['track']:.1f}")
        bad = [r['sd'] for r in good if r['ok'] is not None]
        ok('every site passes owSiteOK', not bad, bad)
        ok('every site 9 to 16 km from Luke on a bearing of 205 to 350', all(9000 <= r['dist'] <= 16000 and 205 <= r['brg'] <= 350 for r in good), [(r['sd'], round(r['dist']), round(r['brg'])) for r in good if not (9000 <= r['dist'] <= 16000 and 205 <= r['brg'] <= 350)])
        ok('nearest divided highway 1,500 m or more, nearest road of any kind 1,000 m or more, for every site',
           all(r['div'] >= 1500 and r['road'] >= 1000 for r in good), [(r['sd'], r['div'], r['road']) for r in good if r['div'] < 1500 or r['road'] < 1000])
        P = []
        for r in good:
            if all(((r['x'] - q['x']) ** 2 + (r['z'] - q['z']) ** 2) ** 0.5 > 600 for q in P): P.append(r)
        ok('at least 25 sites more than 600 m apart from each other', len(P) >= 25, len(P))
        terr = {r['terr'] for r in good}
        ok('at least two terrain classes', len(terr) >= 2, sorted(terr))
        ok('every track ends on a real road (within 10 m), never a motorway or its ramps', all(r['endRoad'] <= 10 and r['endKind'] not in (0, 3) for r in good), [(r['sd'], r['endRoad'], r['endKind']) for r in good if r['endRoad'] > 10 or r['endKind'] in (0, 3)])
        ok('no track step steeper than 12 percent', all(r['mg'] <= 0.12 for r in good), max(r['mg'] for r in good))
        ok('the track ribbon: built and in the tasking\'s objects, under 2,000 triangles', all(r['trackOn'] and r['tris'] < 2000 for r in good), max(r['tris'] for r in good))
        WORD = {'flats': 'flats', 'foothills': 'foothills', 'valley': 'valley', 'wash': 'wash'}
        ok('the briefing names the ground', all(WORD[r['terr']] in r['sit'] for r in good), good[0]['sit'])
        ok('the map DEST is the compound', all(r['dest'] and abs(r['dest']['x'] - r['x']) < 0.01 and abs(r['dest']['z'] - r['z']) < 0.01 for r in good))
        dl = max(max(abs(a - abs(c)) * 60 for a, c in zip(mins(r['tq']), r['ll'])) for r in good)
        ok('tqLL agrees with geoLL within 0.05 minutes', dl <= 0.0501, dl)
        worst = max(r['ms']['roll'] + r['ms']['track'] for r in good)
        print(f"  roll + validator + track: worst {worst:.1f} ms, mean {sum(r['ms']['roll'] + r['ms']['track'] for r in good) / len(good):.1f} ms; taskStart as a whole worst {max(r['start'] for r in good):.0f} ms")
        ok('the roll, the validator and the track build inside 60 ms', worst < 60, worst)
        ok('no console errors (rolls)', not pg.errs, pg.errs[:3])
        await pg.close()
        # the program count in flight: the track in the ball view for 30 s
        pg = await page(b, url, vp={'width': 844, 'height': 390}, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'})
        for _ in range(120):
            if await pg.evaluate(f"()=>{K}.mapdReady()"): break
            await pg.wait_for_timeout(500)
        for _ in range(120):
            if (await pg.evaluate(f"()=>{K}.owSlots()"))['n']: break
            await pg.wait_for_timeout(500)
        await pg.wait_for_timeout(1500)
        n0 = await pg.evaluate(f"()=>{K}.progN()")
        await pg.evaluate(f"()=>{{{K}.TASK.test.noBrief=true;{K}.taskStart('overwatch',{{seed:7}})}}")
        await until(pg, SHOW, 30); await pg.evaluate(f"()=>{K}.taskAnswer('WILCO')")
        await pg.evaluate(f"()=>{K}.auto()"); await until(pg, f"()=>{K}.state().agl>120", 90)
        await pg.evaluate(f"()=>{K}.auto()")
        # skip the transit: 2.6 km off the compound at 3,000 ft, the orbit picks it up
        await pg.evaluate(f"()=>{{const K={K},s=K.state(),d=K.TASK.d;s.pos.x=d.c.x-2600;s.pos.z=d.c.z;s.pos.y=Math.max(s.pos.y,(3000-1071)/3.2808+5);}}")
        await adv(pg, 3)
        await finger(pg, '#bSensor'); await adv(pg, 0.3)
        await pg.evaluate(f"()=>{{const K={K};K.SENSOR.slewTo=K.TASK.d.bld;}}"); await adv(pg, 2)
        await pg.evaluate(f"()=>{K}.sensorLock()")
        n1 = await pg.evaluate(f"()=>{K}.progN()")
        for _ in range(60):
            await adv(pg, 0.4)
            await pg.evaluate("()=>window.__kgeu.stepFrame(0.1,false,false)")
        n2 = await pg.evaluate(f"()=>{K}.progN()")
        vis = await pg.evaluate(f"()=>{{const K={K},S=K.SENSOR,d=K.TASK.d;return {{lock:S.tgt&&S.tgt.name,spot:Math.round(Math.hypot(S.spot.x-d.c.x,S.spot.z-d.c.z)),cam:K.camMode?K.camMode():null}}}}")
        await pg.screenshot(path='/tmp/tasking_site_ball.png')
        print('  progN before taskStart', n0, ' entering the ball view', n1, ' after 30 s in it', n2, vis)
        ok('no shader program linked in flight: the count before taskStart and after 30 s in the ball view with the track in it', n2['max'] <= n0['max'] and n2['compiles'] <= n0['compiles'], (n0, n1, n2))
        ok('no console errors (flight)', not pg.errs, pg.errs[:3])
        await b.close()
    return ok.done('tasking_site_check')

if __name__ == '__main__':
    raise SystemExit(asyncio.run(main()))
