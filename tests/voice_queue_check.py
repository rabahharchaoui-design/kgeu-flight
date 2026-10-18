# One voice at a time: the instructor, the tower and other traffic share one priority
# queue. During a flight school lesson we fire tower calls and chatter while the
# instructor is talking and check that no two voices ever overlap, the instructor goes
# first, the tower follows, stale calls are dropped and the subtitle follows the audio.
# schoolhud: the instructor is her recorded clips (radio/cfi), decoded before the lesson, so her lines have their real
# length in headless Chromium; the test lines are lines the lessons really say. The sim is stepped in real time from
# inside the page, so sim seconds and audio seconds match.
# Run: .venv/bin/python tests/voice_queue_check.py
import asyncio, sys
from playwright.async_api import async_playwright
from harness import serve, THREE, IGNORE, splash_gone, Checks
ok = Checks()
K = 'window.__kgeu'
# step the sim by real elapsed time every 50 ms and sample who is audible
DRIVE = """()=>{const K=window.__kgeu;let last=performance.now();window.__samp=[];clearInterval(window.__iv);
  window.__iv=setInterval(()=>{const n=performance.now(),d=Math.min(0.1,(n-last)/1000);last=n;K.stepFrame(d,false,true);
    const a=document.getElementById('atc');
    window.__samp.push({t:n/1000,radio:K.RADIO.src.length,sp:K.CFIV.src.length>0,atc:a.classList.contains('on')?a.querySelector('b')&&a.querySelector('b').textContent:'',txt:a.textContent,cur:K.VQ.cur?K.VQ.cur.line.text:null,duck:K.music().ducked});},50);}"""
STOP = "()=>{clearInterval(window.__iv);window.__kgeu.stepFrame(0,true);}"

def overlaps(log, tol):
    """pairs of voice records whose audible spans overlap by more than tol seconds"""
    r = sorted([e for e in log if e['a1'] is not None], key=lambda e: e['a0'])
    bad = []
    for i in range(1, len(r)):
        end = max(e['a1'] for e in r[:i])
        if r[i]['a0'] < end - tol: bad.append((r[i - 1]['text'][:30], r[i]['text'][:30], round(end - r[i]['a0'], 2)))
    return bad

async def wait_until(pg, js, limit):
    try: await pg.wait_for_function(js, timeout=limit * 1000, polling=100); return True
    except Exception: return False

async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist',
            '--enable-unsafe-swiftshader', '--autoplay-policy=no-user-gesture-required'])
        ctx = await b.new_context(viewport={'width': 844, 'height': 390}, has_touch=True, is_mobile=True, device_scale_factor=2)
        await ctx.add_init_script("(()=>{if(sessionStorage.getItem('__seeded'))return;sessionStorage.setItem('__seeded','1');localStorage.clear();"
            "localStorage.setItem('kgeuOnboard','pilot');localStorage.setItem('kgeuTut','1');localStorage.setItem('kgeuCoach','3');})()")
        pg = await ctx.new_page(); errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.on('console', lambda m: errs.append(m.text) if m.type == 'error' and not any(k in m.text for k in IGNORE) else None)
        await pg.route('**/three.min.js', lambda r: r.fulfill(body=THREE, content_type='application/javascript'))
        await pg.route('**/fonts.googleapis.com/**', lambda r: r.abort())
        await pg.route('**/fonts.gstatic.com/**', lambda r: r.abort())
        await pg.goto(url); await pg.wait_for_function('()=>window.__kgeu', timeout=30000); await splash_gone(pg)
        await pg.evaluate(f"()=>{K}.initAudio()")
        for _ in range(40):
            r = await pg.evaluate(f"()=>{{const R={K}.RADIO;return R.want&&R.got+Math.max(0,R.err)>=R.want}}")
            if r: break
            await pg.wait_for_timeout(500)
        ok('radio clips loaded', r)
        await pg.evaluate(f"()=>{K}.cfiPrep('pattern')")
        r = await wait_until(pg, f"()=>{K}.CFIV.want>0&&{K}.CFIV.got>={K}.CFIV.want", 90)
        ok("Dana's clips decoded (common and pattern)", r)

        # (1) pattern lesson: the instructor's long opening line, the takeoff clearance at 0.6 s,
        # chatter and a tower advisory fired while the instructor talks
        await pg.evaluate(f"()=>{{const K={K};K.stepFrame(0,false,true);K.startLesson('pattern',true);K.lesBriefSkip();K.vqLog(true);K.radioLog(true);}}")
        # startLesson spoke before we cleared the logs: say it again so it is on record
        await pg.evaluate(f"()=>{{const K={K};K.coach2('Pattern work. Take off, climb to 700 above the ground, fly the circuit at 2,100 and land on runway 1.');K.vqAdd('Viper 99','fighter','Viper 99, chatter test one.',['p_ch_p1'],{{pri:3}});}}")
        await pg.evaluate(DRIVE)
        await pg.wait_for_timeout(1500)
        # school1 item 5: the pattern's clearance waits for the student's call (the CALL reply button)
        await wait_until(pg, f"()=>{K}.TASK.ask&&{K}.TASK.ask.shown", 10)
        ok('the CALL button is offered', await pg.evaluate(f"()=>{K}.tqAnswer('CALL')"))
        await pg.evaluate(f"()=>{{const K={K};window.__ok=true;K.vqAdd('Glendale Tower 121.0','tower','Skyhawk 31G, runway 1, cleared for takeoff. (stale test)',['t_cleared_to'],{{ok:()=>window.__ok}});K.vqAdd('Viper 98','fighter','Viper 98, chatter test two.',['p_ch_p4'],{{pri:3}});}}")
        await pg.wait_for_timeout(1500)
        mid = await pg.evaluate(f"()=>{{const a=document.getElementById('atc'),l=document.getElementById('lesson');const A=a.getBoundingClientRect(),B=l.getBoundingClientRect();"
                                f"return {{who:a.querySelector('b')&&a.querySelector('b').textContent,q:{K}.radioQ().map(x=>x.who+': '+x.text),"
                                "hit:A.height>0&&!(A.right<B.left||B.right<A.left||A.bottom<B.top||B.bottom<A.top),duck:window.__kgeu.music().ducked,"
                                "lc:l.classList.contains('lc'),inPanel:l.classList.contains('call')&&document.getElementById('lesCap').textContent.indexOf('Dana')===0}}")
        ok('while the instructor talks the subtitle is the instructor, not the queued tower', mid['who'] == 'Dana', mid)
        ok('the tower clearance waits in the queue', any('cleared for takeoff' in x for x in mid['q']), mid['q'])
        ok('the tower subtitle box does not cover the lesson panel', not mid['hit'], mid)
        # fix2 item 11: in landscape the lesson strip carries the line on the air (the separate caption is hidden)
        ok("the line on the air is in the lesson panel's instruction line", not mid['lc'] or mid['inPanel'], mid)
        # the instructor goes on; the second clearance stops being relevant before it can play
        await pg.evaluate("()=>{window.__ok=false;}")
        done = await wait_until(pg, f"()=>{{const K={K};return K.radioLog().some(l=>/Cleared for takeoff, /.test(l.text))&&!K.VQ.cur}}", 45)
        ok('the clearance and the readback played after the instructor', done)
        # (2) an instruction arriving mid tower call: the call is cut with a fade, requeued, and replays after
        await pg.evaluate(f"()=>{{const K={K};window.__cutT=null;K.say('Glendale Tower 121.0','Skyhawk 31G, make right closed traffic, runway 1, report midfield downwind.',['t_cs_skyhawk_s','t_closed_traffic','t_rwy_1','t_wind','t_n_0','t_n_1','t_n_0','t_at','t_n_5']);}}")
        await pg.wait_for_timeout(900)
        await pg.evaluate(f"()=>{{{K}.coach2('Turn crosswind now. Level off at 2,100.');}}")
        await wait_until(pg, f"()=>{{const K={K};return K.radioLog().filter(l=>/report midfield/.test(l.text)).length>=2&&!K.VQ.cur&&!K.radioQ().length}}", 40)
        # (3) a safety call cuts the instructor at once
        await pg.evaluate(f"()=>{{{K}.coach2('Pattern work. Take off, climb to 700 above the ground, fly the circuit at 2,100 and land on runway 1.');}}")
        await pg.wait_for_timeout(1200)
        await pg.evaluate(f"()=>{{{K}.coach2('Go around. Full power, nose up, flaps up a notch.',null,{{urgent:1}});}}")
        await wait_until(pg, f"()=>!{K}.VQ.cur&&!{K}.radioQ().length", 20)
        await pg.evaluate(STOP)

        log = await pg.evaluate(f"()=>{K}.vqLog()")
        rlog = await pg.evaluate(f"()=>{K}.radioLog().map(l=>l.who+': '+l.text)")
        samp = await pg.evaluate("()=>window.__samp")
        for e in log: print('    ', e['pri'], ('%.2f' % e['a0']), ('%.2f' % e['a1']) if e['a1'] is not None else '-', e['who'][:18], '|', e['text'][:60])
        texts = [e['text'] for e in log]
        ok('every voice record closed', all(e['a1'] is not None for e in log), [e['text'][:30] for e in log if e['a1'] is None])
        ok('no two voices overlap (0.1 s allowed for the cut fade)', not overlaps(log, 0.1), overlaps(log, 0.1))
        both = [s['t'] for s in samp if s['radio'] > 0 and s['sp']]
        ok('sampled every 50 ms: radio clips and the instructor never sound together', not both, both[:5])
        ok('the instructor plays first', log and log[0]['who'] == 'Dana', texts[:2])
        ci = next((i for i, e in enumerate(log) if 'cleared for takeoff' in e['text'] and 'stale' not in e['text']), None)
        ok('the tower clearance plays after the instruction ends', ci is not None and ci > 0 and log[ci]['a0'] >= log[0]['a1'] - 0.01,
           (ci, log[0]['a1'], log[ci]['a0'] if ci is not None else None))
        rb = next((i for i, e in enumerate(log) if e['text'].startswith('Cleared for takeoff')), None)
        ok('the readback follows the clearance', rb is not None and ci is not None and rb > ci, (ci, rb))
        ok('stale chatter queued behind the instructor was dropped', not any('chatter test' in t for t in texts + rlog), [t for t in texts if 'chatter test' in t])
        ok('a clearance that stopped being relevant was dropped', not any('stale test' in t for t in texts))
        ct = [i for i, e in enumerate(log) if 'report midfield' in e['text']]   # the test's own long call (the pattern's clearance also says closed traffic)
        ins = next((i for i, e in enumerate(log) if e['text'].startswith('Turn crosswind now. Level off')), None)
        ok('an instruction cuts a long tower call, which replays after it', len(ct) == 2 and ins is not None and ct[0] < ins < ct[1], (ct, ins))
        if len(ct) == 2 and ins is not None:
            ok('the cut tower call stops before the instruction starts (fade under 0.1 s)', log[ct[0]]['a1'] <= log[ins]['a0'] + 0.1, (log[ct[0]]['a1'], log[ins]['a0']))
        st = next((i for i, e in enumerate(log) if e['text'].startswith('Go around. Full power')), None)
        ok('an urgent call (Go around) cuts the instructor at once', st is not None and log[st]['pri'] == 0 and log[st - 1]['who'] == 'Dana'
           and log[st - 1]['a1'] is not None and log[st - 1]['a1'] <= log[st]['a0'] + 0.1, (st, log[st - 1:st + 1] if st else None))
        ok('her lines played from clips, none missed', not [e for e in await pg.evaluate(f"()=>{K}.CFIV.miss")], await pg.evaluate(f"()=>{K}.CFIV.miss"))
        # subtitles follow the audio: while the instructor speaks the subtitle is the instructor's,
        # and a tower subtitle only shows while tower clips are playing or just after
        wrong = [s for s in samp if s['sp'] and s['atc'] and s['atc'] != 'Dana']
        ok('while the instructor speaks, the subtitle is never a tower call', not wrong, wrong[:2])
        early = [(s['cur'][:30], s['txt'][:40]) for s in samp if s['cur'] and s['atc'] and s['cur'] not in s['txt']]
        ok('the subtitle is always the line on the air, never one still queued', not early, early[:2])
        dk = [s['duck'] for s in samp if s['sp']]
        ok('music ducks under the instructor', dk and sum(dk) >= 0.9 * len(dk), f'{sum(dk)}/{len(dk)}')
        ok('no page errors', not errs, errs[:3])
        await b.close()
    srv.shutdown()
    sys.exit(ok.done('voice_queue_check'))

asyncio.run(main())
