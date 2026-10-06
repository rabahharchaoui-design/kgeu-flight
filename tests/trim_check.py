# Hands-off trim (item 11): in Hard, every aircraft spawned on the 3 mile and the 1 mile final at
# Glendale and Luke is trimmed for the configuration it actually has (approach flaps, gear, speed),
# so with the stick neutral it follows the 3 degree path instead of ballooning off it (the C-130
# used to climb about 400 ft). 30 s of sim time or down to 60 ft, whichever comes first, in still
# air (WIND_FIX), reporting the worst deviation from the spawn's own path for every aircraft. The
# C-130 must stay within 60 ft. Also: the C-130 airdrop run in (a level spawn) holds its height, and
# the C-130 trimmed level in cruise at a few speeds neither dives nor climbs away.
# Run: .venv/bin/python tests/trim_check.py
import asyncio, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, IPHONE_15
ok = Checks()
K = "window.__kgeu"
TYPES = ['cessna', 'archer', 'alpha', 'reaper', 'mq9b', 'f16', 'a10', 'c130', 'b737', 'a320']
DEV = 60      # ft, the C-130's limit on a final
LEVEL = 50    # ft, a level spawn

# fly T seconds (or down to 60 ft) hands off; the path is the spawn height less the ground
# distance flown times tan(gam). Returns the worst and the final deviation in ft, speeds in kt.
FLY = """([T,gam])=>{const K=window.__kgeu;let s=K.state();const y0=s.pos.y,tg=Math.tan(gam*Math.PI/180);
  let d=0,worst=0,dev=0,t=0,kt0=null;const dt=1/30;
  while(t<T){K.stepFrame(dt,false,true);s=K.state();t+=dt;if(kt0===null)kt0=s.ias*1.943844;
    d+=Math.hypot(s.vel.x,s.vel.z)*dt;dev=(s.pos.y-(y0+d*tg))*3.28084;if(Math.abs(dev)>Math.abs(worst))worst=dev;
    if(s.crashed||s.onGround||s.agl*3.28084<60)break;}
  return {worst:Math.round(worst),end:Math.round(dev),t:+t.toFixed(1),kt0:Math.round(kt0),kt:Math.round(s.ias*1.943844),
    thr:+s.throttle.toFixed(2),trim:+s.trim.toFixed(2),crashed:s.crashed,ap:!!s.ap}}"""

async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1'})
        await pg.evaluate("()=>{window.WIND_FIX=[360,0]}")   # still air: createState reads it
        await pg.evaluate(f"()=>{K}.setSkill('pilot')")
        rows = []
        for t in TYPES:
            for base in ('kgeu', 'luke'):
                for pos in ('final', 'final1'):
                    await pg.evaluate(f"()=>{{{K}.pick('{t}');{K}.pickBase('{base}');{K}.start('{pos}')}}")
                    r = await pg.evaluate(FLY, [30, -3])
                    rows.append((t, base, pos, r))
                    print(f'    {t:7} {base:5} {"3 mi" if pos == "final" else "1 mi"}  worst {r["worst"]:+5} ft  end {r["end"]:+5} ft  '
                          f'{r["t"]:4} s  {r["kt0"]}->{r["kt"]} kt  thr {r["thr"]}  trim {r["trim"]}')
                    ok(f'{t} {base} {pos}: no crash, not on autopilot', not r['crashed'] and not r['ap'], r)
                    if t == 'c130':
                        ok(f'C-130 {base} {pos}: follows the 3 degree path hands off, worst {r["worst"]:+} ft (limit {DEV})', abs(r['worst']) < DEV, r)
        worst = {t: max(abs(r['worst']) for (tt, _, _, r) in rows if tt == t) for t in TYPES}
        print('    worst deviation per aircraft (ft): ' + ', '.join(f'{t} {w}' for t, w in worst.items()))
        # the airdrop run in: level at 1,000 ft and 140 kt, hand flown
        await pg.evaluate(f"()=>{K}.mission('drop')")
        r = await pg.evaluate(FLY, [30, 0])
        ok(f'C-130 airdrop run in holds its height hands off, worst {r["worst"]:+} ft, {r["kt0"]}->{r["kt"]} kt', abs(r['worst']) < LEVEL and not r['crashed'], r)
        # cruise: clean, gear up, 6,000 ft, trimmed level at each speed, then hands off
        for kt in (160, 200, 250):
            await pg.evaluate(f"()=>{{{K}.pick('c130');{K}.pickBase('kgeu');{K}.start('runway')}}")
            await pg.evaluate("""(kt)=>{const K=window.__kgeu,s=K.state(),y=1500,V=kt/1.943844/Math.sqrt(1.097*Math.exp(-y/9200)/1.225);
              s.pos.y+=y;s.vel.set(0,0,-V);s.quat.set(0,0,0,1);s.w.set(0,0,0);s.onGround=false;s.airTime=30;s.flapIdx=0;s.gearDown=false;s.gearPos=0;
              K.trimSpawn(0);}""", kt)
            r = await pg.evaluate(FLY, [30, 0])
            ok(f'C-130 trimmed cruise at {kt} kt: no dive, no climb away, worst {r["worst"]:+} ft, {r["kt0"]}->{r["kt"]} kt', abs(r['worst']) < LEVEL and not r['crashed'], r)
        ok('no page errors', not pg.errs, pg.errs[:3])
        await b.close()
    sys.exit(ok.done('trim_check'))
asyncio.run(main())
