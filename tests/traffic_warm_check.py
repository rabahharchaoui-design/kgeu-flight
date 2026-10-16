# Fix2 item 2: no shader program linked in flight by the AI traffic, the time of day or a region's landmarks.
# iPhone landscape 844x390 at 2x, Medium (localStorage kgeuTier). One page load per case: wait for the precompile
# queue and the menu's WARM steps, start a free flight (Hard, TFC.auto on), note progN().compiles after the first flight
# frame, then 10 simulated minutes of traffic by day (TFC.update(0.5) x 1,200 in one evaluate, a rendered stepFrame
# every 20 updates; the sky cleared and every type with a plan force spawned into its whole pool at minutes 2, 5 and 8,
# tfcClear at 4 and 7), night 2 minutes, sunset 1 minute. Fails on any compile after the first flight frame (prints the progList
# diff: name and cache key) or a 'prog' tag in __kgeu.stalls().log, or a page error.
#   timeout 110 .venv/bin/python -u tests/traffic_warm_check.py --region az-kgeu   (one case a call keeps under 110 s)
#   regions: az-kgeu (F-16), az-luke (Cessna), az-phx (737), rjtt, lfpg, sbrj (F-16); none given: all, one page each
import asyncio, os, sys, time
args = sys.argv[1:]
def opt(n, d):
    if n in args:
        i = args.index(n); v = args[i + 1]; del args[i:i + 2]; return v
    return d
ONLY = opt('--region', '')
os.environ['PFS_TIER'] = opt('--tier', 'medium')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from playwright.async_api import async_playwright   # noqa: E402
import graphics_shots as G   # noqa: E402
from harness import IGNORE   # noqa: E402
K = G.K
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
CASES = {'az-kgeu': (None, 'f16', 'kgeu'), 'az-luke': (None, 'cessna', 'luke'), 'az-phx': (None, 'b737', 'phx'),
         'rjtt': ('rjtt', 'f16', None), 'lfpg': ('lfpg', 'f16', None), 'sbrj': ('sbrj', 'f16', None)}

# n updates of 0.5 s, a drawn frame every k; force spawns (every type with a plan, into its free slots) at the listed
# update indices (the sky cleared first, so the whole pool is free), tfcClear at others. Returns the types seen alive, spawned by force, and the clears done.
RUN = f"""([n,k,force,clear])=>{{const K={K},seen={{}},forced={{}},T=Object.keys(K.TFC.pool);let clears=0,maxN=0;
  const F=new Set(force),C=new Set(clear);
  for(let i=0;i<n;i++){{
    if(F.has(i)){{K.tfcClear();clears++;for(const t of T){{let ok=0;for(let j=0;j<K.TFC.pool[t].length;j++)if(K.tfcSpawn(t,{{force:true}})!=null)ok=1;forced[t]=(forced[t]||0)+ok;}}}}
    if(C.has(i)){{K.tfcClear();clears++;K.TFC.need=true;}}
    K.TFC.update(0.5);if(i%k===0)K.stepFrame(1/30);
    const L=K.tfcList();maxN=Math.max(maxN,L.length);for(const o of L)seen[o.type]=1;}}
  K.stepFrame(1/30);return {{seen:Object.keys(seen).sort(),forced:forced,clears:clears,maxN:maxN}};}}"""
PROG = f"()=>{K}.progN().compiles"

async def run_case(p, name):
    reg, t, base = CASES[name]
    init = G.INIT + (f"localStorage.setItem('kgeuRegion','{reg}');" if reg else '')
    t0 = time.time()
    b = await G.launch(p)
    ctx = await b.new_context(viewport={'width': 844, 'height': 390}, is_mobile=True, has_touch=True, device_scale_factor=2)
    await ctx.add_init_script(init)
    pg = await ctx.new_page(); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.on('console', lambda m: errs.append(m.text) if m.type == 'error' and not any(k in m.text for k in IGNORE) else None)
    await pg.route('**/three.min.js', lambda r: r.fulfill(body=G.THREE, content_type='application/javascript'))
    await pg.route('**/fonts.g*/**', lambda r: r.abort())
    await pg.goto(URL); await pg.wait_for_function(f'()=>{K}', timeout=30000)
    if reg: await pg.wait_for_function(f"()=>{K}.WORLD.ready||{K}.WORLD.err", timeout=30000)
    await pg.wait_for_function(f"()=>{K}.boot().pre.done&&{K}.warm()&&{K}.warmTimes().total>0", timeout=90000, polling=250)
    tier = await pg.evaluate(f"()=>{K}.GFX.tier")
    await pg.evaluate(f"()=>{{const K={K};K.stallsClear();K.setSkill('pilot');K.setTOD('day');K.TFC.auto=true;K.pick('{t}');"
                      + (f"K.pickBase('{base}');" if base else '') + "K.start('runway');K.stepFrame(1/30);}")
    c0 = await pg.evaluate(PROG)
    keys0 = {q['cacheKey'] for q in await pg.evaluate(f"()=>{K}.progList()")}
    print(f'[{name}] {tier}, {t} {"at " + base if base else "in " + reg}: {c0} programs ever linked after the first flight frame ({time.time() - t0:.0f} s)', flush=True)
    m = 120   # updates a simulated minute
    day = await pg.evaluate(RUN, [10 * m, 20, [2 * m, 5 * m, 8 * m], [4 * m, 7 * m]])
    c1 = await pg.evaluate(PROG)
    await pg.evaluate(f"()=>{K}.setTOD('night')")
    night = await pg.evaluate(RUN, [2 * m, 20, [m], []])
    c2 = await pg.evaluate(PROG)
    await pg.evaluate(f"()=>{K}.setTOD('sunset')")
    sun = await pg.evaluate(RUN, [m, 20, [0], []])
    c3 = await pg.evaluate(PROG)
    st = await pg.evaluate(f"()=>{K}.stalls()")
    now = await pg.evaluate(f"()=>{K}.progList()")
    new = [q for q in now if q['cacheKey'] not in keys0]
    prog_tags = [r for r in st['log'] if any(tg.startswith('prog') for tg in r['tags'])]
    plans = await pg.evaluate(f"()=>{K}.TFC.plans.map(p=>p.type).filter((v,i,a)=>a.indexOf(v)===i).sort()")
    print(f'  day 10 min: seen {day["seen"]}, forced {day["forced"]}, clears {day["clears"]}, max alive {day["maxN"]}, compiles {c1 - c0}')
    print(f'  night 2 min: seen {night["seen"]}, compiles {c2 - c1}; sunset 1 min: seen {sun["seen"]}, compiles {c3 - c2}')
    ok = c3 == c0 and not prog_tags and not errs
    every = all(day['forced'].get(tp, 0) >= 2 for tp in plans) and day['clears'] >= 4
    ok = ok and every
    if not every: print(f'  FAIL: not every planned type {plans} force spawned twice and cleared twice')
    for q in new: print(f"  NEW id {q['id']} {q['name']} key {q['cacheKey'][:240]}")
    for r in prog_tags: print(f"  stall {r['gap']} ms {' '.join(r['tags'])}")
    for e in errs[:5]: print('  page error:', e[:200])
    print(f'  {"PASS" if ok else "FAIL"} {name} ({time.time() - t0:.0f} s wall)', flush=True)
    await b.close()
    return ok

URL = None
async def main():
    global URL
    URL = G.serve(ROOT)
    names = [ONLY] if ONLY else list(CASES)
    res = {}
    async with async_playwright() as p:
        for n in names: res[n] = await run_case(p, n)
    print('\n' + ', '.join(f'{n} {"PASS" if v else "FAIL"}' for n, v in res.items()))
    sys.exit(0 if all(res.values()) else 1)

asyncio.run(main())
