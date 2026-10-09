# Event start (phone notes 0929, item 1): every way into a flight, started by a real tap, 10 times
# in a row with the menu in between. Within 500 ms of the start tap the stick, the throttle and the
# HUD must be on screen (display not none, opacity above 0, a real rect, and elementFromPoint at the
# centre lands on them, not on an overlay) and a real touch on the stick and on the throttle must
# move the controls. After the first start of each event nothing may compile on the start frames:
# the aircraft, the drop zone and their shaders are warmed up at the menu, never on the tap.
# iPhone landscape 844x390, touch, dsf 2.
# Run: .venv/bin/python tests/event_start_check.py [--events a,b] [--reps N] [--easy] [--list]
# The full run (18 events x 10) takes about 8 minutes. To keep a run short, split it in two, e.g.
#   --events free_runway,free_final1,daily,short,dash,landing,landing1,drop,range
#   --events lesson_first,lesson_steep,lesson_slow,lesson_stall,lesson_engine,lesson_pattern,crash_retry,pause_restart,grade_retry
import asyncio, sys, time
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, finger, IPHONE_15
ok = Checks()
K = "window.__kgeu"
LIMIT = 500   # ms from the start tap

def arg(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv and sys.argv.index(name) + 1 < len(sys.argv) else default

# event: (menu screen, the button tapped to start it, js run first)
EVENTS = {
    'free_runway':    ('sFly', '#bGo', f"{K}.pickPos('runway')"),
    'free_final1':    ('sFly', '#bGo', f"{K}.pickPos('final1')"),
    'daily':          ('sArc', '#arcCards .mcard[data-m=daily]', ''),
    'short':          ('sArc', '#arcCards .mcard[data-m=short]', ''),
    'dash':           ('sArc', '#arcCards .mcard[data-m=dash]', ''),
    'landing':        ('sArc', '#arcCards .mcard[data-m=landing]', ''),
    'landing1':       ('sArc', '#arcCards .mcard[data-m=landing1]', ''),
    'drop':           ('sArc', '#arcCards .mcard[data-m=drop]', ''),
    'range':          ('sArc', '#arcCards .mcard[data-m=range]', ''),
    'lesson_first':   ('sSchool', '#school .lrow[data-l=first]', ''),
    'lesson_steep':   ('sSchool', '#school .lrow[data-l=steep]', ''),
    'lesson_slow':    ('sSchool', '#school .lrow[data-l=slow]', ''),
    'lesson_stall':   ('sSchool', '#school .lrow[data-l=stall]', ''),
    'lesson_engine':  ('sSchool', '#school .lrow[data-l=engine]', ''),
    'lesson_pattern': ('sSchool', '#school .lrow[data-l=pattern]', ''),
    # the in-flight ways back in: RETRY on the crash card, Restart on the pause sheet (#pApply, it reads Restart until a pick changes), Retry on a lesson grade
    'crash_retry':    (None, '#cRetry', 'crash'),
    'pause_restart':  (None, '#pApply', 'pause'),
    'grade_retry':    (None, '#gRetry', 'grade'),
}

# page side: poll from the start tap until the flight UI is up, or give up at 3 s
UI = """(t0)=>new Promise(res=>{
  const K=window.__kgeu;
  function vis(sel,hitSelf){const el=document.querySelector(sel);if(!el)return sel+' missing';
    const r=el.getBoundingClientRect();if(r.width<2||r.height<2)return sel+' zero rect';
    if(r.right<=0||r.bottom<=0||r.left>=innerWidth||r.top>=innerHeight)return sel+' off screen';
    for(let e=el;e&&e!==document.documentElement;e=e.parentElement){const cs=getComputedStyle(e);
      if(cs.display==='none')return sel+' display none on '+(e.id||e.className||e.tagName);
      if(cs.visibility==='hidden')return sel+' visibility hidden';
      if(+cs.opacity===0)return sel+' opacity 0 on '+(e.id||e.tagName);}
    const h=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);if(!h)return sel+' nothing at centre';
    if(h.closest('.overlay,#rotate,#splash'))return sel+' covered by '+(h.closest('.overlay,#rotate,#splash').id);
    // the HUD lets touches through (pointer-events none): whatever is under it must be the flight view
    if(hitSelf?!el.contains(h):!(h.id==='gl'||h.closest('#uiroot')))return sel+' centre hits '+(h.id||h.className||h.tagName);
    return '';}
  function why(){if(!K.running())return 'not running';if(K.paused())return 'paused';
    const hud=document.body.classList.contains('sensorOn')?'#sensorHud':'#hud .card';
    return vis('#stickZone',1)||vis('#thr',1)||vis(hud,0);}
  const go=()=>{const w=why(),t=performance.now()-t0;if(!w||t>3000)res({ms:Math.round(t),why:w,sensor:document.body.classList.contains('sensorOn')});else setTimeout(go,5);};go();})"""

# page side: from time zero, when the stick takes a finger, when it deflects, when the throttle moves
WATCH = """(t0)=>{const K=window.__kgeu,th0=K.state().throttle,w=window.__watch={t0:t0,stick:null,ail:null,thr:null,done:false};
  const f=()=>{const t=Math.round(performance.now()-t0);
    if(w.stick===null&&K.touchIn.active)w.stick=t;
    if(w.ail===null&&K.touchIn.ail>0.3&&K.touchIn.elev<-0.1)w.ail=t;
    if(w.thr===null&&Math.abs(K.state().throttle-th0)>0.1)w.thr=t;
    w.done=w.stick!==null&&w.ail!==null&&w.thr!==null;if(!w.done&&t<4000)setTimeout(f,2);};f();}"""

async def main():
    if '--list' in sys.argv:
        print('\n'.join(EVENTS)); return 0
    names = arg('--events', ','.join(EVENTS)).split(',')
    bad = [n for n in names if n not in EVENTS]
    if bad: print('unknown events:', bad, '\nknown:', ', '.join(EVENTS)); return 2
    reps = int(arg('--reps', '10'))
    srv, url = serve()
    T = time.time()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'rookie' if '--easy' in sys.argv else 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'})
        await pg.wait_for_function(f"()=>{K}.warm()", timeout=30000)
        ok('warm up at the menu finished (every aircraft and the drop zone built and compiled)', True)
        # today's daily may be at a world airport (the rotation): pin it to Arizona so its tap starts a flight, no reload
        await pg.evaluate(f"()=>{K}.dailyRegion('az')")
        cdp = await pg.context.new_cdp_session(pg)
        async def touch(kind, pts):
            await cdp.send('Input.dispatchTouchEvent', {'type': kind, 'touchPoints': [
                {'x': x, 'y': y, 'id': i, 'radiusX': 4, 'radiusY': 4, 'force': 1} for i, (x, y) in pts]})
        async def rect(sel):
            return await pg.evaluate("(s)=>{const r=document.querySelector(s).getBoundingClientRect();return [r.x,r.y,r.width,r.height]}", sel)

        async def prepare(name):
            scr, sel, pre = EVENTS[name]
            if scr:
                await pg.evaluate(f"(s)=>{{{K}.openMenu();{K}.nav(s);}}", scr)
                if pre: await pg.evaluate(f"()=>{{{pre}}}")
                await pg.wait_for_timeout(250)
                return
            # in flight: fly first, then bring up the card the button lives on
            if pre == 'grade':
                await pg.evaluate(f"()=>{K}.startLesson('steep')"); await pg.wait_for_timeout(300)
                # the lesson never started its turn: past 60 s it grades itself F
                await pg.evaluate(f"()=>{{{K}.LES.t=61;for(let i=0;i<3;i++){K}.stepFrame(1/30,false,true);{K}.stepFrame(0,true);}}")
                await pg.wait_for_function("()=>document.getElementById('gradeOv').classList.contains('on')", timeout=5000)
            else:
                await pg.evaluate(f"()=>{{{K}.openMenu();{K}.pick('cessna',1);{K}.start('runway');}}"); await pg.wait_for_timeout(300)
                if pre == 'crash':
                    await pg.evaluate(f"()=>{{{K}.crashNow('test');for(let i=0;i<60&&!document.getElementById('crash').classList.contains('on');i++){K}.stepFrame(0.1,false,true);{K}.stepFrame(0,true);}}")
                    await pg.wait_for_function("()=>document.getElementById('crash').classList.contains('on')", timeout=5000)
                else:
                    await finger(pg, '#bPause')
                    await pg.wait_for_function("()=>document.getElementById('pauseOv').classList.contains('on')", timeout=5000)
            await pg.wait_for_timeout(200)

        worst = {}
        for name in names:
            sel = EVENTS[name][1]
            fails = []; ms_ui = []; ms_in = []; progs = []; first = []; steady = []
            for rep in range(reps):
                await prepare(name)
                p0 = await pg.evaluate(f"()=>{K}.glProgs()")
                # The harness draws about 3 frames a second, so the game loop is held (no frames) from just
                # before the tap until the checks are done: the tap, start() and the touches then take
                # their own time, not the harness's. It also makes the check strict: the controls must be
                # up and live on the DOM start() leaves, before the game's next frame has run at all.
                await pg.evaluate(f"()=>{K}.stepFrame(0,false,true)")
                t0 = await pg.evaluate("()=>performance.now()")
                await finger(pg, sel)
                r = await pg.evaluate(UI, t0)
                if r['why']:
                    fails.append(f"rep {rep+1}: {r['why']} after {r['ms']} ms"); await pg.evaluate(f"()=>{K}.stepFrame(0,true)"); continue
                ms_ui.append(r['ms'])
                # straight away: one finger on the stick and one on the throttle, then both move. The page
                # notes when the stick takes the finger and deflects and when the throttle moves
                z = await rect('#stickZone'); th = await rect('#thr')
                c = (z[0] + z[2] / 2, z[1] + z[3] / 2); tp = (th[0] + th[2] / 2, th[1] + th[3] * 0.6)
                await pg.evaluate(f"()=>{{{K}.state().throttle=0.05;}}")
                await pg.evaluate(WATCH, t0)
                await touch('touchStart', [(1, c), (2, tp)])
                await touch('touchMove', [(1, (c[0] + 60, c[1] - 30)), (2, (tp[0], tp[1] - th[3] * 0.35))])
                s = await pg.evaluate("()=>new Promise(r=>{const f=()=>{const w=window.__watch;if(w.done||performance.now()-w.t0>4000)r(w);else setTimeout(f,5)};f();})")
                await touch('touchEnd', [])
                if s.get('stick') is None or s.get('ail') is None: fails.append(f"rep {rep+1}: stick dead {s}")
                elif s.get('thr') is None: fails.append(f"rep {rep+1}: throttle dead {s}")
                else: ms_in.append(max(s['stick'], s['ail'], s['thr']))
                # let the game run again: the first frames after the start, against the ones after
                fr = await pg.evaluate(f"""()=>new Promise(res=>{{{K}.stepFrame(0,true);const f=[];let p=performance.now();
                  const st=()=>{{const n=performance.now();f.push(Math.round(n-p));p=n;if(f.length<6)requestAnimationFrame(st);else res(f);}};requestAnimationFrame(st);}})""")
                first.append(max(fr[:2])); steady.append(max(fr[3:]))
                progs.append(await pg.evaluate(f"()=>{K}.glProgs()") - p0)
            n = len(ms_ui)
            ok(f'{name}: controls and HUD up on every start ({n} of {reps})', not [f for f in fails if 'dead' not in f],
               '; '.join(fails[:3]) if fails else f"max {max(ms_ui)} ms" + (' (sensor view)' if r.get('sensor') else ''))
            ok(f'{name}:   ...within {LIMIT} ms of the tap', n and max(ms_ui) <= LIMIT, f"max {max(ms_ui) if n else '-'} ms")
            ok(f'{name}:   stick and throttle answer a real touch within {LIMIT} ms', len(ms_in) == reps and max(ms_in) <= LIMIT,
               '; '.join([f for f in fails if 'dead' in f][:2]) or f"max {max(ms_in) if ms_in else '-'} ms")
            ok(f'{name}:   nothing compiles on the start frames after the first start', all(x == 0 for x in progs[1:]),
               f"new programs per start {progs}; first frames {first} ms, then {steady} ms")
            worst[name] = (max(ms_ui) if ms_ui else None, max(ms_in) if ms_in else None)
        ok('no page errors', not pg.errs, pg.errs[:3])
        await b.close()
    print(f'\n{len(names)} events x {reps} starts in {time.time()-T:.0f} s')
    return ok.done('event_start_check')

sys.exit(asyncio.run(main()))
