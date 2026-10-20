# Overwatch2 item 4b: the OVERWATCH radio is recorded and stitched. Every new clip (tools/make_radio.py OW_MC m_*,
# OW_S6 s_*, OW_PILOT p_*) is in radio/clips.json with a file of 0.15 to 16 s (ffprobe); in the game, with the clips
# decoded: Mission Control's opening tasking plays its stitched clips (the callsign, the terrain phrase, the distance,
# the position, the colour and the type) for 8 to 30 s and the voice queue holds the air that long (c.end - c.t0);
# the departure call names the colour and type; a decoy's Negative line stitches both vehicles; the talk-on stitches;
# every clip id a logged line carries was decoded; no console errors. Run: .venv/bin/python tests/overwatch_radio_check.py
import asyncio, json, os, subprocess, sys
from playwright.async_api import async_playwright
from harness import serve, page, Checks, ROOT
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import make_radio as MR
ok = Checks()
K = 'window.__kgeu'
STEP = "(n)=>{for(let i=0;i<n;i++)window.__kgeu.stepFrame(0.1,false,true)}"
async def adv(pg, sec): await pg.evaluate(STEP, int(sec * 10))
async def until(pg, cond, maxs=120, step=0.5):
    for _ in range(int(maxs / step)):
        await adv(pg, step)
        if await pg.evaluate(cond): return True
    return False

NEW = sorted([f'm_{k}' for k in MR.OW_MC] + [f's_{k}' for k in MR.OW_S6] + [f'p_{k}' for k in MR.OW_PILOT])
CLIPS = set(json.load(open(os.path.join(ROOT, 'radio', 'clips.json'))))

def dur(cid):
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0',
                        os.path.join(ROOT, 'radio', cid + '.m4a')], capture_output=True, text=True)
    try: return float(r.stdout.strip())
    except ValueError: return -1

async def main():
    miss = [c for c in NEW if c not in CLIPS or not os.path.exists(os.path.join(ROOT, 'radio', c + '.m4a'))]
    ok(f'clips.json lists all {len(NEW)} overwatch clips (m {len(MR.OW_MC)}, s {len(MR.OW_S6)}, p {len(MR.OW_PILOT)}), each file there', not miss, miss[:5])
    ds = {c: dur(c) for c in NEW if c not in miss}
    bad = {c: d for c, d in ds.items() if not 0.15 <= d <= 16}
    ok('every overwatch clip is 0.15 to 16 s long (ffprobe)', not bad, (bad, min(ds.values()), max(ds.values())))
    srv, url = serve()
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader',
                                          '--autoplay-policy=no-user-gesture-required'])
        pg = await page(b, url, vp={'width': 844, 'height': 390}, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'})
        await pg.evaluate(f"()=>{K}.initAudio()")
        for _ in range(120):
            r = await pg.evaluate(f"()=>{{const R={K}.RADIO;return {{want:R.want,got:R.got,err:R.err,slots:{K}.owSlots().n}}}}")
            if r['want'] and r['got'] + max(0, r['err']) >= r['want'] and r['slots']: break
            await pg.wait_for_timeout(500)
        ok('every clip decodes in the browser (the ?v=5 list)', r['want'] == len(CLIPS) and r['got'] == r['want'], r)
        dec = await pg.evaluate(f"()=>{K}.actx().state")
        # a seed where a decoy leaves first (the Negative line names it)
        seed = None
        for sd in range(1, 40):
            await pg.evaluate(f"()=>{{{K}.TASK.test.noBrief=false;{K}.taskStart('overwatch',{{seed:{sd}}})}}")
            if await pg.evaluate(f"()=>!!{K}.TASK.d.dcy"): seed = sd; break
            await pg.evaluate(f"()=>{K}.taskStop()")
        await pg.evaluate(f"()=>{K}.taskStop()")
        ok('a seed with a decoy leaving first', seed is not None, seed)
        await pg.evaluate(f"()=>{{{K}.radioLog(true);{K}.TASK.test.noBrief=true;{K}.taskStart('overwatch',{{seed:{seed}}})}}")
        CUR = f"()=>{{const c={K}.VQ.cur;return !!c&&/overwatch on a compound/.test(c.line.text)}}"
        await until(pg, CUR, 60, 0.2)
        o = await pg.evaluate(f"()=>{{const K={K},c=K.VQ.cur,d=K.TASK.d;return {{text:c.line.text,clips:c.line.clips,d:c.end-c.t0,a:K.RADIO.aEnd-K.RADIO.aStart,"
            f"miss:(c.line.clips||[]).filter(i=>!K.RADIO.buf[i]),terr:d.terrain,col:d.target.col,type:d.target.type,actx:K.actx().state}}}}")
        cl = o['clips'] or []
        ok('the opening tasking is stitched: callsign, Mission Control, the terrain phrase, the distance, the position, the climb, the colour and the type',
           cl[:3] == ['m_cs_skyguardian_s', 'm_task_open', 'm_terr_' + o['terr']] and 'm_miles' in cl and 'm_of_luke' in cl and 'm_degrees' in cl and 'm_decimal' in cl
           and cl[-3:] == ['m_task_climb', 'm_col_' + o['col'], 'm_ty_' + o['type']] and not o['miss'], o)
        # 8 to 30 s: at Mission Control's 185 words a minute the full tasking with its position reads about 26 to 27 s
        ok('the opening line plays for 8 to 30 s, and the voice queue holds the air for it (c.end - c.t0)', 8 <= o['a'] <= 30 and o['d'] >= o['a'] and o['d'] <= o['a'] + 1.0, (round(o['a'], 2), round(o['d'], 2), o['actx'], dec))
        # the watch: a decoy leaves, an early REPORT names it (the Negative line), then the target leaves and REPORT names it
        await pg.evaluate(f"()=>{{const K={K};K.taskAnswer('WILCO');K.tqStage(2);}}")
        await until(pg, f"()=>{{const a={K}.task().ask;return !!(a&&a.shown&&a.opts[0]==='REPORT')}}", 60, 0.2)
        await pg.evaluate(f"()=>{{const d={K}.TASK.d;d.dcy.go=1;d.fleet.list[1+d.dcy.i].moving=true;}}")
        await pg.evaluate(f"()=>{K}.taskAnswer('REPORT')")
        await until(pg, f"()=>{K}.radioLog().some(l=>/^Negative, that is/.test(l.text))", 60, 0.2)
        await pg.evaluate(f"()=>{{const d={K}.TASK.d;d.veh.moving=true;d.depT={K}.state().time;}}")
        await until(pg, f"()=>{{const a={K}.task().ask;return !!(a&&a.shown&&a.opts[0]==='REPORT')}}", 60, 0.2)
        await pg.evaluate(f"()=>{K}.taskAnswer('REPORT')")
        await until(pg, f"()=>{K}.radioLog().some(l=>/departing the compound/.test(l.text))", 60, 0.2)
        # the talk-on: first with the sensor off it (reacquiring, get your sensor back on), then on it (valid set for the call)
        await pg.evaluate(f"()=>{{const K={K};K.SENSOR.tgt=null;K.SENSOR.valid=false;K.owTalk();}}")
        await until(pg, f"()=>{K}.radioLog().some(l=>/sensor back on/.test(l.text))", 60, 0.2)
        await pg.evaluate(f"()=>{{const K={K},d=K.TASK.d;K.SENSOR.tgt=d.veh;K.SENSOR.valid=true;d.veh.spd=11;K.owTalk();}}")
        await until(pg, f"()=>{K}.radioLog().some(l=>l.who==='Saber 6'&&/^Contact/.test(l.text))", 90, 0.2)
        L = await pg.evaluate(f"()=>{K}.radioLog()")
        d = await pg.evaluate(f"()=>{{const d={K}.TASK.d,v=d.fleet.list[1+d.dcy.i];return {{col:d.veh.ck,type:d.veh.type,dcol:v.ck,dtype:v.type}}}}")
        buf = set(await pg.evaluate(f"()=>Object.keys({K}.RADIO.buf)"))
        neg = next((l for l in L if l['text'].startswith('Negative, that is')), None)
        ok('the decoy\'s Negative line stitches: that is the decoy, our vehicle is the target, still parked',
           neg and neg['clips'] == ['m_neg_that', 'm_the_' + d['dcol'], 'm_ty_' + d['dtype'], 'm_our_vehicle', 'm_the_' + d['col'], 'm_ty_' + d['type'], 'm_still_parked'], (neg, d))
        dep = next((l for l in L if 'departing the compound' in l['text']), None)
        ok('the departure call names the colour and the type in the pilot voice',
           dep and dep['clips'][:4] == ['p_mission_control', 'p_cs_skyguardian_s', 'p_departing_cmp', 'p_col_' + d['col']] and dep['clips'][4] == 'p_ty_' + d['type']
           and dep['clips'][5] == 'p_heading' and dep['clips'][6].startswith('p_dir_'), dep)
        talk = next((l for l in L if 'your vehicle is' in l['text']), None)
        ok('the talk-on stitches: Saber 6, the callsign, the vehicle, the miles, the bearing, the track or the road and the knots',
           talk and talk['clips'][:5] == ['p_saber6', 'p_cs_skyguardian_s', 'p_your_vehicle', 'p_the_' + d['col'], 'p_ty_' + d['type']] and 'p_miles' in talk['clips']
           and 'p_point' in talk['clips'] and talk['clips'][-1] in ('p_knots', 'p_stopped_track', 'p_stopped_road'), talk)
        tl = [l for l in L if l['who'] in ('Mission Control', 'Saber 6') or l['kind'] == 'pilot']
        nc = [l['text'][:50] for l in tl if not l['clips']]
        bad = sorted({c for l in tl for c in (l['clips'] or []) if c not in buf})
        ok(f'every tasking line on the air ({len(tl)}) carries clips, every one decoded', tl and not nc and not bad, (nc[:3], bad[:5]))
        ok('no console errors', not pg.errs, pg.errs[:3])
        await b.close()
    return ok.done('overwatch_radio_check')

if __name__ == '__main__':
    raise SystemExit(asyncio.run(main()))
