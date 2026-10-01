# Item 4.1a: AI air traffic (TFC). iPhone landscape, Hard, a Cessna at KGEU.
# Population 6..10 in free flight, every type over 10 simulated minutes, nothing spawned within
# 1 km, an airliner flown from a 10 nm final at Sky Harbor through to its next takeoff, a Cessna
# left circuit with a touch and go at Glendale, the Luke overhead to a landing, a helicopter over
# the city, a go around with the player sitting on runway 1, lights at night, hidden in a mission,
# the cost per frame, and no console errors.
# Usage: .venv/bin/python tests/traffic_check.py
import asyncio, sys, json
from playwright.async_api import async_playwright
from harness import serve, launch, page, IPHONE_15, Checks

# fly forced aircraft id with TFC.update(0.1) until stop state (or n steps); the state sequence,
# the heading in each state, the first touchdown and the lowest height above the ground
TRACK = """([id,n,stop])=>{const K=window.__kgeu,seq=[],hd={};let td=null,was=null,minAgl=1e9,last=null;
  for(let i=0;i<n;i++){K.TFC.update(0.1);const o=K.tfcList().find(q=>q.id===id);if(!o)break;last=o;
    if(!seq.length||seq[seq.length-1]!==o.state)seq.push(o.state);
    (hd[o.state]=hd[o.state]||[]).push(o.hdg);
    if(!o.onGround)minAgl=Math.min(minAgl,o.agl);
    if(was===false&&o.onGround&&!td)td={state:o.state,tdA:o.tdA,end:o.end,x:o.x,z:o.z};
    was=o.onGround;if(stop&&o.state===stop)break;}
  const mid={};for(const k in hd){const a=hd[k];mid[k]=a[Math.floor(a.length/2)];}
  return {seq:seq,mid:mid,td:td,minAgl:minAgl,last:last};}"""
FRESH = "()=>{const K=window.__kgeu;K.TFC.auto=false;K.tfcClear();}"
START = "([t,b,m])=>{const K=window.__kgeu;K.TFC.auto=true;K.pick(t);K.pickBase(b);K.start(m);}"


def in_order(seq, want):
    i = 0
    for s in seq:
        if i < len(want) and s == want[i]:
            i += 1
    return i == len(want)


def adiff(a, b):
    return abs((a - b + 540) % 360 - 180)


async def main():
    c = Checks()
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'})
        c('hooks: TFC, tfcList, tfcSpawn, tfcClear', await pg.evaluate(
            "()=>{const K=window.__kgeu;return !!K.TFC&&typeof K.tfcList==='function'&&typeof K.tfcSpawn==='function'&&typeof K.tfcClear==='function'}"))
        await pg.evaluate(START, ['cessna', 'kgeu', 'ramp'])
        await pg.wait_for_timeout(300)
        # --- population after 60 s of flight frames ---
        n = await pg.evaluate("()=>{const K=window.__kgeu;for(let i=0;i<600;i++)K.stepFrame(0.1,false,true);return K.tfcList().length}")
        c('6 to 10 aircraft alive after 60 s', 6 <= n <= 10, n)
        L = await pg.evaluate("()=>window.__kgeu.tfcList()")
        c('generic call names on every aircraft', all(o['callName'] in ('Cessna', 'airliner', 'F-16', 'helicopter') for o in L), [o['callName'] for o in L])
        # --- 10 simulated minutes: every type, the count stays in range, the cost ---
        r = await pg.evaluate("""()=>{const K=window.__kgeu,seen={},cnt=[1e9,0];let ms=0,heliMin=1e9;
          for(let i=0;i<6000;i++){const t=performance.now();K.TFC.update(0.1);ms+=performance.now()-t;
            const L=K.tfcList();cnt[0]=Math.min(cnt[0],L.length);cnt[1]=Math.max(cnt[1],L.length);
            for(const o of L){seen[o.type]=1;if(o.type==='heli')heliMin=Math.min(heliMin,o.agl);}}
          return {seen:Object.keys(seen).sort(),cnt:cnt,ms:ms/6000,heliMin:heliMin,spawns:K.TFC.spawns}}""")
        c('every type present over 10 simulated minutes', r['seen'] == ['airliner', 'cessna', 'f16', 'heli'], r['seen'])
        c('alive count stays within 6 to 10', r['cnt'][0] >= 6 and r['cnt'][1] <= 10, r['cnt'])
        c('TFC.update under 0.3 ms a frame on average', r['ms'] < 0.3, round(r['ms'], 4))
        c('helicopters stay well above the ground', r['heliMin'] > 100, round(r['heliMin']))
        sp = [s for s in r['spawns'] if not s['forced']]
        c('nothing spawns within 1 km of the player (ramp)', sp and min(s['d'] for s in sp) >= 1000, min(s['d'] for s in sp) if sp else None)
        # --- airliner: 10 nm final to Sky Harbor 8, through the turn round, to its next takeoff ---
        await pg.evaluate(FRESH)
        aid = await pg.evaluate("()=>window.__kgeu.tfcSpawn('airliner',{state:'final',end:0,dist:18520,wait:20})")
        t = await pg.evaluate(TRACK, [aid, 30000, 'climb'])
        want = ['final', 'rollout', 'taxi_in', 'parked', 'taxi_out', 'hold', 'lineup', 'takeoff', 'climb']
        c('airliner: final, rollout, taxi in, parked, taxi out, hold, lineup, takeoff, climb', in_order(t['seq'], want), t['seq'])
        td = t['td'] or {}
        c('airliner: touches down at KPHX 08 near the threshold', td.get('end') == 'KPHX 08' and td.get('tdA') is not None and 0 <= td['tdA'] <= 1200, td)
        c('airliner: never below the ground in the air', t['minAgl'] > -0.5, t['minAgl'])
        # --- Cessna: a left circuit at Glendale, all four legs, a touch and go on KGEU ---
        await pg.evaluate(FRESH)
        cid = await pg.evaluate("()=>window.__kgeu.tfcSpawn('cessna',{state:'upwind',end:0})")
        t = await pg.evaluate(TRACK, [cid, 6000, 'touchgo'])
        c('cessna: upwind, crosswind, downwind, base, final, touch and go',
          in_order(t['seq'], ['upwind', 'crosswind', 'downwind', 'base', 'final', 'touchgo']), t['seq'])
        rh = 26
        m = t['mid']
        legs = {'crosswind': rh - 90, 'downwind': rh + 180, 'base': rh + 90, 'final': rh}
        c('cessna: headings through all four legs of left traffic',
          all(k in m and adiff(m[k], v) < 30 for k, v in legs.items()), {k: round(m.get(k, -1)) for k in legs})
        td = t['td'] or {}
        c('cessna: touches down on KGEU runway 1', td.get('end') == 'KGEU 1' and td.get('tdA') is not None and 0 <= td['tdA'] <= 1500, td)
        # --- F-16: the overhead at Luke, a two ship, landing and taxiing in ---
        await pg.evaluate(FRESH)
        fid = await pg.evaluate("()=>window.__kgeu.tfcSpawn('f16',{state:'initial',end:0})")
        nf = await pg.evaluate("()=>window.__kgeu.tfcList().filter(o=>o.type==='f16').length")
        c('f16: a two ship', nf == 2, nf)
        t = await pg.evaluate(TRACK, [fid, 6000, 'taxi_in'])
        c('f16: initial, break, downwind, base, final, rollout, taxi in',
          in_order(t['seq'], ['initial', 'break', 'downwind', 'base', 'final', 'rollout', 'taxi_in']), t['seq'])
        td = t['td'] or {}
        c('f16: touches down at Luke 03L', td.get('end') == 'KLUF 03L' and td.get('tdA') is not None and 0 <= td['tdA'] <= 1500, td)
        w = await pg.evaluate("()=>window.__kgeu.tfcList().filter(o=>o.type==='f16').map(o=>[o.state,o.ga])")
        c('f16: the wingman lands too, no go around', all(s in ('rollout', 'taxi_in') and g == 0 for s, g in w), w)
        # --- helicopter over the city ---
        await pg.evaluate(FRESH)
        hid = await pg.evaluate("()=>window.__kgeu.tfcSpawn('heli',{})")
        t = await pg.evaluate(TRACK, [hid, 3000, None])
        c('heli: stays above the ground over the city', t['minAgl'] > 100 and t['last'] and not t['last']['onGround'] and t['last']['x'] > 2000,
          (round(t['minAgl']), t['last'] and round(t['last']['x'])))
        c('heli: cruises and hovers', in_order(t['seq'], ['cruise']) and set(t['seq']) <= {'cruise', 'hover'}, t['seq'])
        # --- go around: the player on runway 1 at Glendale, a Cessna on a 2.5 km final ---
        await pg.evaluate(START, ['cessna', 'kgeu', 'runway'])
        await pg.evaluate("()=>{const K=window.__kgeu;for(let i=0;i<20;i++)K.stepFrame(0.1,false,true);}")
        sp = await pg.evaluate("()=>window.__kgeu.TFC.spawns.filter(s=>!s.forced).map(s=>s.d)")
        c('nothing spawns within 1 km of the player (runway 1)', sp and min(sp) >= 1000, min(sp) if sp else None)
        await pg.evaluate(FRESH)
        gid = await pg.evaluate("()=>window.__kgeu.tfcSpawn('cessna',{state:'final',end:0,dist:2500})")
        t = await pg.evaluate(TRACK, [gid, 1200, None])
        c('go around with the player on runway 1, no touchdown', 'goaround' in t['seq'] and t['td'] is None and t['last']['ga'] >= 1,
          (t['seq'], t['td']))
        # --- lights at night ---
        await pg.evaluate("()=>{const K=window.__kgeu;K.setTOD('night');K.TFC.auto=false;K.tfcClear();}")
        lid = await pg.evaluate("()=>window.__kgeu.tfcSpawn('airliner',{state:'final',end:0,dist:9000})")
        await pg.evaluate("()=>window.__kgeu.stepFrame(0.1,false,true)")
        lt = await pg.evaluate(f"()=>{{const K=window.__kgeu,o=K.tfcList().find(q=>q.id==={lid});return [o&&o.lights,K.acLights().traffic,K.lights().uLights]}}")
        c('airliner lights at night (nav, strobes, beacons)', lt[0] and lt[0] >= 7 and lt[0] in lt[1] and lt[2] == 1, lt)
        hl = await pg.evaluate("()=>{const K=window.__kgeu,id=K.tfcSpawn('heli',{});const o=K.tfcList().find(q=>q.id===id);return o&&o.lights}")
        c('helicopter lights at night', hl and hl >= 5, hl)
        await pg.evaluate("()=>window.__kgeu.setTOD('day')")
        # --- hidden in a mission, back after ---
        await pg.evaluate(START, ['cessna', 'kgeu', 'ramp'])
        n1 = await pg.evaluate("()=>{const K=window.__kgeu;for(let i=0;i<20;i++)K.stepFrame(0.1,false,true);return K.tfcList().filter(o=>o.visible).length}")
        c('free flight: traffic visible', n1 >= 6, n1)
        await pg.evaluate(START, ['c130', 'kgeu', 'drop'])
        hid_ = await pg.evaluate("""()=>{const K=window.__kgeu,R=K.R3();for(let i=0;i<20;i++)K.stepFrame(0.1,false,true);
          let v=0;R.scene.traverse(o=>{if(/^tfc_/.test(o.name)&&o.visible)v++;});return {miss:K.MISS.on,live:K.tfcList().length,shown:v}}""")
        c('mission: no AI traffic shown', hid_['miss'] and hid_['shown'] == 0 and hid_['live'] == 0, hid_)
        await pg.evaluate(START, ['cessna', 'kgeu', 'ramp'])
        n2 = await pg.evaluate("()=>{const K=window.__kgeu;for(let i=0;i<20;i++)K.stepFrame(0.1,false,true);return K.tfcList().filter(o=>o.visible).length}")
        c('after the mission: traffic back', n2 >= 6, n2)
        await pg.evaluate("()=>window.__kgeu.stepFrame(0,true)")
        c('no console errors', not pg.errs, pg.errs[:5])
        await pg.context.close()
        await b.close()
    srv.shutdown()
    return c.done('traffic_check')


sys.exit(asyncio.run(main()))
