# Planes2 items 3 to 5: what every Pocket Air airliner shares. Sky Harbor is a base (runway 7L, its own tower and
# ground); an airliner only spawns where the runway is long enough (TYPES.minRwy: Glendale and Rio are greyed out
# and refused, picking an airliner at Glendale moves it to Sky Harbor, a start at a short base goes to its home);
# Easy's autothrottle holds the phase speed and lets go on a throttle input; the flight director canvas is up in
# Easy in the air and never in Hard; the fan engine sound is wired; the carousel and pause chips carry it.
# Usage: .venv/bin/python tests/liner_check.py [type ...]  (default: every type with minRwy)
import asyncio, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, IPHONE_15
ok = Checks()
K = 'window.__kgeu'

async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'rookie', 'kgeuTut': '1', 'kgeuCoach': '3'})
        async def step(n, dt=1/30):
            await pg.evaluate("([n,dt])=>{for(let i=0;i<n;i++)window.__kgeu.stepFrame(dt,false,true);window.__kgeu.stepFrame(1/60);}", [n, dt])
        types = sys.argv[1:] or await pg.evaluate(f"()=>Object.keys({K}.TYPES).filter(k=>{K}.TYPES[k].minRwy)")
        print('  airliners:', types)
        ok('Sky Harbor is a base with its own tower, ground and runway 7L', await pg.evaluate(f"()=>{{const B={K}.BASES.phx;return !!B&&B.rwy==='7L'&&/Phoenix Tower/.test(B.twr)&&/Phoenix Ground/.test(B.gnd);}}"))
        ok('the runway rule reads 11,489 ft at Sky Harbor, 7,150 at Glendale, 4,340 at Rio, 8,860 at CDG 26L', await pg.evaluate(f"()=>{{const L={K}.rwyLenOf;return L('phx')>3400&&L('kgeu')<2300&&L('sbrj')<1400&&L('rjtt')>3300&&L('lfpg')>2600;}}"))
        for t in types:
            print('--', t)
            r = await pg.evaluate(f"""()=>{{const K={K};K.pick('cessna');K.pickBase('kgeu');K.pick('{t}');
              const chips=[...document.querySelectorAll('#locFly .pick[data-b]')].map(c=>[c.dataset.b,c.classList.contains('off')]);
              return {{sum:document.getElementById('sumLine').textContent,chips:chips,ok:{{kgeu:K.baseOK('{t}','kgeu'),luke:K.baseOK('{t}','luke'),phx:K.baseOK('{t}','phx'),rjtt:K.baseOK('{t}','rjtt'),lfpg:K.baseOK('{t}','lfpg'),sbrj:K.baseOK('{t}','sbrj')}}}};}}""")
            ok(f'{t}: Sky Harbor, Luke, Haneda and CDG allowed, Glendale and Rio not', r['ok'] == {'kgeu': False, 'luke': True, 'phx': True, 'rjtt': True, 'lfpg': True, 'sbrj': False}, str(r['ok']))
            ok(f'{t}: picking it at Glendale moves the start to Sky Harbor', 'Sky Harbor' in r['sum'], r['sum'])
            ok(f'{t}: the Glendale and Rio chips are greyed out, Luke and Sky Harbor not', dict(r['chips']).get('kgeu') and dict(r['chips']).get('sbrj') and not dict(r['chips']).get('luke') and not dict(r['chips']).get('phx'), str(r['chips']))
            # a start at a short base goes home
            await pg.evaluate(f"()=>{{const K={K};K.pick('{t}');K.start('runway','kgeu');}}"); await pg.wait_for_timeout(800)
            s = await pg.evaluate(f"()=>{{const s={K}.state();return {{base:s.base,type:s.type,gear:+(s.pos.y-{K}.groundHeight(s.pos.x,s.pos.z)).toFixed(2),cs:{K}.TYPES[s.type].cs}};}}")
            ok(f'{t}: a Glendale start lands on Sky Harbor runway 7L', s['base'] == 'phx' and s['type'] == t, str(s))
            # Easy: the autothrottle holds Vy in the climb, then lets go on a throttle input
            await pg.evaluate(f"()=>{{const K={K};K.auto();}}")
            for _ in range(120):
                await step(30)
                a = await pg.evaluate(f"()=>{{const s={K}.state();return {{agl:s.agl,ap:!!s.ap}};}}")
                if a['agl'] > 150: break
            await pg.evaluate(f"()=>{{const s={K}.state();s.ap=null;s.apW=null;}}")   # the auto takeoff lets go: Easy flies, A/THR with it
            await step(120)
            a = await pg.evaluate(f"()=>{{const s={K}.state(),T={K}.TYPES[s.type];return {{agl:Math.round(s.agl),cfg:s.ezCfg||null,m:s.ezATm,kt:Math.round(s.ias*1.94384),vy:Math.round(T.vy*1.94384),thr:+s.throttle.toFixed(2),fd:document.body.classList.contains('fdOn'),fdDisp:getComputedStyle(document.getElementById('fd')).display}};}}")
            print('  climb:', a)
            ok(f'{t}: A/THR engaged in the climb and holding near Vy', a['m'] == 0 and abs(a['kt'] - a['vy']) < 25, str(a))
            ok(f'{t}: the flight director is up in Easy in the air', a['fd'] and a['fdDisp'] != 'none', str(a))
            await pg.evaluate(f"()=>{{const K={K};K.setThr(0.4);}}"); await step(5)
            m = await pg.evaluate(f"()=>({{m:{K}.state().ezATm,side:document.getElementById('sideToast').textContent}})")
            ok(f'{t}: a throttle input hands the throttle to the pilot (A/THR OFF)', m['m'] == 1 and 'A/THR' in m['side'], str(m))
            # Hard: no director, no autothrottle
            await pg.evaluate(f"()=>{{const K={K};K.setSkill('pilot');K.pick('{t}');K.start('final');}}"); await pg.wait_for_timeout(600); await step(30)
            h = await pg.evaluate(f"()=>({{fd:document.body.classList.contains('fdOn'),m:{K}.state().ezATm,kt:Math.round({K}.state().ias*1.94384),snd:{K}.TYPES['{t}'].snd}})")
            ok(f'{t}: Hard has no flight director and no autothrottle, the fan sound is wired', not h['fd'] and h['m'] is None and h['snd'] == 'fan', str(h))
            await pg.evaluate(f"()=>{K}.setSkill('rookie')")
        ok('no page errors', not pg.errs, pg.errs[:2])
        await b.close()
    sys.exit(ok.done('liner_check'))
asyncio.run(main())
