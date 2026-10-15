# Fix2 item 6: every start position chip works at every base of a region for every aircraft allowed there.
# For each base, each position chip (runway, ramp, final, final1) and each type: pick through the real FLY chips
# (the carousel dot .pick[data-t], the location card .pick[data-b], .pick[data-pos]), tap GO, draw the first flight
# frame, then 3 s of flight (stepFrame, brakes held) and read __kgeu.spawnInfo():
#   runway/ramp: on pavement at the position and 8 m behind and ahead along the heading, the base's runway or ramp
#     heading, not crashed, within 0.5 m of the spawn height and still at the spot after 3 s; on the ramp 10 m of room
#     from the wing and fuselage lines to any obstacle (OBST) and to a traffic stand (spawnInfo().clear)
#   final/final1: at B.fin(D) on the runway heading, airborne on the 3 degree path (D tan 3 deg above the ground),
#     not crashed after 3 s
# A type the base refuses (baseOK, the airliners' long runway rule) is skipped with a note and its card must be .off.
# --pause: a flight at KGEU paused, Sky Harbor and Ramp picked on the pause sheet, Apply: the restart is at the phx
# ramp (and the same with Luke). --shots: chase view by day on the ramp, overnight-screenshots/fix2/item6/.
# Usage: .venv/bin/python -u tests/spawn_check.py --region az|rjtt|lfpg|sbrj [--base phx] [--type b737] [--pause] [--shots]
import asyncio, sys, os, time, math
from playwright.async_api import async_playwright
from harness import serve, launch, page, IPHONE_15, Checks

def arg(k, d=None):
    return sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d
REG = arg('--region', 'az')
ONLY_BASE = arg('--base')
ONLY_TYPE = arg('--type')
PAUSE = '--pause' in sys.argv
SHOTS = '--shots' in sys.argv
SHOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'overnight-screenshots', 'fix2', 'item6')
SHOT_SET = {'az': [('phx', 'b737'), ('phx', 'c130'), ('luke', 'f16'), ('kgeu', 'cessna')],
            'rjtt': [('rjtt', 'b747')], 'lfpg': [('lfpg', 'a320')], 'sbrj': [('sbrj', 'cessna')]}
STORE = {'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3', 'kgeuPlace': '{"level":"ride","hours":null}',
         'kgeuRegion': REG, 'kgeuNoPre': '1'}
POSS = ['runway', 'ramp', 'final', 'final1']

# the chips, then GO: where it starts (read before the first flight frame moves it), then that frame drawn
PICK = """([t,b,p])=>{const K=window.__kgeu,q=s=>document.querySelector(s);
  q('#carMain .cdots .pick[data-t="'+t+'"]').click();q('#locFly .pick[data-b="'+b+'"]').click();q('#sFly .pick[data-pos="'+p+'"]').click();
  return {t:K.prefs().type,off:q('#locFly .pick[data-b="'+b+'"]').classList.contains('off'),base:K.prefs().base,pos:K.prefs().pos};}"""
GO = """()=>{const K=window.__kgeu;document.querySelector('#bGo').click();const s=K.spawnInfo();K.stepFrame(1/30);
  const B=K.BASES[K.state().base];s.B={hdg:B.hdg,rampHdg:B.rampHdg,ramp:[B.ramp[0](),B.ramp[1]()],run:[B.runway[0](),B.runway[1]()],
    f3:B.fin(5556),f1:B.fin(1852)};s.store=localStorage.getItem('kgeuPos');return s;}"""
RUN3 = """()=>{const K=window.__kgeu;for(let i=0;i<89;i++)K.stepFrame(1/30,false,true);return K.spawnInfo();}"""

def adiff(a, b): return abs((a - b + 540) % 360 - 180)

def judge(p, s0, s3):
    B = s0['B']; why = []
    if s0['pos'] != p or s0['store'] != p: why.append(f"pos {s0['pos']}/{s0['store']}")
    if s3['crashed']: why.append('crashed: ' + s3['why'])
    if p in ('runway', 'ramp'):
        want = B['ramp'] if p == 'ramp' else B['run']
        h = B['rampHdg'] if p == 'ramp' else B['hdg']
        if math.hypot(s0['x'] - want[0], s0['z'] - want[1]) > 1: why.append('not at the spot')
        if adiff(s0['hdgDeg'], h) > 1: why.append(f"hdg {s0['hdgDeg']:.1f} want {h}")
        if not all(s0['paved']): why.append(f"paved {s0['paved']}")
        if abs(s3['y'] - s0['y']) > 0.5: why.append(f"y {s0['y']:.2f}->{s3['y']:.2f}")
        if math.hypot(s3['x'] - s0['x'], s3['z'] - s0['z']) > 2: why.append('rolled %.1f m' % math.hypot(s3['x'] - s0['x'], s3['z'] - s0['z']))
        if not s3['onGround']: why.append('not on the ground')
        cl = s0['clear']
        if p == 'ramp' and (cl['obst'] < 10 or cl['stand'] < 10): why.append(f"room {cl['obst']:.0f} m to an obstacle, {cl['stand']:.0f} m to a stand")
    else:
        D = 1852 if p == 'final1' else 5556
        f = B['f1'] if p == 'final1' else B['f3']
        if math.hypot(s0['x'] - f[0], s0['z'] - f[1]) > 1: why.append('not at the final fix')
        if adiff(s0['hdgDeg'], B['hdg']) > 3: why.append(f"hdg {s0['hdgDeg']:.1f} want {B['hdg']:.1f}")
        want = D * math.tan(3 * math.pi / 180)
        if abs(s0['agl'] - want) > 0.12 * want: why.append(f"agl {s0['agl']:.0f} want {want:.0f}")
        if s3['onGround'] or s3['agl'] < 0.6 * want: why.append(f"agl after 3 s {s3['agl']:.0f}")
    return why

async def main():
    c = Checks(); srv, url = serve()
    async with async_playwright() as pw:
        b = await launch(pw)
        pg = await page(b, url, vp=IPHONE_15, storage=STORE)
        await pg.wait_for_function("()=>window.__kgeu.WORLD.ready||window.__kgeu.WORLD.err", timeout=30000)
        ev = lambda js, a=None: pg.evaluate(js, a)
        await ev("()=>{const K=window.__kgeu;K.setSkill('pilot');K.setTOD('day');K.openFly();}")
        info = await ev("()=>({reg:window.__kgeu.REGION.id,bases:Object.keys(window.__kgeu.BASES),types:Object.keys(window.__kgeu.TYPES)})")
        c('region loaded: ' + REG, info['reg'] == REG, info['reg'])
        bases = [x for x in info['bases'] if not ONLY_BASE or x == ONLY_BASE]
        types = [t for t in info['types'] if not ONLY_TYPE or t == ONLY_TYPE]
        n = ok = skipped = 0; slow = 0.0
        print(f"{'base':6} {'pos':7} {'type':7} result")
        for base in bases:
            for p in POSS:
                for t in types:
                    t0 = time.time()
                    r = await ev(PICK, [t, base, p])
                    allowed = await ev("([t,b])=>window.__kgeu.baseOK(t,b)", [t, base])
                    if not allowed:
                        skipped += 1
                        c(f'{base} {p} {t}: refused, card .off', r['off'], 'skip (runway too short)')
                        continue
                    s0 = await ev(GO)
                    await pg.keyboard.down(' ')
                    s3 = await ev(RUN3)
                    await pg.keyboard.up(' ')
                    why = judge(p, s0, s3)
                    if s0['base'] != base: why.append('base ' + s0['base'])
                    if s0['type'] != t: why.append('type ' + str(s0['type']))
                    dt = time.time() - t0; slow = max(slow, dt); n += 1
                    if not why: ok += 1
                    line = f"{base:6} {p:7} {t:7} {'ok  ' if not why else 'FAIL'} x {s0['x']:.0f} z {s0['z']:.0f} hdg {s0['hdgDeg']:.0f} agl {s0['agl']:.0f} paved {''.join('P' if v else '-' for v in s0['paved'])} room {min(s0['clear']['obst'],999):.0f}/{min(s0['clear']['stand'],999):.0f} {dt:.2f}s"
                    print(line + (('  ' + '; '.join(why)) if why else ''))
                    if why: c.fails.append(f'{base} {p} {t}: ' + '; '.join(why))
        print(f'\n{n} starts, {ok} pass, {skipped} refused (skipped); slowest {slow:.2f} s')
        if slow > 1.5: print('  note: a start took over 1.5 s')

        if PAUSE and REG == 'az':
            for (tb, tt) in [('phx', 'b737'), ('luke', 'c130')]:
                await ev("()=>{const K=window.__kgeu;K.pick('cessna');K.pickBase('kgeu');K.pickPos('runway');K.start('runway');K.stepFrame(1/30);K.togglePause();}")
                await ev("""([b,t])=>{const q=s=>document.querySelector(s);q('#pAc .pick[data-t="'+t+'"]').click();q('#locPz .pick[data-b="'+b+'"]').click();
                  q('#pauseOv .pick[data-pos="ramp"]').click();q('#pApply').click();}""", [tb, tt])
                s = await ev("()=>{const K=window.__kgeu;K.stepFrame(1/30);const s=K.spawnInfo(),B=K.BASES[s.base];s.ramp=[B.ramp[0](),B.ramp[1]()];return s;}")
                c(f'pause sheet: {tb} + Ramp + Apply restarts at the {tb} ramp', s['base'] == tb and s['pos'] == 'ramp' and s['spawn'] == 'ramp'
                  and math.hypot(s['x'] - s['ramp'][0], s['z'] - s['ramp'][1]) < 1 and all(s['paved']) and s['type'] == tt and not s['crashed'],
                  {k: s[k] for k in ('base', 'pos', 'spawn', 'type', 'paved')})

        if SHOTS:
            os.makedirs(SHOT_DIR, exist_ok=True)
            for (sb, stp) in SHOT_SET.get(REG, []):
                await ev(PICK, [stp, sb, 'ramp']); await ev(GO)
                for _ in range(4): await ev("()=>window.__kgeu.stepFrame(1/30)")
                await pg.wait_for_timeout(200)
                f = os.path.join(SHOT_DIR, f'ramp_{sb}_{stp}.png'); await pg.screenshot(path=f); print('  shot', os.path.relpath(f))
        await ev("()=>window.__kgeu.stepFrame(0,true)")
        c('no console errors', not pg.errs, ' | '.join(pg.errs[:2]))
        await b.close()
    sys.exit(c.done(f'spawn_check {REG}' + (f' {ONLY_BASE}' if ONLY_BASE else '')))

asyncio.run(main())
