# Overwatch2 item 4a: the OVERWATCH vehicles. (A) 30 seeds rolled (TASK.test.noBrief): three types or more and five
# colours or more as targets, decoys never the target's colour (the first of two always its type), speech friendly
# names, the briefing and the lock targets (building, target, decoys), three objects, the triangle budgets (1,400 to
# 2,400 and 250 to 400), every parked vehicle's wheels on the ground. (B) one seed flown: Mission Control's opening call
# names it; a decoy locked: its toast and owOn(target) false; the departure at d.dep (wheels moving within 0.7 s) with
# progN flat through DTV and IR WHT; REPORT names the colour and type; 60 s of driving sampled every 0.5 s (the four
# wheels within 0.25 m of the ground); dust behind it while it moves, more at full speed; the talk-on on the track;
# the steepest or tightest stretch slows it; the track's end: onto the road, along its polyline (within 6 m for 20 s)
# at road speed, the talk-on says on the road. (C) a seed where a decoy leaves first: REPORT gets Mission Control's
# Negative naming both and counts a false report, the decoy drives on. No page errors.
# Run: timeout 540 .venv/bin/python -u tests/overwatch_vehicle_check.py
import asyncio, re
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
INFO = f"()=>{K}.owVeh()"
LOG = f"()=>{K}.task().log.map(l=>(l.who||'')+': '+l.text)"
NAME = re.compile(r'^the (white|red|silver|black|tan|blue) (pickup|compact pickup|SUV|sedan)$')
ROLL = """(sd)=>{const K=window.__kgeu;K.taskStop();K.TASK.test.noBrief=true;K.taskStart('overwatch',{seed:sd});const d=K.TASK.d,I=K.owVeh();
  let rl=0;for(let i=1;i<d.roadLine.length;i++)rl+=Math.hypot(d.roadLine[i].x-d.roadLine[i-1].x,d.roadLine[i].z-d.roadLine[i-1].z);
  return {sd:sd,target:d.target,decoys:d.decoys,dcy:!!d.dcy,tg:K.TASK.tgts.map(t=>t.name),objs:K.TASK.objs.length,sit:K.TASKS.overwatch.brief(d).sit,
    tris:I.list.map(v=>v.tris),wheels:I.list.map(v=>v.wheels),rl:Math.round(rl),ms:d.ms}}"""

async def fly(pg, seed, st):
    await pg.evaluate(f"()=>{{{K}.TASK.test.noBrief=true;{K}.taskStart('overwatch',{{seed:{seed}}})}}")
    await until(pg, SHOW, 30)
    log = await pg.evaluate(LOG)
    await pg.evaluate(f"()=>{K}.taskAnswer('WILCO')")
    await pg.evaluate(f"()=>{K}.auto()"); await until(pg, f"()=>{K}.state().agl>120", 120)
    await pg.evaluate(f"()=>{K}.auto()")
    await pg.evaluate(f"()=>{{const K={K},s=K.state(),d=K.TASK.d;const a=Math.atan2(s.pos.x-d.c.x,s.pos.z-d.c.z);s.pos.x=d.c.x+Math.sin(a)*2200;s.pos.z=d.c.z+Math.cos(a)*2200;s.pos.y=(3000-1071)/3.28084;}}")
    await adv(pg, 8)
    await finger(pg, '#bSensor'); await adv(pg, 0.3)
    return log

async def main():
    srv, url = serve()
    st = {'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'}
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp={'width': 844, 'height': 390}, storage=st)
        for _ in range(120):
            if (await pg.evaluate(f"()=>{K}.owSlots()"))['n']: break
            await pg.wait_for_timeout(500)
        # ---- A: 30 rolls ----
        R = [await pg.evaluate(ROLL, sd) for sd in range(1, 31)]
        await pg.evaluate(f"()=>{K}.taskStop()")
        types = {r['target']['type'] for r in R}; cols = {r['target']['col'] for r in R}
        print('  targets:', ', '.join(f"{r['sd']}:{r['target']['name'][4:]}{'*' if r['dcy'] else ''}" for r in R))
        print('  types', sorted(types), 'colours', sorted(cols), ' decoy-first seeds', [r['sd'] for r in R if r['dcy']], ' road km', [round(r['rl'] / 1000, 1) for r in R])
        ok('30 seeds: three types or more and five colours or more as the target', len(types) >= 3 and len(cols) >= 5, (types, cols))
        ok('decoys: one or two, never the target\'s colour nor each other\'s; with two the first is the target\'s type; two when one leaves first',
           all(1 <= len(r['decoys']) <= 2 and all(q['col'] != r['target']['col'] for q in r['decoys']) and len({q['col'] for q in r['decoys']}) == len(r['decoys'])
               and (len(r['decoys']) < 2 or r['decoys'][0]['type'] == r['target']['type']) and (not r['dcy'] or len(r['decoys']) == 2) for r in R), [r['decoys'] for r in R][:4])
        ok('names are speech friendly ("the red pickup", "the tan compact pickup", "the blue SUV")', all(NAME.match(n) for r in R for n in [r['target']['name']] + [q['name'] for q in r['decoys']]), [r['target']['name'] for r in R][:6])
        ok('lock targets: the white building, the target, then the decoys; three objects', all(r['tg'] == ['the white building', r['target']['name']] + [q['name'] for q in r['decoys']] and r['objs'] == 3 for r in R), [r['tg'] for r in R][:3])
        ok('the briefing names it ("A vehicle is expected to leave, a red pickup")', all(('A vehicle is expected to leave, ' + r['target']['name'].replace('the ', 'a ', 1) + ':') in r['sit'] for r in R), R[0]['sit'])
        tr = [t for r in R for t in r['tris']]
        print('  triangles full', sorted({t[0] for t in tr}), 'light', sorted({t[1] for t in tr}), ' roll ms worst', max(r['ms']['roll'] for r in R), 'fleet ms worst', max(r['ms']['fleet'] for r in R))
        ok('triangles: 1,400 to 2,400 at full detail, 250 to 400 at the light level', all(1400 <= t[0] <= 2400 and 250 <= t[1] <= 400 for t in tr), sorted({tuple(t) for t in tr}))
        wh = [w for r in R for v in r['wheels'] for w in v]
        ok('parked: every wheel on what it stands on (within 0.05 m) and within 0.25 m of the ground', all(abs(w[0]) <= 0.05 and abs(w[1]) <= 0.25 for w in wh), max(abs(w[1]) for w in wh))
        sB = next(r['sd'] for r in R if not r['dcy'] and r['rl'] >= 3000)
        sC = next(r['sd'] for r in R if r['dcy'])
        await pg.close()
        # ---- B: one seed flown ----
        pg = await page(b, url, vp={'width': 844, 'height': 390}, storage=st)
        for _ in range(120):
            if (await pg.evaluate(f"()=>{K}.owSlots()"))['n']: break
            await pg.wait_for_timeout(500)
        n0 = await pg.evaluate(f"()=>{K}.progN()")
        log = await fly(pg, sB, st)
        d0 = await pg.evaluate(f"()=>{{const d={K}.TASK.d;return {{t:d.target,dec:d.decoys}}}}")
        tname = d0['t']['name']; dname = d0['dec'][0]['name']
        print(f'  seed {sB}: {tname}, decoys {[q["name"] for q in d0["dec"]]}')
        ok('Mission Control\'s opening call names it ("The vehicle of interest is a red pickup.")', any('The vehicle of interest is ' + tname.replace('the ', 'a ', 1) + '.' in l for l in log), log[-2:])
        # a decoy locked: the slew to it, LOCK
        await pg.evaluate(f"()=>{{const K={K};K.SENSOR.slewTo=K.TASK.d.fleet.list[1];}}"); await adv(pg, 2)
        await pg.evaluate(f"()=>{{const K={K},S=K.SENSOR;S.tgt=null;S.track=null;S.geo=null;}}")
        await pg.evaluate(f"()=>{K}.sensorLock()"); await adv(pg, 0.2)
        lk = await pg.evaluate(f"()=>{{const K={K},S=K.SENSOR,d=K.TASK.d;return {{tgt:S.tgt&&S.tgt.name,toast:document.getElementById('toast').textContent,on:K.owOn(d.veh,70),onE:K.owOn(d.veh,110),shmid:document.body.innerText.includes('LOCK '+(S.tgt?S.tgt.name.toUpperCase():'?'))}}}}")
        ok('LOCK on a decoy: "Tracking the blue SUV: not the target", owOn(target) false (time on target and the talk-on do not count)',
           lk['tgt'] == dname and lk['toast'] == f'Tracking {dname}: not the target' and not lk['on'] and not lk['onE'], lk)
        await pg.evaluate(f"()=>{{const K={K},S=K.SENSOR;S.tgt=K.TASK.d.veh;}}"); await adv(pg, 0.3)
        ok('LOCK on the target: owOn(target) true', await pg.evaluate(f"()=>{K}.owOn({K}.TASK.d.veh,70)"))
        # the departure, DTV then IR WHT across it
        await pg.evaluate(f"()=>{K}.tqStage(2)"); await adv(pg, 0.5)
        await pg.evaluate(f"()=>{{const K={K},d=K.TASK.d;d.dep=K.state().time-d.w0+4;d.follow=1e6;if(d.ppl)d.ppl.tDep=null;}}")   # the follow stage held: the drive is the subject
        w0, dep = await pg.evaluate(f"()=>[{K}.TASK.d.w0,{K}.TASK.d.dep]")
        await until(pg, f"()=>{K}.TASK.d.veh.moving", 30, 0.1)
        dt = await pg.evaluate(f"()=>{K}.TASK.d.depT") - w0
        ok('the target leaves at d.dep (within 0.7 s)', abs(dt - dep) < 0.7, (dt, dep))
        await adv(pg, 0.7)
        s07 = await pg.evaluate(f"()=>{K}.owVeh().list[0].s")
        ok('its wheels move within 0.7 s', s07 > 0.05, s07)
        # item 5: a pooled smoke puff (puff(), the sprite points) in view too, then IR WHT: nothing links
        await pg.evaluate(f"()=>{{const K={K},v=K.TASK.d.veh;for(let i=0;i<6;i++)K.puff(v.x+i*3,v.y+2,v.z);}}"); await adv(pg, 0.2)
        await pg.evaluate(f"()=>{K}.setSensorMode('irw')"); await adv(pg, 1); await pg.evaluate("()=>window.__kgeu.stepFrame(1/30,false,false)")
        nIR = await pg.evaluate(f"()=>{K}.progN()")
        await pg.evaluate(f"()=>{K}.setSensorMode('tv')"); await adv(pg, 0.3)
        await pg.evaluate(f"()=>{K}.taskAnswer('REPORT')"); await adv(pg, 0.5)
        log = await pg.evaluate(LOG)
        short = tname[4:]
        ok('REPORT: the departure call names the colour and type ("vehicle departing the compound, red pickup, heading")', any(f'vehicle departing the compound, {short}, heading' in l for l in log), log[-3:])
        await until(pg, SHOW, 20); await pg.evaluate(f"()=>{K}.taskAnswer('WILCO')")
        ok('the pill follows it by name ("Follow the red pickup") and DEST shows its type', await pg.evaluate(f"()=>{K}.TASKS.overwatch.stages[3].obj({K}.TASK.d)[0]") == 'Follow ' + tname, await pg.evaluate(f"()=>{K}.dest&&{K}.dest()"))
        # 60 s of driving
        bad = []; spd = []; dl = []; lv = []
        for k in range(120):
            await adv(pg, 0.5)
            v = (await pg.evaluate(INFO))['list'][0]
            bad += [w for w in v['wheels'] if abs(w[1]) > 0.25 or abs(w[0]) > 0.25]
            spd.append(v['spd']); dl.append(v['dust']); lv.append((v['dustLive'], v['dustBehind']))
        vk = await pg.evaluate(f"()=>{K}.TASK.d.vk")
        print(f'  60 s: speeds {spd[0]:.1f} .. {max(spd):.1f} m/s (cruise {vk:.1f}), dust puffs {dl[-1]}, live near it {max(x[0] for x in lv)}, fleet ms {(await pg.evaluate(INFO))["msMax"]}')
        ok('60 s of driving: the four wheels within 0.25 m of the ground the whole time', not bad, bad[:4])
        slow = [dl[i + 2] - dl[i] for i in range(len(spd) - 2) if 2.5 < spd[i] < vk * 0.6]; fast = [dl[i + 2] - dl[i] for i in range(len(spd) - 2) if spd[i] > vk * 0.9]
        ok('dust behind it while it moves (all live puffs near it behind it), more at full speed than slow', all(x[1] >= x[0] - 1 for x in lv) and max(x[0] for x in lv) >= 4
           and fast and slow and sum(fast) / len(fast) > sum(slow) / len(slow), (slow[:4], fast[:4], lv[-3:]))
        t1 = await pg.evaluate(f"()=>{{const K={K};K.SENSOR.tgt=K.TASK.d.veh;K.owTalk();return K.task().log.slice(-2).map(l=>l.text)}}")
        ok('the talk-on names it, on the dirt track', any(f'your vehicle is {tname},' in l and 'on the dirt track' in l for l in t1) and any(f'Contact {tname}.' in l for l in t1), t1)
        # the steepest or tightest stretch: the vehicle put 60 m before it at cruise
        q = await pg.evaluate(f"""()=>{{const K={K},d=K.TASK.d,v=d.fleet.list[0],P=v.path;let bi=-1,bs=0;
          for(let i=0;i<P.n-12&&!P.rd[i];i++){{const g=Math.abs(K.owGnd(P.x[i+10],P.z[i+10])-K.owGnd(P.x[i],P.z[i]))/Math.max(1,P.s[i+10]-P.s[i]),sc=Math.max(g/0.05,Math.abs(P.k[i])*25);if(sc>bs&&P.s[i]>v.s+80){{bs=sc;bi=i;}}}}
          if(bi<0)return null;v.s=P.s[bi]-60;v.pi=0;v.spd=v.vk;v.slowF=1;return {{s:P.s[bi],score:+bs.toFixed(2),k:+P.k[bi].toFixed(4)}}}}""")
        sp2 = []
        for k in range(16):
            await adv(pg, 0.5)
            v = (await pg.evaluate(INFO))['list'][0]; sp2.append((v['spd'], v['rough']))
        print(f'  the roughest stretch {q}: speeds {[s for s, _ in sp2]}')
        ok('it slows on the steepest or tightest stretch (to 55 to 70 percent of its cruise, eased)', q and q['score'] > 1 and any(r for _, r in sp2) and min(s for s, _ in sp2) <= vk * 0.75, (q, sp2))
        # the end of the track: onto the road
        await pg.evaluate(f"()=>{{const K={K},v=K.TASK.d.fleet.list[0],P=v.path;let i=0;while(i<P.n&&!P.rd[i])i++;v.s=Math.max(0,P.s[i]-40);v.pi=0;v.spd=v.vk*0.8;}}")
        await until(pg, f"()=>{K}.owVeh().list[0].onRoad", 20, 0.5)
        rd = []
        for k in range(40):
            await adv(pg, 0.5)
            rd.append(await pg.evaluate(f"""()=>{{const K={K},d=K.TASK.d,v=d.fleet.list[0],L=d.roadLine;let m=1e9;for(let i=0;i+1<L.length;i++){{const ax=L[i].x,az=L[i].z,ex=L[i+1].x-ax,ez=L[i+1].z-az,l=ex*ex+ez*ez,t=l?Math.max(0,Math.min(1,((v.x-ax)*ex+(v.z-az)*ez)/l)):0;m=Math.min(m,Math.hypot(v.x-ax-ex*t,v.z-az-ez*t));}}return [+m.toFixed(2),+v.spd.toFixed(1),v.onRoad,v.moving]}}"""))
        print(f'  on the road: off the polyline {max(r[0] for r in rd)} m worst, speeds {rd[0][1]} .. {max(r[1] for r in rd)}')
        vr = await pg.evaluate(f"()=>{K}.TASK.d.vRoad")
        ok('the track\'s end: it turns onto the road and follows its polyline (within 6 m for 20 s) toward road speed (20 to 24 m/s)',
           all(r[2] for r in rd) and max(r[0] for r in rd) <= 6 and max(r[1] for r in rd) > vk and 20 <= vr <= 24, rd[-3:])
        t2 = await pg.evaluate(f"()=>{{const K={K};K.SENSOR.tgt=K.TASK.d.veh;K.owTalk();return K.task().log.slice(-2).map(l=>l.text)}}")
        ok('the talk-on on the road says so', any('on the road' in l for l in t2), t2)
        n2 = await pg.evaluate(f"()=>{K}.progN()")
        ok('progN flat from before taskStart through DTV and IR WHT at the departure (its dust and pooled smoke puffs in view) and the drive', nIR['max'] <= n0['max'] and n2['max'] <= n0['max'] and n2['compiles'] <= n0['compiles'], (n0, nIR, n2))
        ok('no console errors (B)', not pg.errs, pg.errs[:3])
        await pg.close()
        # ---- C: a decoy leaves first ----
        pg = await page(b, url, vp={'width': 844, 'height': 390}, storage=st)
        for _ in range(120):
            if (await pg.evaluate(f"()=>{K}.owSlots()"))['n']: break
            await pg.wait_for_timeout(500)
        await fly(pg, sC, st)
        await pg.evaluate(f"()=>{K}.tqStage(2)"); await adv(pg, 0.5)
        c = await pg.evaluate(f"()=>{{const K={K},d=K.TASK.d;d.dcy.t=K.state().time-d.w0+2;d.dep=d.dcy.t+60;return {{dcy:d.dcy.mode,t:d.target.name,dn:d.fleet.list[1].name}}}}")
        await until(pg, f"()=>{K}.TASK.d.fleet.list[1].moving", 20, 0.1)
        await adv(pg, 6)
        r0 = await pg.evaluate(f"()=>{{const d={K}.TASK.d,v=d.fleet.list[1];return Math.hypot(v.x-d.c.x,v.z-d.c.z)}}")
        await pg.evaluate(f"()=>{K}.taskAnswer('REPORT')"); await adv(pg, 0.5)
        log = await pg.evaluate(LOG); fr = await pg.evaluate(f"()=>[{K}.TASK.d.falseRep,{K}.TASK.d.dcyRep,{K}.TASK.d.veh.moving]")
        want = f"Negative, that is {c['dn']}. Our vehicle is {c['t']}, still parked. Keep watching."
        print(f'  seed {sC}: {c["dn"]} leaves first ({c["dcy"]}); {c["t"]} stays')
        ok('a decoy leaving first: REPORT gets "Negative, that is the blue SUV. Our vehicle is the red pickup, still parked. Keep watching." and counts a false report',
           any(want in l for l in log) and fr[0] == 1 and fr[1] == 1 and not fr[2], (log[-2:], fr))
        await adv(pg, 20)
        r1 = await pg.evaluate(f"()=>{{const d={K}.TASK.d,v=d.fleet.list[1];return [Math.hypot(v.x-d.c.x,v.z-d.c.z),v.moving,v.spd]}}")
        ok('the decoy keeps driving away', r1[0] > r0 + 60, (r0, r1))
        ok('no console errors (C)', not pg.errs, pg.errs[:3])
        await b.close()
    return ok.done('overwatch_vehicle_check')

if __name__ == '__main__':
    raise SystemExit(asyncio.run(main()))
